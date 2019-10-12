import md2cf.__main__ as main
from md2cf.api import MinimalConfluence as Confluence


def test_upsert_page(mocker):
    """Base case: page doesn't already exist"""

    confluence = mocker.Mock(spec=Confluence)
    parent_page_mock = mocker.Mock()
    parent_page_mock.id = mocker.sentinel.parent_page_id
    confluence.get_page.side_effect = [None, parent_page_mock]

    space = mocker.sentinel.space
    title = mocker.sentinel.title
    body = mocker.sentinel.body
    parent = mocker.sentinel.parent
    message = mocker.sentinel.message

    main.upsert_page(
        confluence=confluence,
        space=space,
        title=title,
        body=body,
        parent=parent,
        message=message
    )

    confluence.get_page.assert_has_calls([
        mocker.call(title=title, space_key=space, page_id=None),
        mocker.call(title=parent, space_key=space)
    ], any_order=False)

    confluence.create_page.assert_called_once_with(
        space=space,
        title=title,
        body=body,
        parent_id=mocker.sentinel.parent_page_id,
        update_message=message
    )
