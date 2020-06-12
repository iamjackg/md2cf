import argparse
import getpass
import os
import sys

import mistune
from requests import HTTPError

from md2cf import api
from md2cf.confluence_renderer import ConfluenceRenderer


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
    parser.add_argument(
        "-a",
        "--parent",
        help="the parent page under which the new page will be uploaded",
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
        help="the markdown file(s) to upload to Confluence",
        nargs="*",
        default=[sys.stdin],
    )
    return parser


def print_missing_parameter(parameter_name):
    sys.stderr.write(
        "Missing required parameter: {}\n"
        "Use {} --help to get help.".format(parameter_name, sys.argv[0])
    )


def page_data_from_file_name(file_name):
    with open(file_name) as file_handle:
        markdown_data = file_handle.read()

    renderer = ConfluenceRenderer(use_xhtml=True)

    confluence_mistune = mistune.Markdown(renderer=renderer)
    confluence_content = confluence_mistune(markdown_data)

    if renderer.title is not None:
        page_title = renderer.title
    else:
        page_title = os.path.splitext(os.path.basename(file_name))[0]

    page_data = {
        "title": page_title,
        "body": confluence_content,
        "attachments": renderer.attachments,
    }

    return page_data


def upsert_page(
    confluence, space, title, body, parent, message, page_id=None, attachments=None
):
    if attachments is None:
        attachments = list()

    existing_page = confluence.get_page(title=title, space_key=space, page_id=page_id)

    if existing_page is None:
        parent_id = None
        if parent is not None:
            parent_page = confluence.get_page(title=parent, space_key=space)
            if parent_page is None:
                raise KeyError("The parent page could not be found")
            parent_id = parent_page.id

        existing_page = confluence.create_page(
            space=space,
            title=title,
            body=body,
            parent_id=parent_id,
            update_message=message,
        )
    else:
        confluence.update_page(page=existing_page, body=body, update_message=message)

    if attachments:
        for attachment in attachments:
            with open(attachment, "rb") as fp:
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

    if args.title and len(args.file_list) > 1:
        sys.stderr.write('The title cannot be specified on the command line if uploading more than one file')
        exit(1)

    something_went_wrong = False
    for file_name in args.file_list:
        page_data = page_data_from_file_name(file_name)
        print(page_data)
        try:
            upsert_page(
                confluence=confluence,
                space=args.space,
                title=args.title or page_data["title"],
                body=page_data["body"],
                parent=args.parent,
                message=args.message,
                page_id=args.page_id,
                attachments=page_data["attachments"],
            )
        except HTTPError as e:
            sys.stderr.write('{} - {}\n'.format(str(e), e.response.content))
            something_went_wrong = True

    if something_went_wrong:
        exit(1)


if __name__ == "__main__":
    main()
