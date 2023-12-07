#!/usr/bin/env python

import argparse
import base64
import sys
import time
import xml.etree.ElementTree as et
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import pandas as pd
import requests
import yaml
from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository

# Config variables
BIOTOOLS_API_URL = "https://bio.tools"
# BIOTOOLS_API_URL = "https://130.226.25.21"


def read_file(filepath: Optional[str]) -> List[str]:
    """
    Read an optional file with 1 element per line

    :param filepath: path to a file
    """
    if filepath is None:
        return []
    fp = Path(filepath)
    if fp.is_file():
        with fp.open("r") as f:
            return [x.rstrip() for x in f.readlines()]
    else:
        return []


def get_string_content(cf: ContentFile) -> str:
    """
    Get string of the content from a ContentFile

    :param cf: GitHub ContentFile object
    """
    return base64.b64decode(cf.content).decode("utf-8")


def get_tool_github_repositories(g: Github, RepoSelection: Optional[str], run_test: bool) -> List[str]:
    """
    Get list of tool GitHub repositories to parse

    :param g: GitHub instance
    :param RepoSelection: The selection to use from the repository (needed to split the process for CI jobs)
    :run_test: for CI testing only use one repository
    """

    if run_test:
        return ["https://github.com/TGAC/earlham-galaxytools"]

    repo = g.get_user("galaxyproject").get_repo("planemo-monitor")
    repo_list: List[str] = []
    for i in range(1, 5):
        repo_selection = f"repositories0{i}.list"
        if RepoSelection:  # only get these repositories
            if RepoSelection == repo_selection:
                repo_f = repo.get_contents(repo_selection)
                repo_l = get_string_content(repo_f).rstrip()
                repo_list.extend(repo_l.split("\n"))
        else:
            repo_f = repo.get_contents(repo_selection)
            repo_l = get_string_content(repo_f).rstrip()
            repo_list.extend(repo_l.split("\n"))

    print("Parsing repositories from:")
    for repo in repo_list:
        print("\t", repo)

    return repo_list


def get_github_repo(url: str, g: Github) -> Repository:
    """
    Get a GitHub Repository object from an URL

    :param url: URL to a GitHub repository
    :param g: GitHub instance
    """
    if not url.startswith("https://github.com/"):
        raise ValueError
    if url.endswith("/"):
        url = url[:-1]
    if url.endswith(".git"):
        url = url[:-4]
    u_split = url.split("/")
    return g.get_user(u_split[-2]).get_repo(u_split[-1])


def get_shed_attribute(attrib: str, shed_content: Dict[str, Any], empty_value: Any) -> Any:
    """
    Get a shed attribute

    :param attrib: attribute to extract
    :param shed_content: content of the .shed.yml
    :param empty_value: value to return if attribute not found
    """
    if attrib in shed_content:
        return shed_content[attrib]
    else:
        return empty_value


def get_biotools(el: et.Element) -> Optional[str]:
    """
    Get bio.tools information

    :param el: Element object
    """
    xrefs = el.find("xrefs")
    if xrefs is not None:
        xref = xrefs.find("xref")
        if xref is not None and xref.attrib["type"] == "bio.tools":
            return xref.text
    return None


def get_conda_package(el: et.Element) -> Optional[str]:
    """
    Get conda package information

    :param el: Element object
    """
    reqs = el.find("requirements")
    if reqs is not None:
        req = reqs.find("requirement")
        if req is not None:
            return req.text
        # for req in reqs.findall('requirement'):
        #    if 'version' in req.attrib:
        #        if req.attrib['version'] == '@VERSION@' or req.attrib['version'] == '@TOOL_VERSION@':
        #            return req.text
        #        elif req.attrib['version']
        #    elif 'version' in req.attrib:
        #        return req.text
        #    else:
        #        return req.text
    return None


