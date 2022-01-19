import hashlib
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

    def get_content_hash(self):
        return hashlib.sha1(self.body.encode()).hexdigest()


def find_non_empty_parent_path(
    current_dir: Path, folder_data: Dict[Path, Dict[str, Any]]
) -> Path:
    for parent in current_dir.parents:
        if folder_data[parent]["n_files"]:
            return parent


def get_pages_from_directory(
    file_path: Path,
    collapse_single_pages: bool = False,
    skip_empty: bool = False,
    collapse_empty: bool = False,
    beautify_folders: bool = False,
    use_pages_file: bool = False,
) -> List[Page]:
    processed_pages = list()
    base_path = file_path.resolve()
    parent_page_title = None
    folder_data = dict()
    for current_path, directories, file_names in os.walk(file_path):
        current_path = Path(current_path).resolve()

        markdown_files = [
            Path(current_path, file_name)
            for file_name in file_names
            if file_name.endswith(".md")
        ]

        folder_data[current_path] = {
            "n_files": len(markdown_files),
            "title": current_path.name if current_path != base_path else None,
        }

        if not markdown_files and not directories:
            continue

        if not markdown_files and (skip_empty or collapse_empty):
            continue

        if current_path != base_path:
            # TODO: add support for .pages file to read folder title
            if skip_empty or collapse_empty:
                folder_parent_path = find_non_empty_parent_path(
                    current_path, folder_data
                )
            else:
                folder_parent_path = current_path.parent

            folder_parent_title = folder_data[folder_parent_path]["title"]

            if len(markdown_files) == 1 and collapse_single_pages:
                parent_page_title = folder_parent_title
            else:
                if collapse_empty:
                    folder_data[current_path]["title"] = current_path.relative_to(
                        folder_parent_path
                    )
                if beautify_folders:
                    folder_data[current_path]["title"] = (
                        folder_data[current_path]["title"]
                        .replace("-", " ")
                        .replace("_", " ")
                        .capitalize()
                    )
                elif use_pages_file and ".pages" in file_names:
                    with open(current_path.joinpath(".pages")) as pages_fp:
                        pages_file_contents = yaml.safe_load(pages_fp)
                    if "title" in pages_file_contents:
                        folder_data[current_path]["title"] = pages_file_contents[
                            "title"
                        ]
                parent_page_title = folder_data[current_path]["title"]
                processed_pages.append(
                    Page(
                        title=parent_page_title,
                        parent_title=folder_parent_title,
                        body="",
                    )
                )

        for markdown_file in markdown_files:
            processed_page = get_page_data_from_file_path(markdown_file)
            processed_page.parent_title = parent_page_title
            processed_pages.append(processed_page)

            # This replaces the title for the current folder with the title for the
            # document we just parsed, so things below this folder will be correctly
            # parented to the collapsed document.
            if len(markdown_files) == 1 and collapse_single_pages:
                folder_data[current_path]["title"] = processed_page.title

    return processed_pages


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
