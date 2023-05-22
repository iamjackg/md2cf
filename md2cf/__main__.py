import argparse
import copy
import getpass
import os
import sys
from collections import Counter
from pathlib import Path
from typing import List

import rich.table
import rich.text
import rich.tree
from requests import HTTPError
from rich import box
from rich_argparse import RichHelpFormatter

import md2cf.document
from md2cf import api
from md2cf.console_output import (
    console,
    error_console,
    json_output_console,
    minimal_output_console,
)
from md2cf.document import Page
from md2cf.tui import Md2cfTUI
from md2cf.upsert import upsert_attachment, upsert_page


def get_parser():
    parser = argparse.ArgumentParser(formatter_class=RichHelpFormatter)
    login_group = parser.add_argument_group("login arguments")
    login_group.add_argument(
        "-o",
        "--host",
        help="full URL of the Confluence instance. "
        "Can also be specified as CONFLUENCE_HOST environment variable.",
        default=os.getenv("CONFLUENCE_HOST"),
    )
    login_group.add_argument(
        "-u",
        "--username",
        help="username for logging into Confluence. "
        "Can also be specified as CONFLUENCE_USERNAME environment variable.",
        default=os.getenv("CONFLUENCE_USERNAME"),
    )
    login_group.add_argument(
        "-p",
        "--password",
        help="password for logging into Confluence. "
        "Can also be specified as CONFLUENCE_PASSWORD environment variable. "
        "If not specified, it will be asked for interactively.",
        default=os.getenv("CONFLUENCE_PASSWORD"),
    )
    login_group.add_argument(
        "--token",
        help="personal access token for logging into Confluence. "
        "Can also be specified as CONFLUENCE_TOKEN environment variable.",
        default=os.getenv("CONFLUENCE_TOKEN"),
    )
    login_group.add_argument(
        "--insecure",
        action="store_true",
        help="do not verify SSL certificates",
    )

    required_group = parser.add_argument_group("required arguments")
    required_group.add_argument(
        "-s",
        "--space",
        help="key for the Confluence space the page will be published to. "
        "Can also be specified as CONFLUENCE_SPACE environment variable.",
        default=os.getenv("CONFLUENCE_SPACE"),
    )

    output_group = parser.add_argument_group("md2cf output arguments")
    output_group.add_argument(
        "--output",
        choices=["default", "minimal", "json"],
        default="default",
    )

    page_group = parser.add_argument_group("page information arguments")
    parent_group = page_group.add_mutually_exclusive_group()
    parent_group.add_argument(
        "-a",
        "--parent-title",
        help="title of the parent page under which the new page will be uploaded",
    )
    parent_group.add_argument(
        "-A",
        "--parent-id",
        help="ID of the parent page under which the new page will be uploaded",
    )
    parent_group.add_argument(
        "--top-level",
        action="store_true",
        help="upload the page tree starting from the top level (no top level parent)",
    )

    page_group.add_argument(
        "-t",
        "--title",
        help="a title for the page. Determined from the document if missing",
    )

    page_group.add_argument(
        "-c",
        "--content-type",
        help="Content type. Default value: page",
        choices=["page", "blogpost"],
        default="page",
    )

    page_group.add_argument("-m", "--message", help="update message for the change")
    page_group.add_argument(
        "--minor-edit", action="store_true", help="do not notify watchers of change"
    )
    page_group.add_argument("-i", "--page-id", help="ID of the page to be updated")
    page_group.add_argument(
        "--prefix",
        help="a string to prefix to every page title to ensure uniqueness",
        type=str,
    )
    page_group.add_argument(
        "--strip-top-header",
        action="store_true",
        help="remove the top level header from the page",
    )
    page_group.add_argument(
        "--remove-text-newlines",
        action="store_true",
        help="remove single newlines in paragraphs",
    )
    page_group.add_argument(
        "--replace-all-labels",
        action="store_true",
        help="replace all labels instead of only adding new ones",
    )

    preface_group = page_group.add_mutually_exclusive_group()
    preface_group.add_argument(
        "--preface-markdown",
        nargs="?",
        type=str,
        default=None,
        const="**Contents are auto-generated, do not edit.**",
        help="markdown content to prepend to each page. "
        'Defaults to "**Contents are auto-generated, do not edit.**" '
        "if no markdown is specified",
    )
    preface_group.add_argument(
        "--preface-file",
        type=Path,
        help="path to a markdown file to be prepended to every page",
    )

    postface_group = page_group.add_mutually_exclusive_group()
    postface_group.add_argument(
        "--postface-markdown",
        nargs="?",
        type=str,
        default=None,
        const="**Contents are auto-generated, do not edit.**",
        help="markdown content to append to each page. "
        'Defaults to "**Contents are auto-generated, do not edit.**" '
        "if no markdown is specified",
    )
    postface_group.add_argument(
        "--postface-file",
        type=Path,
        help="path to a markdown file to be appended to every page",
    )

    dir_group = parser.add_argument_group("directory arguments")
    dir_group.add_argument(
        "--collapse-single-pages",
        action="store_true",
        help="if a folder contains a single document, collapse it "
        "so the folder doesn't appear",
    )
    dir_group.add_argument(
        "--no-gitignore",
        action="store_false",
        dest="use_gitignore",
        default=True,
        help="do not use .gitignore files to filter directory search",
    )
    dir_title_group = dir_group.add_mutually_exclusive_group()
    dir_title_group.add_argument(
        "--beautify-folders",
        action="store_true",
        help="replace hyphens and underscore in folder names with spaces, "
        "and capitalize the first letter",
    )
    dir_title_group.add_argument(
        "--use-pages-file",
        action="store_true",
        help='use the "title" entry in YAML files called .pages in each '
        "directory to change the folder name",
    )

    empty_group = dir_group.add_mutually_exclusive_group()
    empty_group.add_argument(
        "--collapse-empty",
        action="store_true",
        help="collapse multiple empty folders into one",
    )
    empty_group.add_argument(
        "--skip-empty",
        action="store_true",
        help="if a folder doesn't contain documents, skip it",
    )

    relative_links_group = parser.add_argument_group("relative links arguments")
    relative_links_group.add_argument(
        "--enable-relative-links",
        action="store_true",
        help="enable parsing of relative links to other markdown files. "
        "Requires two passes for pages with relative links, and will cause them "
        "to always be updated regardless of the --only-changed flag",
    )
    relative_links_group.add_argument(
        "--ignore-relative-link-errors",
        action="store_true",
        help="when relative links are enabled and a link doesn't point to an "
        "existing and uploaded file, leave the link as-is instead of exiting.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print information on all the pages instead of uploading to Confluence",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="print full stack traces for exceptions",
    )
    parser.add_argument(
        "--only-changed",
        action="store_true",
        help="only upload pages and attachments that have changed. "
        "This adds a hash of the page or attachment contents to the update message",
    )
    parser.add_argument(
        "file_list",
        type=Path,
        help="markdown files or directories to upload to Confluence. Empty for stdin",
        nargs="*",
    )

    return parser


