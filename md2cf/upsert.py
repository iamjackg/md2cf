import hashlib
import re
from enum import Enum
from pathlib import Path
from typing import NamedTuple

import md2cf.document
from md2cf import api

CONTENT_HASH_REGEX = re.compile(r"\[v([a-f0-9]{40})]$")


class UpsertAction(Enum):
    CREATED = 1
    UPDATED = 2
    SKIPPED = 3


class UpsertResult(NamedTuple):
    action: UpsertAction
    response: api.Bunch


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
        content_type=page.content_type,
        additional_expansions=[
            "space",
            "ancestors",
            "history",
            "version",
            "metadata.labels",
        ],
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

    action = None
    if existing_page is None:
        existing_page = confluence.create_page(
            space=page.space,
            title=page.title,
            body=page.body,
            content_type=page.content_type,
            parent_id=page.parent_id,
            update_message=page_message,
            labels=page.labels,
        )
        action = UpsertAction.CREATED
    else:
        if not only_changed or page_needs_updating(
            page, existing_page, replace_all_labels
        ):
            existing_page = confluence.update_page(
                page=existing_page,
                body=page.body,
                parent_id=page.parent_id,
                update_message=page_message,
                labels=page.labels if replace_all_labels else None,
                minor_edit=minor_edit,
            )
            action = UpsertAction.UPDATED
        else:
            action = UpsertAction.SKIPPED

        if (
            not replace_all_labels
            and page.labels
            and labels_need_updating(page, existing_page)
        ):
            # print(f"Adding labels to page: {page.title} {page.labels}")
            confluence.add_labels(page=existing_page, labels=page.labels)

    return UpsertResult(action=action, response=existing_page)


def labels_need_updating(page, existing_page):
    if page.labels is None:
        return False

    if sorted(
        [label.name for label in existing_page.metadata.labels.results]
    ) != sorted(page.labels):
        return True


def page_needs_updating(page, existing_page, replace_all_labels):
    if page.parent_id is None and len(existing_page.ancestors) > 1:
        # page wants to become a top level page and was not one before
        # (top level pages only have one ancestor: the space's home page)
        return True

    if page.parent_id is not None and page.parent_id != existing_page.ancestors[-1].id:
        # page wants to change parent
        return True

    if replace_all_labels and labels_need_updating(page, existing_page):
        # print(f"Page labels have changed: {page.title} {page.labels}")
        return True
    else:
        existing_page_hash_match = CONTENT_HASH_REGEX.search(
            existing_page.version.message
        )
        if existing_page_hash_match is not None:
            original_page_hash = existing_page_hash_match.group(1)
            if original_page_hash == page.get_content_hash():
                return False

    return True


def upsert_attachment(
    confluence, attachment, existing_page, message, only_changed, page
):
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

    existing_attachment = confluence.get_attachment(existing_page, attachment_path.name)

    action = None
    if existing_attachment is None:
        # print(f"Uploading file: {attachment_path}")
        action = UpsertAction.CREATED
        with attachment_path.open("rb") as fp:
            existing_attachment = confluence.create_attachment(
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
                    action = UpsertAction.SKIPPED

        if should_update:
            # print(f"Updating file: {attachment_path}")
            with attachment_path.open("rb") as fp:
                existing_attachment = confluence.update_attachment(
                    page=existing_page,
                    fp=fp,
                    existing_attachment=existing_attachment,
                    message=attachment_message,
                )
            action = UpsertAction.UPDATED

    return UpsertResult(action=action, response=existing_attachment)
