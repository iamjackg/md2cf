import hashlib
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

import re

import mistune
import yaml
from yaml.parser import ParserError

from md2cf.ignored_files import GitRepository
from md2cf.confluence_renderer import ConfluenceRenderer


class Page(object):
    def __init__(
        self,
        title: Optional[str],
        body: str,
        attachments: Optional[List[Path]] = None,
        file_path: Optional[Path] = None,
        page_id: str = None,
        page_url: Optional[str] = None,
        parent_id: str = None,
        parent_title: str = None,
        space: str = None,
        labels: Optional[List[str]] = None,
    ):
        self.title = title
        self.body = body
        self.file_path = file_path
        self.attachments = attachments
        if self.attachments is None:
            self.attachments = list()
        self.page_id = page_id
        self.page_id = page_url
        self.parent_id = parent_id
        self.parent_title = parent_title
        self.space = space
        self.labels = labels

    def get_content_hash(self):
        return hashlib.sha1(self.body.encode()).hexdigest()

    # This function will use the file_page_map to lookup relative paths for documents that have been uploaded
    def replace_relative_paths(self, file_page_map, error_on_missing_references=False):
        # match all urls
        urls = re.findall(r'href=[\'"]?([^\'" >]+)', self.body)
        file_dir = os.path.dirname(os.path.abspath(self.file_path))
        changed = False
        for url in urls:
            # only consider urls that do not start with either http(s) or www.
            if url.startswith('http') or url.startswith('wwww'):
                continue

            # get the absolute path to the potential file
            page_file_path = os.path.abspath(os.path.join(file_dir, url))

            # check if the file exists
            if not os.path.exists(page_file_path):
                if not error_on_missing_references:
                    continue
                raise ValueError("found relative path '{}' to non-existing file '{}'".format(url, page_file_path))
            elif page_file_path not in file_page_map:
                if not error_on_missing_references:
                    continue
                raise ValueError("found relative path '{}' to file '{}' which was not marked for uplaod".format(url, page_file_path))
            else:
                # replace the relative path in the body with the page_url from previous run
                self.body = self.body.replace(url, file_page_map[page_file_path].page_url)
                changed = True
        return changed


    def __repr__(self):
        return "Page({})".format(
            ", ".join(
                [
                    "{}={}".format(name, repr(value))
                    for name, value in [
                        ["title", self.title],
                        ["file_path", self.file_path],
                        ["page_id", self.page_id],
                        ["parent_id", self.parent_id],
                        ["parent_title", self.parent_title],
                        ["space", self.space],
                    ]
                ]
            )
        )

def find_non_empty_parent_path(
    current_dir: Path, folder_data: Dict[Path, Dict[str, Any]], default: Path
) -> Path:
    for parent in current_dir.parents:
        if parent in folder_data and folder_data[parent]["n_files"]:
            return parent
    return default.absolute()


def get_pages_from_directory(
    file_path: Path,
    collapse_single_pages: bool = False,
    skip_empty: bool = False,
    collapse_empty: bool = False,
    beautify_folders: bool = False,
    use_pages_file: bool = False,
    strip_header: bool = False,
    remove_text_newlines: bool = False,
    use_gitignore: bool = True,
) -> List[Page]:
    """
    Collect a list of markdown files recursively under the file_path directory.

    :param file_path: The starting path from which to search
    :param collapse_single_pages:
    :param skip_empty:
    :param collapse_empty:
    :param beautify_folders:
    :param use_pages_file:
    :param strip_header:
    :param remove_text_newlines:
    :param use_gitignore: Use .gitignore files to skip unwanted markdown in directory search
    :return: A list of paths to the markdown files to upload.
    """
    processed_pages = list()
    base_path = file_path.resolve()
    parent_page_title = None
    folder_data = dict()
    git_repo = GitRepository(file_path, use_gitignore=use_gitignore)

    for current_path, directories, file_names in os.walk(file_path):
        current_path = Path(current_path).resolve()

        markdown_files = [
            Path(current_path, file_name)
            for file_name in file_names
            if file_name.endswith(".md")
        ]
        # Filter out ignored files
        markdown_files = [
            path for path in markdown_files if not git_repo.is_ignored(path)
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
                    current_path, folder_data, default=file_path
                )
            else:
                folder_parent_path = current_path.parent

            folder_parent_title = folder_data[folder_parent_path]["title"]
            if len(markdown_files) == 1 and collapse_single_pages:
                parent_page_title = folder_parent_title
            else:
                if collapse_empty:
                    folder_data[current_path]["title"] = str(
                        current_path.relative_to(folder_parent_path)
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
            processed_page = get_page_data_from_file_path(
                markdown_file,
                strip_header=strip_header,
                remove_text_newlines=remove_text_newlines,
            )
            processed_page.parent_title = parent_page_title
            processed_pages.append(processed_page)

            # This replaces the title for the current folder with the title for the
            # document we just parsed, so things below this folder will be correctly
            # parented to the collapsed document.
            if len(markdown_files) == 1 and collapse_single_pages:
                folder_data[current_path]["title"] = processed_page.title

    return processed_pages


def get_page_data_from_file_path(
    file_path: Path, strip_header: bool = False, remove_text_newlines: bool = False
) -> Page:
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    with open(file_path) as file_handle:
        markdown_lines = file_handle.readlines()

    page = get_page_data_from_lines(
        markdown_lines,
        strip_header=strip_header,
        remove_text_newlines=remove_text_newlines,
    )

    if not page.title:
        page.title = file_path.stem

    page.file_path = file_path

    return page


def get_page_data_from_lines(
    markdown_lines: List[str],
    strip_header: bool = False,
    remove_text_newlines: bool = False,
) -> Page:
    frontmatter = get_document_frontmatter(markdown_lines)
    if "frontmatter_end_line" in frontmatter:
        markdown_lines = markdown_lines[frontmatter["frontmatter_end_line"] :]

    page = parse_page(
        markdown_lines,
        strip_header=strip_header,
        remove_text_newlines=remove_text_newlines,
    )

    if "title" in frontmatter:
        page.title = frontmatter["title"]

    if "labels" in frontmatter:
        if isinstance(frontmatter["labels"], list):
            page.labels = [str(label) for label in frontmatter["labels"]]
        else:
            raise TypeError(
                "the labels section in the frontmatter " "must be a list of strings"
            )
    return page


def parse_page(
    markdown_lines: List[str],
    strip_header: bool = False,
    remove_text_newlines: bool = False,
) -> Page:
    renderer = ConfluenceRenderer(
        use_xhtml=True,
        strip_header=strip_header,
        remove_text_newlines=remove_text_newlines,
    )
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