def print_missing_parameter(parameter_name: str):
    error_console.log(
        ":x: Missing required parameter: {}\n"
        "Use {} --help to get help.".format(parameter_name, sys.argv[0])
    )


def print_page_details(page: Page):
    page_copy = copy.copy(page)
    page_copy.body = page_copy.body[:40] + ("..." if page_copy.body else "")
    console.print(page_copy)


def main():
    args = get_parser().parse_args()

    if args.host is None:
        print_missing_parameter("host")
        sys.exit(1)

    if args.username is None and args.token is None:
        print_missing_parameter("username or bearer token")
        sys.exit(1)

    if args.space is None:
        print_missing_parameter("space")
        sys.exit(1)

    if args.password is None and args.token is None:
        args.password = getpass.getpass()

    if args.output == "minimal":
        console.quiet = True
        minimal_output_console.quiet = False
    elif args.output == "json":
        console.quiet = True
        json_output_console.quiet = False

    confluence = api.MinimalConfluence(
        host=args.host,
        username=args.username,
        password=args.password,
        token=args.token,
        verify=not args.insecure,
    )

    if (args.title or args.page_id) and (
        len(args.file_list) > 1 or any(map(os.path.isdir, args.file_list))
    ):
        error_console.log(
            ":x: Title and page ID cannot be specified on the command line "
            "if uploading more than one file or whole directories\n"
        )
        sys.exit(1)

    pages_to_upload = collect_pages_to_upload(args)

    page_title_counts = Counter([page.title for page in pages_to_upload])
    colliding_titles = [
        title for title, count in page_title_counts.most_common() if count > 1
    ]
    if colliding_titles:
        error_console.log(
            ":x: Some documents have the [bold]same title[/], but all Confluence pages "
            "in the same space must have different titles.\n\n"
            "These are the documents (and path, if available) with identical titles:",
            markup=True,
        )
        colliding_titles_table = rich.table.Table(box=box.SIMPLE)
        colliding_titles_table.add_column("Title")
        colliding_titles_table.add_column("File")
        for title in colliding_titles:
            for filename in [
                page.file_path for page in pages_to_upload if page.title == title
            ]:
                # error_console.log(f"{title}\t{filename}\n", markup=True)
                colliding_titles_table.add_row(title, str(filename))
        error_console.log(colliding_titles_table)
        sys.exit(1)

    for page in pages_to_upload:
        for attachment in page.attachments:
            if page.file_path is not None:
                attachment_path = page.file_path.parent.joinpath(attachment)
            else:
                attachment_path = attachment

            if not attachment_path.is_file():
                error_console.log(
                    f"[bold red]:x: ERROR:[default] attachment {attachment_path} "
                    f"for page {page.title} does not exist"
                )
                sys.exit(1)

    preface_markup = ""
    if args.preface_markdown:
        preface_markup = md2cf.document.parse_page([args.preface_markdown]).body
    elif args.preface_file:
        # We don't use strip_header or remove_text_newlines here
        # since this is just a preface doc
        preface_markup = md2cf.document.get_page_data_from_file_path(
            args.preface_file
        ).body

    postface_markup = ""
    if args.postface_markdown:
        postface_markup = md2cf.document.parse_page([args.postface_markdown]).body
    elif args.postface_file:
        # We don't use strip_header or remove_text_newlines here
        # since this is just a postface doc
        postface_markup = md2cf.document.get_page_data_from_file_path(
            args.postface_file
        ).body

    map_document_path_to_confluence_page = dict()
    if args.enable_relative_links:
        map_document_path_to_confluence_page = build_document_path_to_page_map(
            pages_to_upload
        )
        if not args.ignore_relative_link_errors:
            validate_relative_links(
                pages_to_upload, map_document_path_to_confluence_page
            )

    something_went_wrong = False
    error = None
    tui = Md2cfTUI(pages_to_upload)
    with tui:
        space_info = confluence.get_space(
            args.space, additional_expansions=["homepage"]
        )

        for page in pages_to_upload:
            pre_process_page(page, args, postface_markup, preface_markup, space_info)
            tui.start_item_task(page.original_title)
            upsert_page_result = None
            try:
                tui.set_item_progress_label(page.original_title, "Upserting")
                final_page = None
                if not args.dry_run:
                    upsert_page_result = upsert_page(
                        confluence=confluence,
                        message=args.message,
                        page=page,
                        only_changed=args.only_changed,
                        replace_all_labels=args.replace_all_labels,
                        minor_edit=args.minor_edit,
                    )
                    final_page = upsert_page_result.response
                    minimal_output_console.log(confluence.get_url(final_page))
                    json_output_console.print_json(data=final_page, indent=None)
                if page.attachments:
                    tui.set_item_progress_label(
                        page.original_title, "Processing attachments"
                    )
                    for attachment in page.attachments:
                        attachment_identifier = f"{page.original_title} {attachment}"
                        tui.start_item_task(attachment_identifier)
                        if not args.dry_run:
                            upsert_attachment_result = upsert_attachment(
                                confluence=confluence,
                                attachment=attachment,
                                existing_page=final_page,
                                message=args.message,
                                only_changed=args.only_changed,
                                page=page,
                            )
                            tui.set_item_finished_text_from_result(
                                attachment_identifier, upsert_attachment_result
                            )
                        else:
                            tui.set_item_finished_text(
                                attachment_identifier, "[yellow]Skipped (dry run)"
                            )
                        tui.set_item_progress_label(attachment_identifier, "")
                        tui.tick_item_progress(attachment_identifier)
                        tui.tick_item_progress(page.original_title)
                        tui.tick_global_progress()
                if page.file_path is not None and args.enable_relative_links:
                    # Skip pages without a file_path
                    # (e.g. section pages representing directories)
                    map_document_path_to_confluence_page[
                        page.file_path.resolve()
                    ] = final_page
            except HTTPError as e:
                if args.debug:
                    console.print_exception(show_locals=True)
                error = "{} - {}".format(str(e), e.response.content)
                something_went_wrong = True
            except Exception as e:
                if args.debug:
                    console.print_exception(show_locals=True)
                error = "[red]ERROR:[default] {}".format(str(e))
                something_went_wrong = True

            tui.set_item_progress_label(page.original_title, "")
            if not args.dry_run:
                if not something_went_wrong:
                    tui.set_item_finished_text_from_result(
                        page.original_title, upsert_page_result
                    )
                else:
                    tui.set_item_progress_label(
                        page.original_title, "[red]:x: Error while uploading"
                    )
            else:
                tui.set_item_finished_text(
                    page.original_title,
                    rich.text.Text.from_markup("[yellow]Skipped (dry run)"),
                )

            tui.tick_item_progress(page.original_title)
            tui.tick_global_progress()

            if something_went_wrong:
                break

        if not something_went_wrong and args.enable_relative_links:
            try:
                update_pages_with_relative_links(
                    args,
                    confluence,
                    pages_to_upload,
                    map_document_path_to_confluence_page,
                    tui,
                )
            except HTTPError as e:
                if args.debug:
                    console.print_exception(show_locals=True)
                error = "{} - {}".format(str(e), e.response.content)
                something_went_wrong = True
            except Exception as e:
                if args.debug:
                    console.print_exception(show_locals=True)
                error = "[red]ERROR:[default] {}".format(str(e))
                something_went_wrong = True

    if something_went_wrong:
        error_console.log(error)
        sys.exit(1)


