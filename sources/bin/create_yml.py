
import yaml
import json
import re

def create_tool_yml(data_source: str, yml_output_path: str):

    with open(data_source, mode="r", encoding="utf-8") as file:
        data = json.load(file)

    ### https://stackoverflow.com/a/12595082
    ### https://stackoverflow.com/a/15340694
    for tool in range(len(data)):
        availability = {}
        for field in data[tool]:
            field_value = data[tool][field]
            availability_match_string = "[Aa]vailable on"
            if re.search(availability_match_string, field):
                instance_match_string = "[Uu]se[Gg]alaxy\.[a-z]{2}"
                if re.search(instance_match_string, field):
                    field_name = re.search(instance_match_string, field).group(0)
                if field_value != 0:
                    availability[field_name] = field_value
        data[tool]["availability"] = availability

    with open(yml_output_path, 'w') as file:
        yaml.dump(data, file, default_flow_style=False)

create_tool_yml(data_source = "./communities/all/resources/tools.json", yml_output_path = "./docs/_data/tools.yml")

def create_yml(data_source: str, yml_output_path: str):

    with open(data_source, mode="r", encoding="utf-8") as file:
        data = json.load(file)

    with open(yml_output_path, 'w') as file:
        yaml.dump(data, file, default_flow_style=False)

create_yml(data_source = "./communities/all/resources/workflows.json", yml_output_path = "./docs/_data/workflows.yml")


def create_training_yml(data_source: str, yml_output_path: str, fields: list):

    with open(data_source, mode="r", encoding="utf-8") as file:
        data = json.load(file)

    updated_training_data = {}

    for training in data:
        id = training["id"]
        updated_training_data[id] = {}
        for field in fields:
            if field in training:
                updated_training_data[id][field] = training[field]

    with open(yml_output_path, 'w') as file:
        yaml.dump(updated_training_data, file, default_flow_style=False)

required_fields = ["title", "hands_on", "url", "slides", "mod_date", "pub_date", "version", "short_tools", "exact_supported_servers","inexact_supported_servers", "topic_name_human", "video", "edam_topic", "edam_operation", "feedback_number", "feedback_mean_note", "visitors", "pageviews", "visit_duration", "video_versions", "video_view"]

create_training_yml(data_source = "./communities/all/resources/tutorials.json", yml_output_path = "./docs/_data/tutorials.yml", fields = required_fields)
