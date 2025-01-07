# python ./sources/bin/populate_labs.py --tool_tsv communities/microgalaxy/resources/curated_tools.tsv --tool_yml communities/microgalaxy/lab/sections/4_tools.yml

import argparse
import os
from typing import List

import pandas as pd
from ruamel.yaml import YAML as yaml
from ruamel.yaml.scalarstring import LiteralScalarString

number_of_categories = 10
number_of_tools = 10


def add_tools_url(tools) -> None:
    return tools


def main() -> None:
    parser = argparse.ArgumentParser(description="Create community tools.yml from tool.tsv.")

    # Adding positional arguments with short options
    parser.add_argument(
        "-c", "--tool_tsv", type=str, required=True, help="Path to the TSV file (e.g., curated_tools.tsv)"
    )
    parser.add_argument(
        "-y", "--tool_yml", type=str, required=True, help="Path to the output YAML file (e.g., tools.yml)"
    )

    args = parser.parse_args()

    # Check if the tool TSV file exists
    if not os.path.exists(args.tool_tsv):
        print(f"Error: The file '{args.tool_tsv}' does not exist.")
        return

    try:
        # Read the TSV file with pandas (use tab delimiter)
        tools = pd.read_csv(args.tool_tsv, sep="\t")

        # Construct the YAML data structure
        yaml_data = {
            "id": "tools",
            "title": "Community curated tools",
            "tabs": [],
        }

        #################################
        # Add manual entry for tool request and complete list
        #################################

        entries = []

        # Tool request
        entry = {
            "title_md": "Request a new tool",
            "description_md": "You can request a new tool by contacting the microGalaxy community: microgalaxy@lists.galaxyproject.org",
        }
        entries.append(entry)

        # Complete tool list
        entry = {
            "title_md": "See the complete tool list",
            "description_md": "Our comprehensive curated tool list is available via https://galaxyproject.github.io/galaxy_codex/microgalaxy",
        }
        entries.append(entry)

        # Add manual entries to the top of the tabs
        yaml_data["tabs"].append(
            {
                "id": "more_tools",
                "title": "More tools !",
                "heading_md": f"Request a new tools or look at the complete list",
                "content": entries,
            }
        )

        #######################################
        # Get highest ranking EDAM operations
        #######################################

        count_column = "Suite runs on main servers"

        # Step 1: Split the categories into separate rows and strip whitespace
        df = tools.assign(Category=tools["EDAM operations"].str.split(",")).explode("Category")
        df["Category"] = df["Category"].str.strip()  # Strip whitespace

        # Step 2: Group by category to calculate total count and item count
        grouped = (
            df.groupby("Category")
            .agg(
                total_count=(count_column, "sum"),
                item_count=("Suite ID", "size"),  # Count distinct items if necessary, use 'nunique'
            )
            .reset_index()
        )

        # Step 3: Filter categories with at least 5 items
        filtered = grouped[grouped["item_count"] >= 5]

        ###########################
        # Get the corresponding tools
        ###########################

        # Step 4: Sort by total count in descending order
        top_categories = filtered.sort_values(by="total_count", ascending=False).head(number_of_categories)["Category"]

        # Step 5: Assign each tool to the first category it appears in
        # Sort by 'Galaxy wrapper id' to ensure we assign based on first appearance
        df_unique = df[df["Category"].isin(top_categories)]  # Filter rows for top 5 categories
        df_unique = df_unique.sort_values(by=["Suite ID", "Category"])  # Sort by tool ID to keep first category only

        # Step 6: Remove duplicates, keeping the first appearance of each tool
        df_unique = df_unique.drop_duplicates(subset=["Suite ID"], keep="first")

        # Step 7: Extract top 5 items per category based on total count
        top_items_per_category = (
            df_unique.groupby("Category", group_keys=False)  # Group by category
            .apply(lambda group: group.nlargest(number_of_tools, count_column))  # Get top items per category
            .reset_index(drop=True)  # Reset index for clean output
        )

        #############################
        # Populate the table
        #############################

        for group_id, group in top_items_per_category.groupby("Category"):

            tool_entries = []
            for index, row in group.iterrows():

                # Prepare the description with an HTML unordered list and links for each Galaxy tool ID
                description = f"{row['Description']}\n (Tool usage: {row[count_column]})"
                tool_ids = row["Tool IDs"]
                owner = row["Suite owner"]
                wrapper_id = row["Suite ID"]

                # Split the tool IDs by comma if it's a valid string, otherwise handle as an empty list
                tool_ids_list = tool_ids.split(",") if isinstance(tool_ids, str) else []

                # Create the base URL template for each tool link
                url_template = (
                    "/tool_runner?tool_id=toolshed.g2.bx.psu.edu%2Frepos%2F{owner}%2F{wrapper_id}%2F{tool_id}"
                )

                # Build HTML list items with links
                description += "\n<ul>\n"
                for tool_id in tool_ids_list:
                    tool_id = tool_id.strip()  # Trim whitespace
                    # Format the URL with owner, wrapper ID, and tool ID
                    url = url_template.format(owner=owner, wrapper_id=wrapper_id, tool_id=tool_id)
                    url = "{{ galaxy_base_url }}" + url
                    description += f'  <li><a href="{url}">{tool_id}</a></li>\n'
                description += "</ul>"

                # Use LiteralScalarString to enforce literal block style for the description
                description_md = LiteralScalarString(description.strip())

                # Create the tool entry
                tool_entry = {
                    "title_md": wrapper_id,
                    "description_md": description_md,
                }

                tool_entries.append(tool_entry)

            # Create table entry for each EDAM
            yaml_data["tabs"].append(
                {
                    "id": group_id.replace(" ", "_").lower(),
                    "title": group_id,
                    "heading_md": f"Top 10 for the EDAM operation: {group_id}",
                    "content": tool_entries,
                }
            )

        # Write the YAML data to the output file
        with open(args.tool_yml, "w") as yaml_file:
            yaml().dump(yaml_data, yaml_file)
        print(f"Data successfully written to '{args.tool_yml}'")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
