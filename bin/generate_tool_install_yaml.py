#!/usr/bin/env python

import argparse

import pandas as pd
import yaml

COLUMNS = {
    "Galaxy tool ids": "name",
    "Galaxy wrapper owner": "owner",
    "EDAM operation": "tool_panel_section_label",
}


def generate_install_yaml(
    tsv_path: str,
    output_path: str,
) -> None:
    df = pd.read_csv(tsv_path, sep="\t").assign(Expand=lambda df: "").fillna("")
    if "To keep" in df.columns:
        df["To keep"] = df["To keep"].replace("", False)
        df = df.query("`To keep`")
    columns_to_keep = list(COLUMNS.keys())
    df = df.loc[:, columns_to_keep].reindex(columns=columns_to_keep).rename(columns=COLUMNS)
    df["name"] = df["name"].str.split(", ")
    df = df.explode("name")

    tool_dict = {
        "install_tool_dependencies": True,
        "install_repository_dependencies": True,
        "install_resolver_dependencies": True,
        "tools": df.to_dict("records"),
    }

    with open(output_path, "w") as output:
        yaml.dump(tool_dict, output, default_flow_style=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate the YAML to install the tools on a Galaxy server \
            from TSV file"
    )
    parser.add_argument(
        "--table",
        "-ta",
        required=True,
        help="Path to TSV file with tools",
    )
    parser.add_argument(
        "--output",
        "-out",
        required=True,
        help="Path to YAML output",
    )

    args = parser.parse_args()
    generate_install_yaml(args.table, args.output)