def pre_process_page(page, args, postface_markup, preface_markup, space_info):
    page.original_title = page.title
    page.space = args.space
    page.page_id = args.page_id
    page.content_type = args.content_type

    if page.parent_title is None:  # This only happens for top level pages
        # If the argument is not supplied this leaves
        # the parent_title as None, which is fine
        page.parent_title = args.parent_title
    else:
        if args.prefix:
            page.parent_title = f"{args.prefix} - {page.parent_title}"

    if page.parent_title is None:
        page.parent_id = (
            page.parent_id or args.parent_id
        )  # This can still end up being None.
        # It's fine -- it means it's a top level page.

    # If we want to *move* a page back to the top space, we need to make it
    # a child of the space's home page
    if args.top_level and page.parent_title is None and page.parent_id is None:
        page.parent_id = space_info.homepage.id

    if args.prefix:
        page.title = f"{args.prefix} - {page.title}"

    if preface_markup:
        page.body = preface_markup + page.body

    if postface_markup:
        page.body = page.body + postface_markup


def validate_relative_links(pages_to_upload, path_to_page):
    invalid_links = False
    for page in pages_to_upload:
        for link_data in page.relative_links:
            link_absolute_path = (
                page.file_path.parent / Path(link_data.path)
            ).resolve()
            if link_absolute_path not in path_to_page:
                error_console.log(
                    f"Page {page.file_path} has a relative link to {link_data.path}"
                    ", which is not in the list of pages to be uploaded.\n"
                )
                invalid_links = True
    if invalid_links:
        error_console.log(
            "\nSome of the pages to be uploaded have invalid relative links.\n"
        )
        sys.exit(1)


