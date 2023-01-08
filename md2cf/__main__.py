import argparse
import copy
import getpass
import hashlib
import os
import pprint
import sys
from collections import Counter
from pathlib import Path
from typing import List

from requests import HTTPError

from md2cf import api
import md2cf.document
from md2cf.document import Page
from md2cf.upsert import upsert_page


def get_parser():
    parser = argparse.ArgumentParser()
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
    sys.stderr.write(
        "Missing required parameter: {}\n"
        "Use {} --help to get help.\n".format(parameter_name, sys.argv[0])
    )


def print_page_details(page: Page):
    page_copy = copy.copy(page)
    page_copy.body = page_copy.body[:40] + ("..." if page_copy.body else "")
    pprint.pprint(page_copy.__dict__)


def main():
    args = get_parser().parse_args()

    if args.host is None:
        print_missing_parameter("host")
        exit(1)

    if args.username is None and args.token is None:
        print_missing_parameter("username or bearer token")
        exit(1)

    if args.space is None:
        print_missing_parameter("space")
        exit(1)

    if args.password is None and args.token is None:
        args.password = getpass.getpass()

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
        sys.stderr.write(
            "Title and page ID cannot be specified on the command line "
            "if uploading more than one file or whole directories\n"
        )
        exit(1)

    pages_to_upload = collect_pages_to_upload(args)

    something_went_wrong = False

    page_title_counts = Counter([page.title for page in pages_to_upload])
    colliding_titles = [
        title for title, count in page_title_counts.most_common() if count > 1
    ]
    if colliding_titles:
        sys.stderr.write(
            "Some documents have the same title, but all Confluence pages "
            "in the same space must have different titles.\n"
            "These are the documents (and path, if available) with identical titles:\n"
        )
        for title in colliding_titles:
            for filename in [
                page.file_path for page in pages_to_upload if page.title == title
            ]:
                sys.stderr.write(f"{title}\t{filename}\n")
        exit(1)

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

    map_document_path_to_page = dict()
    if args.enable_relative_links:
        map_document_path_to_page = build_document_path_to_page_map(pages_to_upload)
        if not args.ignore_relative_link_errors:
            validate_relative_links(pages_to_upload, map_document_path_to_page)

    for page in pages_to_upload:
        pre_process_page(page, args, postface_markup, preface_markup)

        try:
            if args.dry_run:
                print_page_details(page)
            else:
                final_page = upsert_page(
                    confluence=confluence,
                    message=args.message,
                    page=page,
                    only_changed=args.only_changed,
                    replace_all_labels=args.replace_all_labels,
                    minor_edit=args.minor_edit,
                )
                if page.file_path is not None and args.enable_relative_links:
                    # Skip pages without a file_path
                    # (e.g. section pages representing directories)
                    map_document_path_to_page[page.file_path.resolve()] = final_page
        except HTTPError as e:
            sys.stderr.write("{} - {}\n".format(str(e), e.response.content))
            something_went_wrong = True
        except Exception as e:
            sys.stderr.write("ERROR: {}\n".format(str(e)))
            something_went_wrong = True

    if something_went_wrong:
        exit(1)

    print()

    if args.enable_relative_links:
        update_pages_with_relative_links(
            args, confluence, pages_to_upload, map_document_path_to_page
        )


def pre_process_page(page, args, postface_markup, preface_markup):
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
                sys.stderr.write(
                    f"Page {page.file_path} has a relative link to {link_data.path}"
                    ", which is not in the list of pages to be uploaded.\n"
                )
                invalid_links = True
    if invalid_links:
        sys.stderr.write(
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


def update_pages_with_relative_links(args, confluence, pages_to_upload, path_to_page):
    something_went_wrong = False
    for page in pages_to_upload:
        if page.file_path is None:
            # Skip pages without a file_path
            # (e.g. section pages representing directories)
            continue

        if args.dry_run and page.relative_links:
            sys.stderr.write(
                f"Dry run: skipping relative link replacement for {page.file_path}"
            )
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
                    sys.stderr.write(
                        f"Page {page.file_path} has a relative link to {link_data.path}"
                        ", which was not uploaded correctly.\n"
                    )
                    break

            page.body = page.body.replace(
                link_data.replacement, confluence.get_url(page_on_confluence)
            )
            page_modified = True

        if page_modified:
            try:
                print(
                    f"Page {page.file_path} has updated relative links. Re-uploading."
                )
                upsert_page(
                    confluence=confluence,
                    message=args.message,
                    page=page,
                    only_changed=args.only_changed,
                    replace_all_labels=args.replace_all_labels,
                    minor_edit=True,
                )
            except HTTPError as e:
                sys.stderr.write("{} - {}\n".format(str(e), e.response.content))
                something_went_wrong = True
            except Exception as e:
                sys.stderr.write("ERROR: {}\n".format(str(e)))
                something_went_wrong = True

        if something_went_wrong:
            exit(1)


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
            sys.stderr.write(
                "You must specify a title or have a title in the document "
                "if uploading from standard input\n"
            )
            exit(1)

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
                    sys.stderr.write(f"File {file_name} does not exist\n")

        if len(pages_to_upload) == 1:
            only_page = pages_to_upload[0]

            if args.title:
                only_page.title = args.title

            # This is implicitly only here if relative link processing is active
            if only_page.relative_links:
                # This covers the last edge case where directory processing leaves us
                # with only one page, which we can't anticipate.
                # In this case, we have to restore all the links to their original
                # values.
                sys.stderr.write(
                    "Relative links are ignored when there's a single page\n"
                )
                for link_data in only_page.relative_links:
                    only_page.body.replace(
                        link_data.replacement, link_data.escaped_original
                    )

    return pages_to_upload


if __name__ == "__main__":
    main()
