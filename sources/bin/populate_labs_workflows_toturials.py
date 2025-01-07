import argparse
import os
from typing import List, Dict, Any
import pandas as pd
from ruamel.yaml import YAML as yaml


def matches_filter(text: str, words: List[str], logic: str) -> bool:
    """
    Determines if the given text matches the filter logic:
    - 'include': Includes the text if it matches any word in the filter.
    - 'exclude': Excludes the text if it matches any word in the filter.

    Args:
        text (str): The text to check.
        words (List[str]): A list of words to search for.
        logic (str): The filter logic, either 'include' or 'exclude'.

    Returns:
        bool: True if the text matches the filter logic, False otherwise.
    """
    # Convert text and words to lowercase for case-insensitive comparison
    text = text.lower()
    words = [word.lower() for word in words]

    if logic == "include":
        # Include if the text contains any word from the filter
        return any(word in text for word in words)

    elif logic == "exclude":
        # Exclude if the text contains any word from the filter
        return not any(word in text for word in words)

    # Default to False if the logic is not recognized
    return False


def main() -> None:
    """
    Main function to create a YAML file from a TSV file based on specified filters and logic.
    """
    # Initialize argument parser
    parser = argparse.ArgumentParser(description="Create community *.yml from *.tsv.")

    # Define required arguments
    parser.add_argument("-c", "--tsv", type=str, required=True, help="Path to the TSV file (e.g., curated_tools.tsv)")
    parser.add_argument("-y", "--yml", type=str, required=True, help="Path to the output YAML file (e.g., tools.yml)")

    # Columns and filter details
    parser.add_argument("-tc", "--title_column", type=str, required=True, help="Column to use as title.")
    parser.add_argument("-dc", "--description_column", type=str, required=True, help="Column to use as description.")
    parser.add_argument(
        "-blc", "--button_link_column", type=str, required=True, help="Column to use as link for the button."
    )
    parser.add_argument("-fc", "--filter_column", type=str, required=True, help="Column to use as filter.")
    parser.add_argument(
        "-fi", "--filter", type=str, required=True, help="Comma-separated list of words for filtering."
    )
    parser.add_argument(
        "-fl", "--filter_logic", type=str, required=True, choices=["include", "exclude"],
        help="Specify the filter logic: 'include' to include matches, 'exclude' to exclude matches."
    )

    # Parse the arguments
    args = parser.parse_args()

    # Check if the TSV file exists
    if not os.path.exists(args.tsv):
        print(f"Error: The file '{args.tsv}' does not exist.")
        return

    try:
        # Read the TSV file into a Pandas DataFrame
        data_df: pd.DataFrame = pd.read_csv(args.tsv, sep="\t")

        # Initialize the YAML data structure
        yaml_data: Dict[str, List[Dict[str, Any]]] = {"content": []}

        # Split the filter string into a list of words
        filter_words = args.filter.split(",")

        # Iterate through each row in the DataFrame
        for _index, row in data_df.iterrows():
            # Apply the filter logic
            if matches_filter(str(row[args.filter_column]), filter_words, args.filter_logic):
                # Only add rows that satisfy the filter logic
                entry: Dict[str, Any] = {
                    "title_md": row[args.title_column],
                    "description_md": row[args.description_column],
                    "button_link": row[args.button_link_column],
                }
                yaml_data["content"].append(entry)

        # Write the constructed YAML data to the output file
        with open(args.yml, "w") as yaml_file:
            yaml().dump(yaml_data, yaml_file)

        print(f"Data successfully written to '{args.yml}'")

    except Exception as e:
        # Handle any exceptions and print an error message
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