def build_document_path_to_page_map(pages_to_upload):
    path_to_page = dict()
    for page in pages_to_upload:
        try:
            # Will be filled in later with the page returned by upsert
            path_to_page[page.file_path.resolve()] = None
        except AttributeError:
            # A page might not have a file_path
            # (for example if it's representing a directory)
            continue
    return path_to_page


def update_pages_with_relative_links(
    args, confluence, pages_to_upload, path_to_page, tui
):
    something_went_wrong = False
    error = ""
    for page in pages_to_upload:
        if page.file_path is None:
            # Skip pages without a file_path
            # (e.g. section pages representing directories)
            continue

        page_modified = False
        for link_data in page.relative_links:
            try:
                link_absolute_path = (
                    page.file_path.parent / Path(link_data.path)
                ).resolve()
                page_on_confluence = path_to_page[link_absolute_path]
            except KeyError:
                if args.ignore_relative_link_errors:
                    page.body = page.body.replace(
                        link_data.replacement, link_data.escaped_original
                    )
                    continue
                else:
                    error_console.log(
                        f"Page {page.file_path} has a relative link to {link_data.path}"
                        ", which was not uploaded correctly.\n"
                    )
                    break

            # in a dry run we don't actually have page URLs since we never upload
            # anything
            if not args.dry_run:
                page.body = page.body.replace(
                    link_data.replacement, confluence.get_url(page_on_confluence)
                )
            page_modified = True

        if page_modified:
            tui.reset_item_task(page.original_title, total=1)
            tui.set_item_progress_label(page.original_title, "Updating relative links")
            tui.start_item_task(page.original_title)
            if not args.dry_run:
                try:
                    upsert_page(
                        confluence=confluence,
                        message=args.message,
                        page=page,
                        only_changed=args.only_changed,
                        replace_all_labels=args.replace_all_labels,
                        minor_edit=True,
                    )
                except Exception as e:
                    error = e
                    something_went_wrong = True

                if not something_went_wrong:
                    tui.set_item_finished_text(
                        page.original_title,
                        rich.text.Text.from_markup(
                            "[green]:heavy_check_mark-emoji: Updated "
                            "(updated relative links)"
                        ),
                    )
                else:
                    tui.set_item_progress_label(
                        page.original_title,
                        "[red]:x: Error while updating relative links",
                    )
            else:
                tui.set_item_finished_text(
                    page.original_title,
                    rich.text.Text.from_markup(
                        "[yellow]Not updating relative links (dry run)"
                    ),
                )

            tui.set_item_progress_label(page.original_title, "")
            tui.tick_item_progress(page.original_title)

        if something_went_wrong:
            raise error


