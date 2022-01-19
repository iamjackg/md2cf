import argparse
import getpass
import hashlib
import os
import pprint
import re
import sys
from collections import Counter
from pathlib import Path
from typing import List

from requests import HTTPError

from md2cf import api
import md2cf.document
from md2cf.document import Page


CONTENT_HASH_REGEX = re.compile(r"\[v([a-f0-9]{40})]$")


def get_parser():
    parser = argparse.ArgumentParser()
    login_group = parser.add_argument_group("login arguments")
    login_group.add_argument(
        "-o",
        "--host",
        help="full URL of the Confluence instance. "
        "Can also be specified as CONFLUENCE_HOST environment variable",
        default=os.getenv("CONFLUENCE_HOST"),
    )
    login_group.add_argument(
        "-u",
        "--username",
        help="username for logging into Confluence. "
        "Can also be specified as CONFLUENCE_USERNAME environment variable",
        default=os.getenv("CONFLUENCE_USERNAME"),
    )
    login_group.add_argument(
        "-p",
        "--password",
        help="password for logging into Confluence. "
        "Can also be specified as CONFLUENCE_PASSWORD environment variable. "
        "If not specified, it will be asked for interactively",
        default=os.getenv("CONFLUENCE_PASSWORD"),
    )

    required_group = parser.add_argument_group("required arguments")
    parser.add_argument(
        "-s",
        "--space",
        required=True,
        help="key for the Confluence space the page will be published to",
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
    page_group.add_argument("-m", "--message", help="update message for the change")
    page_group.add_argument("-i", "--page-id", help="ID of the page to be updated")
    page_group.add_argument(
        "--prefix",
        help="a string to prefix to every page title to ensure uniqueness",
        type=str,
    )
    preface_group = page_group.add_mutually_exclusive_group()
    preface_group.add_argument(
        "--preface-markdown",
        nargs="?",
        type=str,
        default=None,
        const="**Contents are auto-generated, do not edit.**",
        help="markdown content to prepend to each page. "
        'Defaults to "**Contents are auto-generated, do not edit.**" if no markdown is specified',
    )
    preface_group.add_argument(
        "--preface-file",
        type=Path,
        help="path to a markdown file to be prepended to every page",
    )

    dir_group = parser.add_argument_group("directory arguments")
    dir_group.add_argument(
        "--collapse-single-pages",
        action="store_true",
        help="if a folder contains a single document, collapse it so the folder doesn't appear",
    )
    dir_title_group = dir_group.add_mutually_exclusive_group()
    dir_title_group.add_argument(
        "--beautify-folders",
        action="store_true",
        help="replace hyphens and underscore in folder names with spaces, and capitalize the first letter",
    )
    dir_title_group.add_argument(
        "--use-pages-file",
        action="store_true",
        help='use the "title" entry in YAML files called .pages in each directory to change the folder name',
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
        "Use {} --help to get help.".format(parameter_name, sys.argv[0])
    )


def print_page_details(page: Page):
    page.body = page.body[:40] + ("..." if page.body else "")
    pprint.pprint(page.__dict__)


# Adapted from https://stackoverflow.com/a/3431838
def get_file_sha1(file_path: Path):
    hash_sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha1.update(chunk)
    return hash_sha1.hexdigest()


def upsert_page(
    confluence: api.MinimalConfluence,
    message: str,
    page: md2cf.document.Page,
    only_changed: bool = False,
):
    existing_page = confluence.get_page(
        title=page.title, space_key=page.space, page_id=page.page_id
    )

    if page.parent_id is None:
        if page.parent_title is not None:
            parent_page = confluence.get_page(
                title=page.parent_title, space_key=page.space
            )
            if parent_page is None:
                raise KeyError("The parent page could not be found")
            page.parent_id = parent_page.id

    page_message = message
    if only_changed:
        # If the functionality was just enabled, the previous version might not have the version hash in the message
        new_page_hash = page.get_content_hash()
        page_message = (
            f"{page_message} [v{new_page_hash}]"
            if page_message
            else f"[v{new_page_hash}]"
        )

    if existing_page is None:
        print(f"Creating new page: {page.title}")
        existing_page = confluence.create_page(
            space=page.space,
            title=page.title,
            body=page.body,
            parent_id=page.parent_id,
            update_message=page_message,
        )
    else:
        should_update = True
        if only_changed:
            original_page_hash_match = CONTENT_HASH_REGEX.match(
                existing_page.version.message
            )
            if original_page_hash_match is not None:
                original_page_hash = original_page_hash_match.group(1)
                if original_page_hash == page.get_content_hash():
                    should_update = False
                    print(f"Skipping page that didn't change: {page.title}")

        if should_update:
            print(f"Updating page: {page.title}")
            confluence.update_page(
                page=existing_page,
                body=page.body,
                parent_id=page.parent_id,
                update_message=page_message,
            )

    if page.attachments:
        print(f"Uploading attachments for page: {page.title}")
        for attachment in page.attachments:
            if page.file_path is not None:
                attachment_path = page.file_path.parent.joinpath(attachment)
            else:
                attachment_path = attachment

            attachment_message = message
            if only_changed:
                new_attachment_hash = get_file_sha1(attachment_path)
                attachment_message = (
                    f"{attachment_message} [v{new_attachment_hash}]"
                    if attachment_message
                    else f"[v{new_attachment_hash}]"
                )

            existing_attachment = confluence.get_attachment(
                existing_page, attachment_path.name
            )

            if existing_attachment is None:
                print(f"Uploading file: {attachment_path}")
                with attachment_path.open("rb") as fp:
                    confluence.create_attachment(
                        page=existing_page, fp=fp, message=attachment_message
                    )
            else:
                should_update = True
                if only_changed:
                    original_attachment_hash_match = CONTENT_HASH_REGEX.match(
                        existing_attachment.version.message
                    )
                    if original_attachment_hash_match is not None:
                        original_attachment_hash = original_attachment_hash_match.group(
                            1
                        )
                        if original_attachment_hash == new_attachment_hash:
                            should_update = False
                            print(
                                f"Skipping attachment that didn't change: {attachment_path}"
                            )

                if should_update:
                    print(f"Updating file: {attachment_path}")
                    with attachment_path.open("rb") as fp:
                        confluence.update_attachment(
                            page=existing_page,
                            fp=fp,
                            existing_attachment=existing_attachment,
                            message=attachment_message,
                        )


def main():
    args = get_parser().parse_args()

    for required_parameter in ["host", "username"]:
        if getattr(args, required_parameter) is None:
            print_missing_parameter(required_parameter)
            exit(1)

    if args.password is None:
        print("Password:")
        args.password = getpass.getpass()

    confluence = api.MinimalConfluence(
        host=args.host, username=args.username, password=args.password
    )

    if (args.title or args.page_id) and (
        len(args.file_list) > 1 or any(map(os.path.isdir, args.file_list))
    ):
        sys.stderr.write(
            "Title and page ID cannot be specified on the command line if uploading more than one file or whole directories\n"
        )
        exit(1)

    pages_to_upload: List[Page] = list()
    if not args.file_list:  # Uploading from standard input
        pages_to_upload.append(
            md2cf.document.get_page_data_from_lines(sys.stdin.readlines())
        )

        if not (pages_to_upload[0].title or args.title):
            sys.stderr.write(
                "You must specify a title or have a title in the document if uploading from standard input\n"
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
                    use_pages_file=args.use_pages_file,
                )
            else:
                try:
                    pages_to_upload.append(
                        md2cf.document.get_page_data_from_file_path(file_name)
                    )
                except FileNotFoundError:
                    sys.stderr.write(f"File {file_name} does not exist\n")

        if len(pages_to_upload) == 1:
            if args.title:
                pages_to_upload[0].title = args.title

    something_went_wrong = False

    page_title_counts = Counter([page.title for page in pages_to_upload])
    colliding_titles = [
        title for title, count in page_title_counts.most_common() if count > 1
    ]
    if colliding_titles:
        sys.stderr.write(
            "Some documents have the same title, but all Confluence pages in the same space must have different titles.\n"
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
        preface_markup = md2cf.document.get_page_data_from_file_path(
            args.preface_file
        ).body

    for page in pages_to_upload:
        page.space = args.space
        page.page_id = args.page_id

        if page.parent_title is None:  # This only happens for top level pages
            # If the argument is not supplied this leaves the parent_title as None, which is fine
            page.parent_title = args.parent_title
        else:
            if args.prefix:
                page.parent_title = f"{args.prefix} - {page.parent_title}"

        if page.parent_title is None:
            page.parent_id = (
                page.parent_id or args.parent_id
            )  # This can still end up being None. It's fine.

        if args.prefix:
            page.title = f"{args.prefix} - {page.title}"

        if preface_markup:
            page.body = preface_markup + page.body

        try:
            if args.dry_run:
                print_page_details(page)
            else:
                upsert_page(
                    confluence=confluence,
                    message=args.message,
                    page=page,
                    only_changed=args.only_changed,
                )
        except HTTPError as e:
            sys.stderr.write("{} - {}\n".format(str(e), e.response.content))
            something_went_wrong = True
        except Exception as e:
            sys.stderr.write("ERROR: {}\n".format(str(e)))
            something_went_wrong = True

    if something_went_wrong:
        exit(1)


if __name__ == "__main__":
    main()
