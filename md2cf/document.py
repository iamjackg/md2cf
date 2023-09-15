import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import chardet
import mistune
import yaml
from yaml.parser import ParserError

from md2cf.confluence_renderer import ConfluenceRenderer, RelativeLink
from md2cf.ignored_files import GitRepository


class Page(object):
    def __init__(
        self,
        title: Optional[str],
        body: str,
        content_type: Optional[str] = "page",
        attachments: Optional[List[Path]] = None,
        file_path: Optional[Path] = None,
        page_id: str = None,
        parent_id: str = None,
        parent_title: str = None,
        space: str = None,
        labels: Optional[List[str]] = None,
        relative_links: Optional[List[RelativeLink]] = None,
    ):
        self.title = title
        self.original_title = None
        self.body = body
        self.content_type = content_type
        self.file_path = file_path
        self.attachments = attachments
        if self.attachments is None:
            self.attachments: List[Path] = list()
        self.relative_links = relative_links
        if self.relative_links is None:
            self.relative_links: List[RelativeLink] = list()
        self.page_id = page_id
        self.parent_id = parent_id
        self.parent_title = parent_title
        self.space = space
        self.labels = labels

    def get_content_hash(self):
        return hashlib.sha1(self.body.encode()).hexdigest()

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
                        [
                            "body",
                            f"{self.body[:40]} [...]"
                            if len(self.body) > 40
                            else self.body,
                        ],
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
    enable_relative_links: bool = False,
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
    :param use_gitignore: Use .gitignore files to skip unwanted markdown in directory
      search
    :param enable_relative_links: extract all relative links and replace them with
      placeholders
    :return: A list of paths to the markdown files to upload.
    """
    processed_pages = list()
    base_path = file_path.resolve()
    folder_data = dict()
    git_repo = GitRepository(file_path, use_gitignore=use_gitignore)

    for current_path, directories, file_names in os.walk(file_path):
        current_path = Path(current_path).resolve()

        if git_repo.is_ignored(current_path):
            continue

        markdown_files = [
            Path(current_path, file_name)
            for file_name in file_names
            if file_name.endswith(".md")
        ]
        # Filter out ignored files
        markdown_files = [
            path for path in markdown_files if not git_repo.is_ignored(path)
        ]

        folder_data[current_path] = {"n_files": len(markdown_files)}

        # we'll capture title and path of the parent folder for this folder:
        folder_parent_title = None
        folder_parent_path = None

        # title for this folder's page (as parent of its children):
        parent_page_title = None
        # title for the folder (same as above except when collapsing):
        folder_title = None

        if current_path != base_path:
            # TODO: add support for .pages file to read folder title
            if skip_empty or collapse_empty:
                folder_parent_path = find_non_empty_parent_path(
                    current_path, folder_data, default=file_path
                )
            else:
                folder_parent_path = current_path.parent

            folder_parent_title = folder_data[folder_parent_path]["title"]
            parent_page_title = current_path.name
            if len(markdown_files) == 1 and collapse_single_pages:
                parent_page_title = folder_parent_title
                folder_title = None
            else:
                if collapse_empty:
                    parent_page_title = str(
                        current_path.relative_to(folder_parent_path)
                    )
                if beautify_folders:
                    parent_page_title = (
                        current_path.name.replace("-", " ")
                        .replace("_", " ")
                        .capitalize()
                    )
                folder_title = parent_page_title
        if use_pages_file and ".pages" in file_names:
            with open(current_path.joinpath(".pages")) as pages_fp:
                pages_file_contents = yaml.safe_load(pages_fp)
            if "title" in pages_file_contents:
                parent_page_title = pages_file_contents["title"]
                folder_title = parent_page_title

        folder_data[current_path]["title"] = folder_title

        if folder_title is not None and (
            markdown_files or (directories and not skip_empty and not collapse_empty)
        ):
            processed_pages.append(
                Page(
                    title=folder_title,
                    parent_title=folder_parent_title,
                    body="",
                )
            )

        for markdown_file in markdown_files:
            processed_page = get_page_data_from_file_path(
                markdown_file,
                strip_header=strip_header,
                remove_text_newlines=remove_text_newlines,
                enable_relative_links=enable_relative_links,
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
    file_path: Path,
    strip_header: bool = False,
    remove_text_newlines: bool = False,
    enable_relative_links: bool = False,
) -> Page:
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    try:
        with open(file_path) as file_handle:
            markdown_lines = file_handle.readlines()
    except UnicodeDecodeError:
        with open(file_path, "rb") as file_handle:
            detected_encoding = chardet.detect(file_handle.read())
        with open(file_path, encoding=detected_encoding["encoding"]) as file_handle:
            markdown_lines = file_handle.readlines()

    page = get_page_data_from_lines(
        markdown_lines,
        strip_header=strip_header,
        remove_text_newlines=remove_text_newlines,
        enable_relative_links=enable_relative_links,
    )

    if not page.title:
        page.title = file_path.stem

    page.file_path = file_path

    return page


def get_page_data_from_lines(
    markdown_lines: List[str],
    strip_header: bool = False,
    remove_text_newlines: bool = False,
    enable_relative_links: bool = False,
) -> Page:
    frontmatter = get_document_frontmatter(markdown_lines)
    if "frontmatter_end_line" in frontmatter:
        markdown_lines = markdown_lines[frontmatter["frontmatter_end_line"] :]

    page = parse_page(
        markdown_lines,
        strip_header=strip_header,
        remove_text_newlines=remove_text_newlines,
        enable_relative_links=enable_relative_links,
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
    enable_relative_links: bool = False,
    escape: bool = False,
    allow_harmful_protocols: bool = False
) -> Page:
    renderer = ConfluenceRenderer(
        strip_header=strip_header,
        remove_text_newlines=remove_text_newlines,
        enable_relative_links=enable_relative_links,
        escape=escape,
        allow_harmful_protocols=allow_harmful_protocols
    )
    confluence_mistune = mistune.Markdown(renderer=renderer)
    confluence_content = confluence_mistune("".join(markdown_lines))

    page = Page(
        title=renderer.title,
        body=confluence_content,
        attachments=renderer.attachments,
        relative_links=renderer.relative_links,
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
