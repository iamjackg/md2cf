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

    upserted_page = md2cf.upsert.upsert_page(
        confluence=confluence,
        page=page,
        message=message,
    )

    assert upserted_page == mocker.sentinel.upserted_page

    confluence.get_page.assert_any_call(
        title=page.title,
        space_key=page.space,
        page_id=None,
        additional_expansions=[
            "space",
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

    md2cf.upsert.upsert_page(
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
