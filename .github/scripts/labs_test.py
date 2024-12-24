"""Build URLs for each Lab page for Labs that have been changed in this PR.

Test each URL to see if it returns a 200 status code, and post the results
in a PR comment.
"""

import os
import sys
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

OUTPUT_DIR = "output"
COMMENT_TITLE_TEMPLATE = "Preview changes to {lab_name} Lab <!--=-->"
URL_TEMPLATE = (
    "https://labs.usegalaxy.org.au"
    "/?content_root=https://github.com/{repo}"
    "/blob/{branch_name}/{lab_content_path}"
    "&cache=false"
)
TRY_FILES = [
    'base.yml',
    'usegalaxy.eu.yml',
    'usegalaxy.org.yml',
    'usegalaxy.org.au.yml',
]

# Environment variables from GitHub Actions
BRANCH_NAME = os.environ["BRANCH_NAME"]
HEAD_REPO = os.getenv("HEAD_REPO")


def test_lab(lab_name):
    """Iterate through each YAML root file for the given lab name.
    For files that exist, build a URL for that Lab page, check the HTTP status
    code and post the URLs with pass/fail status as a comment on the PR.
    """
    success = True
    title_string = COMMENT_TITLE_TEMPLATE.format(lab_name=lab_name)
    comment_md = f"### {title_string}\n\n"
    test_paths = [
        f'communities/{lab_name}/lab/{f}'
        for f in TRY_FILES
    ]

    for path in test_paths:
        if not os.path.exists('head/' + path):
            print(f"Skipping {path}: file not found in head repo")
            continue
        url = build_url(path)
        try:
            http_status = http_status_for(url)
            filename = path.split('/')[-1]
            if http_status < 400:
                line = f"- ✅ {filename} [HTTP {http_status}]: {url}\n\n"
            else:
                line = f"- ❌ {filename} [HTTP {http_status}]: {url}\n\n"
                success = False
        except URLError as exc:
            line = f"- ❌ {filename} [URL ERROR]: {url}\n\n```\n{exc}\n```"
            success = False
        comment_md += line

    if not success:
        comment_md += (
            "\n\n"
            "🚨 One or more Lab pages are returning an error. "
            "Please follow the link to see details of the issue."
        )

    write_comment(lab_name, comment_md)
    return success


def write_comment(lab_name, md):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(f'{OUTPUT_DIR}/{lab_name}.md', 'w') as f:
        f.write(md)


def http_status_for(url):
    try:
        response = urlopen(url)
        return response.getcode()
    except HTTPError as e:
        return e.code


def build_url(content_path):
    return URL_TEMPLATE.format(
        repo=HEAD_REPO,
        branch_name=BRANCH_NAME,
        lab_content_path=content_path)


def main():
    path = sys.argv[1] if len(sys.argv) else "paths.txt"
    with open(path) as f:
        files = f.read().splitlines()

    success = True
    directories = []

    # Check each file to see if it is in a "Lab" directory
    for path in files:
        if path.startswith("communities/") and "/lab/" in path:
            lab_name = path.split("/")[1]
            if lab_name not in directories:
                print(f"Detected change to {lab_name} Lab in file: {path}")
                print(f"Testing {lab_name}...")
                directories.append(lab_name)
                result = test_lab(lab_name)
                success = success and result
        else:
            print(f"Ignoring changes to {path}: not in a lab directory")

    if not success:
        raise ValueError("One or more Lab pages returned an HTTP error.")


if __name__ == "__main__":
    main()
