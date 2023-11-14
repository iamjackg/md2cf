import pytest

import md2cf.upsert
from md2cf.api import MinimalConfluence as Confluence
from md2cf.document import Page


def test_upsert_page(mocker):
    """Base case: page doesn't already exist"""

    confluence = mocker.Mock(spec=Confluence)
    confluence.get_page.return_value = None
    confluence.create_page.return_value = mocker.sentinel.upserted_page

    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body=mocker.sentinel.body,
        parent_id=mocker.sentinel.parent_id,
    )

    message = mocker.sentinel.message

    upsert_result = md2cf.upsert.upsert_page(
        confluence=confluence,
        page=page,
        message=message,
    )

    assert upsert_result.response == mocker.sentinel.upserted_page
    assert upsert_result.action == upsert_result.action.CREATED

    confluence.get_page.assert_any_call(
        title=page.title,
        space_key=page.space,
        content_type=page.content_type,
        page_id=None,
        additional_expansions=[
            "space",
            "ancestors",
            "history",
            "version",
            "metadata.labels",
        ],
    )

    confluence.create_page.assert_called_once_with(
        space=page.space,
        title=page.title,
        body=page.body,
        content_type=page.content_type,
        parent_id=mocker.sentinel.parent_id,
        update_message=message,
        labels=None,
    )

    confluence.update_page.assert_not_called()


def test_upsert_page_get_parent_by_title(mocker):
    """Base case: page doesn't already exist"""

    confluence = mocker.Mock(spec=Confluence)
    parent_page_mock = mocker.Mock()
    parent_page_mock.id = mocker.sentinel.parent_page_id
    confluence.get_page.side_effect = [None, parent_page_mock]
    confluence.create_page.return_value = mocker.sentinel.upserted_page

    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body=mocker.sentinel.body,
        parent_title=mocker.sentinel.parent_title,
    )

    message = mocker.sentinel.message

    upsert_result = md2cf.upsert.upsert_page(
        confluence=confluence,
        page=page,
        message=message,
    )

    confluence.create_page.assert_called_once_with(
        space=page.space,
        title=page.title,
        body=page.body,
        content_type=page.content_type,
        parent_id=mocker.sentinel.parent_page_id,
        update_message=message,
        labels=None,
    )

    assert upsert_result.response == mocker.sentinel.upserted_page
    assert upsert_result.action == upsert_result.action.CREATED


def test_upsert_page_parent_not_found(mocker):
    """Base case: page parent doesn't exist"""

    confluence = mocker.Mock(spec=Confluence)
    confluence.get_page.side_effect = [None, None]

    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body=mocker.sentinel.body,
        parent_title=mocker.sentinel.parent,
    )

    message = mocker.sentinel.message

    with pytest.raises(KeyError) as parent_exception:
        md2cf.upsert.upsert_page(
            confluence=confluence,
            page=page,
            message=message,
        )

    assert "The parent page could not be found" in str(parent_exception)

    confluence.create_page.assert_not_called()


def test_upsert_page_only_changed_new_page(mocker):
    """We only want to upload pages that have changed, but this is the first
    version of the page"""

    confluence = mocker.Mock(spec=Confluence)
    confluence.get_page.return_value = None
    confluence.create_page.return_value = mocker.sentinel.created_page

    message_hash = "[v6e71b3cac15d32fe2d36c270887df9479c25c640]"

    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body="hello there",
    )

    upsert_result = md2cf.upsert.upsert_page(
        confluence=confluence, page=page, message="", only_changed=True
    )

    confluence.create_page.assert_called_once_with(
        space=page.space,
        title=page.title,
        body=page.body,
        content_type=page.content_type,
        parent_id=None,
        update_message=message_hash,
        labels=None,
    )

    assert upsert_result.response == mocker.sentinel.created_page
    assert upsert_result.action == upsert_result.action.CREATED


def test_upsert_page_only_changed_modified_page(mocker):
    """We only want to upload pages that have changed, and the existing page
    has been changed"""

    confluence = mocker.Mock(spec=Confluence)
    original_message_hash = "[vdeadbeefc15d32fe2d36c270887df9479c25c640]"
    existing_page_mock = mocker.Mock()
    existing_page_mock.version.message = original_message_hash
    existing_page_mock.ancestors = [mocker.Mock()]
    confluence.get_page.side_effect = [existing_page_mock, None]
    confluence.update_page.return_value = mocker.sentinel.updated_page

    message_hash = "[v6e71b3cac15d32fe2d36c270887df9479c25c640]"

    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body="hello there",
    )

    upsert_result = md2cf.upsert.upsert_page(
        confluence=confluence, page=page, message="", only_changed=True
    )

    confluence.update_page.assert_called_once_with(
        page=existing_page_mock,
        body=page.body,
        minor_edit=False,
        parent_id=None,
        update_message=message_hash,
        labels=None,
    )

    assert upsert_result.response == mocker.sentinel.updated_page
    assert upsert_result.action == upsert_result.action.UPDATED