def check_categories(ts_categories: str, ts_cat: List[str]) -> bool:
    """
    Check if tool fit in ToolShed categories to keep

    :param ts_categories: tool ToolShed categories
    :param ts_cat: list of ToolShed categories to keep in the extraction
    """
    if not ts_cat:
        return True
    if not ts_categories:
        return False
    ts_cats = ts_categories.split(", ")
    return bool(set(ts_cat) & set(ts_cats))


def get_tool_metadata(tool: ContentFile, repo: Repository) -> Optional[Dict[str, Any]]:
    """
    Get tool metadata from the .shed.yaml, requirements in the macros or xml
    file,  bio.tools information if available in the macros or xml, EDAM
    annotations using bio.tools API, recent conda version using conda API

    :param tool: GitHub ContentFile object
    :param repo: GitHub Repository object
    """
    if tool.type != "dir":
        return None
    metadata = {
        "Galaxy wrapper id": tool.name,
        "Galaxy tool ids": [],
        "Description": None,
        "bio.tool id": None,
        "bio.tool name": None,
        "bio.tool description": None,
        "EDAM operation": [],
        "EDAM topic": [],
        "Status": "To update",
        "Source": None,
        "ToolShed categories": [],
        "ToolShed id": None,
        "Galaxy wrapper owner": None,
        "Galaxy wrapper source": None,
        "Galaxy wrapper version": None,
        "Conda id": None,
        "Conda version": None,
    }
    # extract .shed.yml information and check macros.xml
    try:
        shed = repo.get_contents(f"{tool.path}/.shed.yml")
    except Exception:
        return None
    else:
        file_content = get_string_content(shed)
        yaml_content = yaml.load(file_content, Loader=yaml.FullLoader)
        metadata["Description"] = get_shed_attribute("description", yaml_content, None)
        if metadata["Description"] is None:
            metadata["Description"] = get_shed_attribute("long_description", yaml_content, None)
        if metadata["Description"] is not None:
            metadata["Description"] = metadata["Description"].replace("\n", "")
        metadata["ToolShed id"] = get_shed_attribute("name", yaml_content, None)
        metadata["Galaxy wrapper owner"] = get_shed_attribute("owner", yaml_content, None)
        metadata["Galaxy wrapper source"] = get_shed_attribute("remote_repository_url", yaml_content, None)
        if "homepage_url" in yaml_content:
            metadata["Source"] = yaml_content["homepage_url"]
        metadata["ToolShed categories"] = get_shed_attribute("categories", yaml_content, [])
        if metadata["ToolShed categories"] is None:
            metadata["ToolShed categories"] = []
    # find and parse macro file
    file_list = repo.get_contents(tool.path)
    assert isinstance(file_list, list)
    for file in file_list:
        if "macro" in file.name and file.name.endswith("xml"):
            file_content = get_string_content(file)
            root = et.fromstring(file_content)
            for child in root:
                if "name" in child.attrib:
                    if child.attrib["name"] == "@TOOL_VERSION@" or child.attrib["name"] == "@VERSION@":
                        metadata["Galaxy wrapper version"] = child.text
                    elif child.attrib["name"] == "requirements":
                        metadata["Conda id"] = get_conda_package(child)
                    biotools = get_biotools(child)
                    if biotools is not None:
                        metadata["bio.tool id"] = biotools
    # parse XML file and get meta data from there, also tool ids
    for file in file_list:
        if file.name.endswith("xml") and "macro" not in file.name:
            file_content = get_string_content(file)
            try:
                root = et.fromstring(file_content)
            except Exception:
                print(file_content, sys.stderr)
            else:
                # version
                if metadata["Galaxy wrapper version"] is None:
                    if "version" in root.attrib:
                        version = root.attrib["version"]
                        if "VERSION@" not in version:
                            metadata["Galaxy wrapper version"] = version
                        else:
                            macros = root.find("macros")
                            if macros is not None:
                                for child in macros:
                                    if "name" in child.attrib and (
                                        child.attrib["name"] == "@TOOL_VERSION@" or child.attrib["name"] == "@VERSION@"
                                    ):
                                        metadata["Galaxy wrapper version"] = child.text
                # bio.tools
                if metadata["bio.tool id"] is None:
                    biotools = get_biotools(root)
                    if biotools is not None:
                        metadata["bio.tool id"] = biotools
                # conda package
                if metadata["Conda id"] is None:
                    reqs = get_conda_package(root)
                    if reqs is not None:
                        metadata["Conda id"] = reqs
                # tool ids
                if "id" in root.attrib:
                    metadata["Galaxy tool ids"].append(root.attrib["id"])
    # get latest conda version and compare to the wrapper version
    if metadata["Conda id"] is not None:
        r = requests.get(f'https://api.anaconda.org/package/bioconda/{metadata["Conda id"]}')
        if r.status_code == requests.codes.ok:
            conda_info = r.json()
            if "latest_version" in conda_info:
                metadata["Conda version"] = conda_info["latest_version"]
                if metadata["Conda version"] == metadata["Galaxy wrapper version"]:
                    metadata["Status"] = "Up-to-date"
    # get bio.tool information
    if metadata["bio.tool id"] is not None:
        r = requests.get(f'{BIOTOOLS_API_URL}/api/tool/{metadata["bio.tool id"]}/?format=json')
        if r.status_code == requests.codes.ok:
            biotool_info = r.json()
            if "function" in biotool_info:
                for func in biotool_info["function"]:
                    if "operation" in func:
                        for op in func["operation"]:
                            metadata["EDAM operation"].append(op["term"])
            if "topic" in biotool_info:
                for t in biotool_info["topic"]:
                    metadata["EDAM topic"].append(t["term"])
            if "name" in biotool_info:
                metadata["bio.tool name"] = biotool_info["name"]
            if "description" in biotool_info:
                metadata["bio.tool description"] = biotool_info["description"].replace("\n", "")
    return metadata