def collect_pages_to_upload(args):
    pages_to_upload: List[Page] = list()
    if not args.file_list:  # Uploading from standard input
        pages_to_upload.append(
            md2cf.document.get_page_data_from_lines(
                sys.stdin.readlines(),
                strip_header=args.strip_top_header,
                remove_text_newlines=args.remove_text_newlines,
                enable_relative_links=False,
            )
        )

        if not (pages_to_upload[0].title or args.title):
            error_console.log(
                "You must specify a title or have a title in the document "
                "if uploading from standard input\n"
            )
            sys.exit(1)

        if args.title:
            pages_to_upload[0].title = args.title
    else:
        for file_name in args.file_list:
            if file_name.is_dir():
                pages_to_upload += md2cf.document.get_pages_from_directory(
                    file_name,
                    collapse_single_pages=args.collapse_single_pages,
                    skip_empty=args.skip_empty,
                    collapse_empty=args.collapse_empty,
                    beautify_folders=args.beautify_folders,
                    remove_text_newlines=args.remove_text_newlines,
                    strip_header=args.strip_top_header,
                    use_pages_file=args.use_pages_file,
                    use_gitignore=args.use_gitignore,
                    enable_relative_links=args.enable_relative_links,
                )
            else:
                try:
                    enable_relative_links = (
                        len(args.file_list) > 1 and args.enable_relative_links
                    )
                    pages_to_upload.append(
                        md2cf.document.get_page_data_from_file_path(
                            file_name,
                            strip_header=args.strip_top_header,
                            remove_text_newlines=args.remove_text_newlines,
                            enable_relative_links=enable_relative_links,
                        )
                    )
                except FileNotFoundError:
                    error_console.log(f"File {file_name} does not exist\n")

        if len(pages_to_upload) == 1:
            only_page = pages_to_upload[0]

            if args.title:
                only_page.title = args.title

            # This is implicitly only truthy if relative link processing is active
            if only_page.relative_links:
                # This covers the last edge case where directory processing leaves us
                # with only one page, which we can't anticipate at startup time.
                # In this case, we have to restore all the links to their original
                # values.
                error_console.log(
                    "Relative links are ignored when there's a single page\n"
                )
                for link_data in only_page.relative_links:
                    only_page.body.replace(
                        link_data.replacement, link_data.escaped_original
                    )
                only_page.relative_links = []

    return pages_to_upload


if __name__ == "__main__":
    main()