def test_upsert_page_only_changed_no_changes(mocker):
    """We only want to upload pages that have changed, but the existing page
    has NOT been changed"""

    confluence = mocker.Mock(spec=Confluence)
    message_hash = "[v6e71b3cac15d32fe2d36c270887df9479c25c640]"
    existing_page_mock = mocker.Mock()
    existing_page_mock.version.message = message_hash
    ancestor_mock = mocker.Mock()
    ancestor_mock.id = mocker.sentinel.parent_id
    existing_page_mock.ancestors = [ancestor_mock]
    confluence.get_page.side_effect = [existing_page_mock, None]
    confluence.update_page.return_value = mocker.sentinel.updated_page

    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body="hello there",
        parent_id=mocker.sentinel.parent_id,
    )

    upsert_result = md2cf.upsert.upsert_page(
        confluence=confluence, page=page, message="", only_changed=True
    )

    confluence.update_page.assert_not_called()

    assert upsert_result.response == existing_page_mock
    assert upsert_result.action == upsert_result.action.SKIPPED


def test_page_needs_updating_page_not_changed(mocker):
    message_hash = "[v6e71b3cac15d32fe2d36c270887df9479c25c640]"
    existing_page_mock = mocker.Mock()
    ancestor_mock = mocker.Mock()
    ancestor_mock.id = mocker.sentinel.parent_id
    existing_page_mock.ancestors = [ancestor_mock]
    existing_page_mock.version.message = message_hash

    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body="hello there",
        parent_id=mocker.sentinel.parent_id,
    )

    assert not md2cf.upsert.page_needs_updating(
        page, existing_page_mock, replace_all_labels=False
    )


def test_page_needs_updating_page_changed(mocker):
    message_hash = "[vdeadbeefc15d32fe2d36c270887df9479c25c640]"
    existing_page_mock = mocker.Mock()
    ancestor_mock = mocker.Mock()
    ancestor_mock.id = mocker.sentinel.parent_id
    existing_page_mock.ancestors = [ancestor_mock]
    existing_page_mock.version.message = message_hash

    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body="hello there",
        parent_id=mocker.sentinel.parent_id,
    )

    assert md2cf.upsert.page_needs_updating(
        page, existing_page_mock, replace_all_labels=False
    )


def test_page_needs_updating_content_replace_all_labels_and_labels_not_changed(mocker):
    """We want to replace all the labels, but they have not changed"""
    labels = ["label1", "label2"]
    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body="hello there",
        labels=labels,
        parent_id=mocker.sentinel.parent_id,
    )

    message_hash = "[v6e71b3cac15d32fe2d36c270887df9479c25c640]"
    existing_page_mock = mocker.Mock(
        get=mocker.Mock(return_value=[{"name": label} for label in labels])
    )
    ancestor_mock = mocker.Mock()
    ancestor_mock.id = mocker.sentinel.parent_id
    existing_page_mock.ancestors = [ancestor_mock]
    existing_page_mock.version.message = message_hash
    existing_page_mock.metadata.labels.results = []

    assert not md2cf.upsert.page_needs_updating(
        page, existing_page_mock, replace_all_labels=True
    )


def test_page_needs_updating_from_top_page_to_another_parent(mocker):
    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body="hello there",
        parent_id="123",
    )

    message_hash = "[v6e71b3cac15d32fe2d36c270887df9479c25c640]"
    existing_page_mock = mocker.Mock()
    existing_page_mock.ancestors = []
    existing_page_mock.version.message = message_hash
    existing_page_mock.metadata.labels.results = []

    assert md2cf.upsert.page_needs_updating(
        page, existing_page_mock, replace_all_labels=True
    )


def test_page_needs_updating_from_child_page_to_top_page(mocker):
    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body="hello there",
        parent_id=None,
    )

    message_hash = "[v6e71b3cac15d32fe2d36c270887df9479c25c640]"
    existing_page_mock = mocker.Mock()
    ancestor_mock = mocker.Mock()
    ancestor_mock.id = "123"
    existing_page_mock.ancestors = [ancestor_mock]
    existing_page_mock.version.message = message_hash
    existing_page_mock.metadata.labels.results = []

    assert md2cf.upsert.page_needs_updating(
        page, existing_page_mock, replace_all_labels=True
    )