def parse_tools(repo: Repository) -> List[Dict[str, Any]]:
    """
    Parse tools in a GitHub repository, extract them and their metadata

    :param repo: GitHub Repository object
    """
    # get tool folders
    tool_folders: List[List[ContentFile]] = []
    try:
        repo_tools = repo.get_contents("tools")
    except Exception:
        try:
            repo_tools = repo.get_contents("wrappers")
        except Exception:
            print("No tool folder found", sys.stderr)
            return []
    assert isinstance(repo_tools, list)
    tool_folders.append(repo_tools)
    try:
        repo_tools = repo.get_contents("tool_collections")
    except Exception:
        pass
    else:
        assert isinstance(repo_tools, list)
        tool_folders.append(repo_tools)
    # parse folders
    tools = []
    for folder in tool_folders:
        for tool in folder:
            # to avoid API request limit issue, wait for one hour
            if g.get_rate_limit().core.remaining < 200:
                print("WAITING for 1 hour to retrieve GitHub API request access !!!")
                print()
                time.sleep(60 * 60)
            # parse tool
            try:
                repo.get_contents(f"{tool.path}/.shed.yml")
            except Exception:
                if tool.type != "dir":
                    continue
                file_list = repo.get_contents(tool.path)
                assert isinstance(file_list, list)
                for content in file_list:
                    metadata = get_tool_metadata(content, repo)
                    if metadata is not None:
                        tools.append(metadata)
            else:
                metadata = get_tool_metadata(tool, repo)
                if metadata is not None:
                    tools.append(metadata)
    return tools


def format_list_column(col: pd.Series) -> pd.Series:
    """
    Format a column that could be a list before exporting
    """
    return col.apply(lambda x: ", ".join(str(i) for i in x))


def export_tools(tools: List[Dict], output_fp: str, format_list_col: bool = False) -> None:
    """
    Export tool metadata to tsv output file

    :param tools: dictionary with tools
    :param output_fp: path to output file
    :param format_list_col: boolean indicating if list columns should be formatting
    """
    df = pd.DataFrame(tools)
    if format_list_col:
        df["ToolShed categories"] = format_list_column(df["ToolShed categories"])
        df["EDAM operation"] = format_list_column(df["EDAM operation"])
        df["EDAM topic"] = format_list_column(df["EDAM topic"])
        df["Galaxy tool ids"] = format_list_column(df["Galaxy tool ids"])
    df.to_csv(output_fp, sep="\t", index=False)


