import os
from pathlib import Path
from typing import Optional, List, Dict, Any

import mistune
import yaml
from yaml.parser import ParserError

from md2cf.confluence_renderer import ConfluenceRenderer


class Page(object):
    def __init__(
        self,
        title: Optional[str],
        body: str,
        attachments: Optional[List[Path]] = None,
        file_path: Optional[Path] = None,
        page_id: str = None,
        parent_id: str = None,
        parent_title: str = None,
        space: str = None,
    ):
        self.title = title
        self.body = body
        self.file_path = file_path
        self.attachments = attachments
        if self.attachments is None:
            self.attachments = list()
        self.page_id = page_id
        self.parent_id = parent_id
        self.parent_title = parent_title
        self.space = space


def get_pages_from_directory(file_path: Path) -> List[Page]:
    pages = list()
    full_path = file_path.resolve()
    parent_page_title = None
    path_to_amount_of_md_files = dict()
    for current_path, directories, file_names in os.walk(file_path):
        current_path = Path(current_path)
        markdown_files = [Path(current_path, file_name) for file_name in file_names if file_name.endswith('.md')]
        path_to_amount_of_md_files[current_path] = len(markdown_files)

        if not markdown_files:
            continue

        if current_path != full_path:
            pages.append(Page(title=current_path.name, body=''))
            parent_page_title = current_path.name

        for markdown_file in markdown_files:
            processed_page = get_page_data_from_file_path(markdown_file)
            processed_page.parent_title = parent_page_title
            pages.append(processed_page)

    return pages


def get_page_data_from_file_path(file_path: Path) -> Page:
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    with open(file_path) as file_handle:
        markdown_lines = file_handle.readlines()

    page = get_page_data_from_lines(markdown_lines)

    if not page.title:
        page.title = file_path.stem

    page.file_path = file_path

    return page


def get_page_data_from_lines(markdown_lines: List[str]) -> Page:
    frontmatter = get_document_frontmatter(markdown_lines)
    if "frontmatter_end_line" in frontmatter:
        markdown_lines = markdown_lines[frontmatter["frontmatter_end_line"] :]

    page = parse_page(markdown_lines)

    if "title" in frontmatter:
        page.title = frontmatter["title"]
    return page


def parse_page(markdown_lines: List[str]) -> Page:
    renderer = ConfluenceRenderer(use_xhtml=True)
    confluence_mistune = mistune.Markdown(renderer=renderer)
    confluence_content = confluence_mistune("".join(markdown_lines))

    page = Page(
        title=renderer.title, body=confluence_content, attachments=renderer.attachments
    )

    return page


def get_document_frontmatter(markdown_lines: List[str]) -> Dict[str, Any]:
    frontmatter_yaml = ""
    frontmatter_end_line = 0
    if markdown_lines and markdown_lines[0] == "---\n":
        for index, line in enumerate(markdown_lines[1:]):
            if line == "---\n":
                frontmatter_end_line = index + 2
                break
            else:
                frontmatter_yaml += line
    frontmatter = None
    if frontmatter_yaml and frontmatter_end_line:
        try:
            frontmatter = yaml.safe_load(frontmatter_yaml)
        except ParserError:
            pass
    if isinstance(frontmatter, dict):
        frontmatter["frontmatter_end_line"] = frontmatter_end_line
    else:
        frontmatter = {}

    return frontmatter