def test_page_needs_updating_from_grandchild_page_to_top_page(mocker):
    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body="hello there",
        parent_id=None,
    )

    message_hash = "[v6e71b3cac15d32fe2d36c270887df9479c25c640]"
    existing_page_mock = mocker.Mock()
    ancestor_mock = mocker.Mock()
    ancestor_mock.id = "123"
    other_ancestor_mock = mocker.Mock()
    other_ancestor_mock.id = "567"
    existing_page_mock.ancestors = [ancestor_mock, other_ancestor_mock]
    existing_page_mock.version.message = message_hash
    existing_page_mock.metadata.labels.results = []

    assert md2cf.upsert.page_needs_updating(
        page, existing_page_mock, replace_all_labels=True
    )


def test_page_needs_updating_content_replace_all_labels_and_labels_changed(mocker):
    """We want to replace all the labels, and they have changed"""
    page_labels = ["label1", "label2"]
    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body="hello there",
        labels=page_labels,
    )

    message_hash = "[v6e71b3cac15d32fe2d36c270887df9479c25c640]"
    existing_page_mock = mocker.Mock()
    existing_page_mock.ancestors = [mocker.Mock()]
    existing_page_mock.version.message = message_hash
    existing_page_mock.metadata.labels.results = []
    existing_page_labels = ["label2", "label3"]
    for label in existing_page_labels:
        label_mock = mocker.Mock()
        label_mock.name = label
        existing_page_mock.metadata.labels.results.append(label_mock)

    assert md2cf.upsert.page_needs_updating(
        page, existing_page_mock, replace_all_labels=True
    )


def test_page_needs_updating_content_replace_all_labels_but_no_labels_supplied(mocker):
    """We want to replace all the labels, but none were supplied"""
    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body="hello there",
        labels=None,
        parent_id=mocker.sentinel.parent_id,
    )

    message_hash = "[v6e71b3cac15d32fe2d36c270887df9479c25c640]"
    existing_page_mock = mocker.Mock()
    ancestor_mock = mocker.Mock()
    ancestor_mock.id = mocker.sentinel.parent_id
    existing_page_mock.ancestors = [ancestor_mock]
    existing_page_mock.version.message = message_hash

    labels = ["label1", "label2"]
    existing_page_mock.metadata.labels.results = []
    for label in labels:
        label_mock = mocker.Mock()
        label_mock.name = label
        existing_page_mock.metadata.labels.results.append(label_mock)

    assert not md2cf.upsert.page_needs_updating(
        page, existing_page_mock, replace_all_labels=True
    )


def test_page_needs_updating_content_replace_all_labels_and_empty_labels_supplied(
    mocker,
):
    """We want to replace all the labels, and an empty list was supplied:
    should update to remove all labels if the list is different"""
    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body="hello there",
        labels=[],
        parent_id=mocker.sentinel.parent_id,
    )

    message_hash = "[v6e71b3cac15d32fe2d36c270887df9479c25c640]"
    labels = ["label1", "label2"]
    existing_page_mock = mocker.Mock(
        get=mocker.Mock(return_value=[{"name": label} for label in labels])
    )
    ancestor_mock = mocker.Mock()
    ancestor_mock.id = mocker.sentinel.parent_id
    existing_page_mock.ancestors = [ancestor_mock]
    existing_page_mock.version.message = message_hash

    assert md2cf.upsert.page_needs_updating(
        page, existing_page_mock, replace_all_labels=True
    )


def test_page_needs_updating_content_replace_all_labels_and_empty_labels_supplied_not_changed(  # noqa: E501
    mocker,
):
    """We want to replace all the labels, and an empty list was supplied:
    should not update because the page already has no labels"""
    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body="hello there",
        labels=[],
        parent_id=mocker.sentinel.parent_id,
    )

    message_hash = "[v6e71b3cac15d32fe2d36c270887df9479c25c640]"
    existing_page_mock = mocker.Mock(get=mocker.Mock(return_value=[]))
    ancestor_mock = mocker.Mock()
    ancestor_mock.id = mocker.sentinel.parent_id
    existing_page_mock.ancestors = [ancestor_mock]
    existing_page_mock.version.message = message_hash

    assert not md2cf.upsert.page_needs_updating(
        page, existing_page_mock, replace_all_labels=True
    )


def test_page_needs_updated_created_with_no_labels_and_new_ones_were_added(mocker):
    """An existing page with no labels was created, and new labels were added
    after the fact. We should update the page with these new labels"""
    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body="hello there",
        labels=["foo"],
        parent_id=mocker.sentinel.parent_id,
    )

    message_hash = "[v6e71b3cac15d32fe2d36c270887df9479c25c640]"
    existing_page_mock = mocker.Mock(get=mocker.Mock(return_value=[]))
    ancestor_mock = mocker.Mock()
    ancestor_mock.id = mocker.sentinel.parent_id
    existing_page_mock.ancestors = [ancestor_mock]
    existing_page_mock.version.message = message_hash

    assert md2cf.upsert.page_needs_updating(
        page, existing_page_mock, replace_all_labels=True
    )
