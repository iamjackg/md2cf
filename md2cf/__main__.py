import argparse
import getpass
import os
import sys
from pathlib import Path
from typing import List, Optional

from requests import HTTPError

from md2cf import api
import md2cf.document
from md2cf.document import Page


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o",
        "--host",
        help="full URL of the Confluence instance."
        "Can also be specified as CONFLUENCE_HOST environment variable",
        default=os.getenv("CONFLUENCE_HOST"),
    )
    parser.add_argument(
        "-u",
        "--username",
        help="the username for logging into Confluence. "
        "Can also be specified as CONFLUENCE_USERNAME environment variable",
        default=os.getenv("CONFLUENCE_USERNAME"),
    )
    parser.add_argument(
        "-p",
        "--password",
        help="the password for logging into Confluence. "
        "Can also be specified as CONFLUENCE_PASSWORD environment variable. "
        "If not specified, it will be asked for interactively",
        default=os.getenv("CONFLUENCE_PASSWORD"),
    )
    parser.add_argument(
        "-s",
        "--space",
        required=True,
        help="the key for the Confluence space the page will be published to",
    )

    parent_group = parser.add_mutually_exclusive_group()
    parent_group.add_argument(
        "-a",
        "--parent-title",
        help="the title of the parent page under which the new page will be uploaded",
    )
    parent_group.add_argument(
        "-A",
        "--parent-id",
        help="the ID of the parent page under which the new page will be uploaded",
    )

    parser.add_argument(
        "-t",
        "--title",
        help="a title for the page. Defaults to first top level header in document, or filename",
    )
    parser.add_argument("-m", "--message", help="the update message for the change")
    parser.add_argument("-i", "--page-id", help="the ID of the page to be updated")
    parser.add_argument(
        "file_list",
        type=Path,
        help="the markdown file(s) to upload to Confluence",
        nargs="*",
    )
    return parser


def print_missing_parameter(parameter_name: str):
    sys.stderr.write(
        "Missing required parameter: {}\n"
        "Use {} --help to get help.".format(parameter_name, sys.argv[0])
    )


def upsert_page(
    confluence: api.MinimalConfluence,
    message: str,
    page: md2cf.document.Page
):
    existing_page = confluence.get_page(title=page.title, space_key=page.space, page_id=page.page_id)

    if existing_page is None:
        if page.parent_id is None:
            if page.parent_title is not None:
                parent_page = confluence.get_page(title=page.parent_title, space_key=page.space)
                if parent_page is None:
                    raise KeyError("The parent page could not be found")
                page.parent_id = parent_page.id

        existing_page = confluence.create_page(
            space=page.space,
            title=page.title,
            body=page.body,
            parent_id=page.parent_id,
            update_message=message,
        )
    else:
        confluence.update_page(page=existing_page, body=page.body, update_message=message)

    if page.attachments:
        for attachment in page.attachments:
            if page.file_path is not None:
                attachment_path = page.file_path.joinpath(attachment)
            else:
                attachment_path = attachment

            with attachment_path.open("rb") as fp:
                confluence.upload_attachment(page=existing_page, fp=fp)


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

    if args.title and (len(args.file_list) > 1 or any(map(os.path.isdir, args.file_list))):
        sys.stderr.write(
            "The title cannot be specified on the command line if uploading more than one file or whole directories\n"
        )
        exit(1)

    pages_to_upload: List[Page] = list()
    if not args.file_list:
        pages_to_upload.append(
            md2cf.document.get_page_data_from_lines(sys.stdin.readlines())
        )

        if not pages_to_upload[0]["title"] and not args.title:
            sys.stderr.write(
                "You must specify a title or have a title in the document if uploading from standard input\n"
            )
            exit(1)

        if args.title:
            pages_to_upload[0]["title"] = args.title
    else:
        for file_name in args.file_list:
            pages_to_upload.append(
                md2cf.document.get_page_data_from_file_path(file_name)
            )

        if len(pages_to_upload) == 1:
            if args.title:
                pages_to_upload[0]["title"] = args.title

    something_went_wrong = False

    for page in pages_to_upload:
        page.space = args.space
        page.parent_title = args.parent_title
        page.parent_id = args.parent_id
        page.page_id = args.page_id
        try:
            upsert_page(
                confluence=confluence,
                message=args.message,
                page=page
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
