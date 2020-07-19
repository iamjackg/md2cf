import pytest


def bunchify(obj):
    if isinstance(obj, (list, tuple)):
        return [bunchify(item) for item in obj]
    if isinstance(obj, dict):
        return Bunch(obj)
    return obj


class Bunch(dict):
    def __init__(self, kwargs=None):
        if kwargs is None:
            kwargs = {}
        for key, value in kwargs.items():
            kwargs[key] = bunchify(value)
        super(Bunch, self).__init__(kwargs)
        self.__dict__ = self


@pytest.fixture()
def confluence(mocker):
    from md2cf.api import MinimalConfluence

    mocker.patch("md2cf.api.tortilla", mocker.Mock())

    return MinimalConfluence(host="http://example.com/", username="foo", password="bar")


def test_object_properly_initialized(confluence, mocker):
    assert isinstance(confluence.api, mocker.Mock)


def test_get_page_with_page_id(confluence):
    test_page_id = 12345
    test_return_value = "some_stuff"
    confluence.api.content.get.return_value = test_return_value

    page = confluence.get_page(page_id=test_page_id)

    confluence.api.content.get.assert_called_once_with(test_page_id)
    assert page == test_return_value


def test_get_page_with_title(confluence, mocker):
    test_page_title = "hellothere"
    test_page_id = 12345
    test_return_value = bunchify({"results": [{"id": test_page_id}]})

    confluence.api.content.get.return_value = test_return_value

    page = confluence.get_page(title=test_page_title)

    confluence.api.content.get.has_calls(
        mocker.call(params={"title": test_page_title}), mocker.call(test_page_id)
    )

    assert page == test_return_value


def test_get_page_with_title_and_space(confluence, mocker):
    test_page_title = "hellothere"
    test_page_id = 12345
    test_page_space = "ABC"
    test_return_value = bunchify({"results": [{"id": test_page_id}]})

    confluence.api.content.get.return_value = test_return_value

    page = confluence.get_page(title=test_page_title, space_key=test_page_space)

    confluence.api.content.get.has_calls(
        mocker.call(params={"title": test_page_title, "spaceKey": test_page_space}),
        mocker.call(test_page_id),
    )

    assert page == test_return_value


def test_get_page_with_all_parameters(confluence, mocker):
    test_page_title = "hellothere"
    test_page_id = 12345
    test_page_space = "ABC"
    test_return_value = bunchify({"results": [{"id": test_page_id}]})

    confluence.api.content.get.return_value = test_return_value

    page = confluence.get_page(
        page_id=test_page_id, title=test_page_title, space_key=test_page_space
    )

    confluence.api.content.get.assert_called_once_with(test_page_id)

    assert page == test_return_value


def test_get_page_without_any_parameters(confluence):
    with pytest.raises(ValueError):
        confluence.get_page()


def test_get_page_without_title_or_id(confluence):
    with pytest.raises(ValueError):
        confluence.get_page(space_key="ABC")


def test_create_page(confluence):
    test_title = "This is a title"
    test_space = "ABC"
    test_body = "<p>This is some content</p>"

    page_structure = {
        "title": test_title,
        "type": "page",
        "space": {"key": test_space},
        "body": {"storage": {"value": test_body, "representation": "storage"}},
    }

    confluence.create_page(space=test_space, title=test_title, body=test_body)

    confluence.api.content.post.assert_called_once_with(json=page_structure)


def test_create_page_with_parent(confluence):
    test_title = "This is a title"
    test_space = "ABC"
    test_body = "<p>This is some content</p>"
    test_parent_id = 12345

    page_structure = {
        "title": test_title,
        "type": "page",
        "space": {"key": test_space},
        "body": {"storage": {"value": test_body, "representation": "storage"}},
        "ancestors": [{"id": test_parent_id}],
    }

    confluence.create_page(
        space=test_space, title=test_title, body=test_body, parent_id=test_parent_id
    )

    confluence.api.content.post.assert_called_once_with(json=page_structure)


def test_create_page_with_string_parent(confluence):
    test_title = "This is a title"
    test_space = "ABC"
    test_body = "<p>This is some content</p>"
    test_parent_id = "12345"

    page_structure = {
        "title": test_title,
        "type": "page",
        "space": {"key": test_space},
        "body": {"storage": {"value": test_body, "representation": "storage"}},
        "ancestors": [{"id": int(test_parent_id)}],
    }

    confluence.create_page(
        space=test_space, title=test_title, body=test_body, parent_id=test_parent_id
    )

    confluence.api.content.post.assert_called_once_with(json=page_structure)


def test_create_page_with_message(confluence):
    test_title = "This is a title"
    test_space = "ABC"
    test_body = "<p>This is some content</p>"
    test_update_message = "This is an insightful message"

    page_structure = {
        "title": test_title,
        "type": "page",
        "space": {"key": test_space},
        "body": {"storage": {"value": test_body, "representation": "storage"}},
        "version": {"message": test_update_message},
    }

    confluence.create_page(
        space=test_space,
        title=test_title,
        body=test_body,
        update_message=test_update_message,
    )

    confluence.api.content.post.assert_called_once_with(json=page_structure)


def test_update_page(confluence):
    test_page_id = 12345
    test_page_title = "This is a title"
    test_page_version = 1

    test_page_object = bunchify(
        {
            "id": test_page_id,
            "title": test_page_title,
            "version": {"number": test_page_version},
        }
    )

    test_new_body = "<p>This is my new body</p>"

    update_structure = {
        "version": {"number": test_page_version + 1,},
        "title": test_page_title,
        "type": "page",
        "body": {"storage": {"value": test_new_body, "representation": "storage"}},
    }

    confluence.update_page(test_page_object, body=test_new_body)

    confluence.api.content.put.assert_called_once_with(
        test_page_id, json=update_structure
    )


def test_update_page_with_message(confluence):
    test_page_id = 12345
    test_page_title = "This is a title"
    test_page_version = 1
    test_page_message = "This is an incredibly descriptive update message"

    test_page_object = bunchify(
        {
            "id": test_page_id,
            "title": test_page_title,
            "version": {"number": test_page_version},
        }
    )

    test_new_body = "<p>This is my new body</p>"

    update_structure = {
        "version": {"number": test_page_version + 1, "message": test_page_message},
        "title": test_page_title,
        "type": "page",
        "body": {"storage": {"value": test_new_body, "representation": "storage"}},
    }

    confluence.update_page(
        test_page_object, body=test_new_body, update_message=test_page_message
    )

    confluence.api.content.put.assert_called_once_with(
        test_page_id, json=update_structure
    )
