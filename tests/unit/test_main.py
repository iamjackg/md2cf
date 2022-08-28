import md2cf.__main__ as main
from md2cf.api import MinimalConfluence as Confluence
from md2cf.document import Page


def test_upsert_page(mocker):
    """Base case: page doesn't already exist"""

    confluence = mocker.Mock(spec=Confluence)
    parent_page_mock = mocker.Mock()
    parent_page_mock.id = mocker.sentinel.parent_page_id
    confluence.get_page.side_effect = [None, parent_page_mock]

    page = Page(
        space=mocker.sentinel.space,
        title=mocker.sentinel.title,
        body=mocker.sentinel.body,
        parent_title=mocker.sentinel.parent,
    )

    message = mocker.sentinel.message

    main.upsert_page(
        confluence=confluence,
        page=page,
        message=message,
    )

    confluence.get_page.assert_has_calls(
        [
            mocker.call(
                title=page.title,
                space_key=page.space,
                page_id=None,
                additional_expansions=[
                    "space",
                    "history",
                    "version",
                    "metadata.labels",
                ],
            ),
            mocker.call(
                title=page.parent_title,
                space_key=page.space,
                additional_expansions=[
                    "space",
                    "history",
                    "version",
                    "metadata.labels",
                ],
            ),
        ],
        any_order=False,
    )

    confluence.create_page.assert_called_once_with(
        space=page.space,
        title=page.title,
        body=page.body,
        parent_id=mocker.sentinel.parent_page_id,
        update_message=message,
        labels=None,
    )
