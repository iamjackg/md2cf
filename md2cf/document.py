from pathlib import Path

import mistune
import yaml
from yaml.parser import ParserError

from md2cf.confluence_renderer import ConfluenceRenderer


def get_page_data_from_file_path(file_path):
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    with open(file_path) as file_handle:
        markdown_lines = file_handle.readlines()

    page_data = get_page_data_from_lines(markdown_lines)

    if "title" not in page_data:
        page_data["title"] = file_path.stem

    return page_data


def get_page_data_from_lines(markdown_lines):
    metadata = get_document_metadata(markdown_lines)
    if "metadata_end_line" in metadata:
        markdown_lines = markdown_lines[metadata['metadata_end_line']:]

    page_data = parse_page(markdown_lines)

    if "title" in metadata:
        page_data["title"] = metadata["title"]
    return page_data


def parse_page(markdown_lines):
    renderer = ConfluenceRenderer(use_xhtml=True)
    confluence_mistune = mistune.Markdown(renderer=renderer)
    confluence_content = confluence_mistune("".join(markdown_lines))

    page_data = {
        "title": renderer.title,
        "body": confluence_content,
        "attachments": renderer.attachments,
    }

    return page_data


def get_document_metadata(markdown_lines):
    metadata_yaml = ""
    metadata_end_line = 0
    if markdown_lines and markdown_lines[0] == "---\n":
        for index, line in enumerate(markdown_lines[1:]):
            if line == "---\n":
                metadata_end_line = index + 2
                break
            else:
                metadata_yaml += line
    metadata = None
    if metadata_yaml and metadata_end_line:
        try:
            metadata = yaml.safe_load(metadata_yaml)
        except ParserError:
            pass
    if isinstance(metadata, dict):
        metadata["metadata_end_line"] = metadata_end_line
    else:
        metadata = {}

    return metadata
