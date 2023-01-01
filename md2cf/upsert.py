import hashlib
import re
from pathlib import Path

import md2cf.document
from md2cf import api

CONTENT_HASH_REGEX = re.compile(r"\[v([a-f0-9]{40})]$")


# Adapted from https://stackoverflow.com/a/3431838
def get_file_sha1(file_path: Path):
    hash_sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha1.update(chunk)
    return hash_sha1.hexdigest()


def get_parent_id_from_title(confluence, page):
    parent_page = confluence.get_page(
        title=page.parent_title,
        space_key=page.space,
        additional_expansions=[
            "space",
            "history",
            "version",
            "metadata.labels",
        ],
    )
    if parent_page is None:
        raise KeyError("The parent page could not be found")
    return parent_page.id


def upsert_page(
    confluence: api.MinimalConfluence,
    message: str,
    page: md2cf.document.Page,
    only_changed: bool = False,
    replace_all_labels: bool = False,
    minor_edit: bool = False,
):
    existing_page = confluence.get_page(
        title=page.title,
        space_key=page.space,
        page_id=page.page_id,
        additional_expansions=["space", "history", "version", "metadata.labels"],
    )

    # It's not mandatory to have a parent ID -- if there isn't one, the page will be a
    # top-level page in the Confluence space
    if page.parent_id is None:
        if page.parent_title is not None:
            page.parent_id = get_parent_id_from_title(confluence, page)

    page_message = message
    if only_changed:
        page_hash = page.get_content_hash()
        page_message = (
            f"{page_message} [v{page_hash}]" if page_message else f"[v{page_hash}]"
        )

    if existing_page is None:
        print(f"Creating new page: {page.title}")
        existing_page = confluence.create_page(
            space=page.space,
            title=page.title,
            body=page.body,
            content_type=page.content_type,
            parent_id=page.parent_id,
            update_message=page_message,
            labels=page.labels,
        )
    else:
        if not only_changed or page_needs_updating(
            page, existing_page, replace_all_labels
        ):
            print(f"Updating page: {page.title}")
            existing_page = confluence.update_page(  # TODO: test this
                page=existing_page,
                body=page.body,
                parent_id=page.parent_id,
                update_message=page_message,
                labels=page.labels if replace_all_labels else None,
                minor_edit=minor_edit,
            )

        if (
            not replace_all_labels
            and page.labels
            and labels_need_updating(page, existing_page)
        ):
            print(f"Adding labels to page: {page.title} {page.labels}")
            confluence.add_labels(page=existing_page, labels=page.labels)

    print(confluence.get_url(existing_page))

    if page.attachments:
        upsert_attachments(confluence, existing_page, message, only_changed, page)

    return existing_page


def labels_need_updating(page, existing_page):
    if page.labels is None:
        return False

    if sorted(
        [label.name for label in existing_page.metadata.labels.results]
    ) != sorted(page.labels):
        return True


def page_needs_updating(page, existing_page, replace_all_labels):
    should_update = True
    if replace_all_labels and labels_need_updating(page, existing_page):
        print(f"Page labels have changed: {page.title} {page.labels}")
        should_update = True
    else:
        existing_page_hash_match = CONTENT_HASH_REGEX.search(
            existing_page.version.message
        )
        if existing_page_hash_match is not None:
            original_page_hash = existing_page_hash_match.group(1)
            if original_page_hash == page.get_content_hash():
                should_update = False
                print(f"Skipping page that didn't change: {page.title}")

    return should_update


def upsert_attachments(confluence, existing_page, message, only_changed, page):
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
                existing_attachment_hash_match = CONTENT_HASH_REGEX.search(
                    existing_attachment.version.message
                )
                if existing_attachment_hash_match is not None:
                    original_attachment_hash = existing_attachment_hash_match.group(1)
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