def filter_tools(tools: List[Dict], ts_cat: List[str], excluded_tools: List[str], keep_tools: List[str]) -> List[Dict]:
    """
    Filter tools for specific ToolShed categories and add information if to keep or to exclude

    :param tools: dictionary with tools and their metadata
    :param ts_cat: list of ToolShed categories to keep in the extraction
    :param excluded_tools: list of tools to skip
    :param keep_tools: list of tools to keep
    """
    filtered_tools = []
    for tool in tools:
        # filter ToolShed categories and leave function if not in expected categories
        if check_categories(tool["ToolShed categories"], ts_cat):
            name = tool["Galaxy wrapper id"]
            tool["Reviewed"] = name in keep_tools or name in excluded_tools
            tool["To keep"] = None
            if name in keep_tools:
                tool["To keep"] = True
            elif name in excluded_tools:
                tool["To keep"] = False
            filtered_tools.append(tool)
    return filtered_tools


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract Galaxy tools from GitHub repositories together with biotools and conda metadata"
    )
    subparser = parser.add_subparsers(dest="command")
    # Extract tools
    extractools = subparser.add_parser("extractools", help="Extract tools")
    extractools.add_argument("--api", "-a", required=True, help="GitHub access token")
    extractools.add_argument("--all_tools", "-o", required=True, help="Filepath to TSV with all extracted tools")
    extractools.add_argument(
        "--planemorepository", "-pr", required=False, help="Repository list to use from the planemo-monitor repository"
    )

    extractools.add_argument(
        "--test",
        "-t",
        action="store_true",
        default=False,
        required=False,
        help="Run a small test case using only the repository: https://github.com/TGAC/earlham-galaxytools",
    )

    # Filter tools
    filtertools = subparser.add_parser("filtertools", help="Filter tools")
    filtertools.add_argument(
        "--tools",
        "-t",
        required=True,
        help="Filepath to TSV with all extracted tools, generated by extractools command",
    )
    filtertools.add_argument("--filtered_tools", "-f", required=True, help="Filepath to TSV with filtered tools")
    filtertools.add_argument(
        "--categories", "-c", help="Path to a file with ToolShed category to keep in the extraction (one per line)"
    )
    filtertools.add_argument(
        "--exclude", "-e", help="Path to a file with ToolShed ids of tools to exclude (one per line)"
    )
    filtertools.add_argument("--keep", "-k", help="Path to a file with ToolShed ids of tools to keep (one per line)")
    args = parser.parse_args()

    if args.command == "extractools":
        # connect to GitHub
        g = Github(args.api)
        # get list of GitHub repositories to parse
        repo_list = get_tool_github_repositories(g, args.planemorepository, args.test)
        # parse tools in GitHub repositories to extract metada, filter by TS categories and export to output file
        tools: List[Dict] = []
        for r in repo_list:
            print("Parsing tools from:", (r))
            if "github" not in r:
                continue
            try:
                repo = get_github_repo(r, g)
                tools.extend(parse_tools(repo))
            except Exception as e:
                print(f"Error while extracting tools from repo {r}: {e}", file=sys.stderr)
        export_tools(tools, args.all_tools, format_list_col=True)
    elif args.command == "filtertools":
        tools = pd.read_csv(Path(args.tools), sep="\t", keep_default_na=False).to_dict("records")
        # get categories and tools to exclude
        categories = read_file(args.categories)
        excl_tools = read_file(args.exclude)
        keep_tools = read_file(args.keep)
        # filter tool lists
        filtered_tools = filter_tools(tools, categories, excl_tools, keep_tools)
        export_tools(filtered_tools, args.filtered_tools)
