import io

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


TEST_HOST = "http://example.com/api/"


@pytest.fixture()
def confluence():
    from md2cf.api import MinimalConfluence

    c = MinimalConfluence(host=TEST_HOST, username="foo", password="bar")

    return c


def test_user_pass_auth():
    import md2cf.api as api

    c = api.MinimalConfluence(
        host="http://example.com/", username="foo", password="bar"
    )

    auth = c.api.auth

    assert auth == ("foo", "bar")


def test_token_auth():
    import md2cf.api as api

    c = api.MinimalConfluence(host="http://example.com/", token="hello")

    assert c.api.auth is None
    assert c.api.headers["Authorization"] == "Bearer hello"


def test_get_page_with_page_id(confluence, requests_mock):
    test_page_id = 12345
    test_return_value = {"some_stuff": 1}

    requests_mock.get(TEST_HOST + f"content/{test_page_id}", json=test_return_value)
    page = confluence.get_page(page_id=test_page_id)

    assert page == bunchify(test_return_value)


def test_get_page_with_page_id_and_one_expansion(confluence, requests_mock):
    test_page_id = 12345
    test_return_value = {"some_stuff": 1}

    requests_mock.get(
        TEST_HOST + f"content/{test_page_id}?expand=history",
        complete_qs=True,
        json=test_return_value,
    )
    page = confluence.get_page(page_id=test_page_id, additional_expansions=["history"])

    assert page == test_return_value


def test_get_page_with_page_id_and_multiple_expansions(confluence, requests_mock):
    test_page_id = 12345
    test_return_value = {"some_stuff": 1}

    requests_mock.get(
        TEST_HOST + f"content/{test_page_id}?expand=history,version",
        complete_qs=True,
        json=test_return_value,
    )
    page = confluence.get_page(
        page_id=test_page_id, additional_expansions=["history", "version"]
    )

    assert page == test_return_value


def test_get_page_with_title(confluence, mocker, requests_mock):
    test_page_title = "hellothere"
    test_page_id = 12345
    test_return_value = {"results": [{"id": test_page_id}]}

    requests_mock.get(
        TEST_HOST + f"content?title={test_page_title}&type=page",
        complete_qs=True,
        json=test_return_value,
    )
    requests_mock.get(TEST_HOST + f"content/{test_page_id}", json=test_return_value)
    page = confluence.get_page(title=test_page_title)

    assert page == bunchify(test_return_value)


def test_get_page_with_title_and_space(confluence, mocker, requests_mock):
    test_page_title = "hellothere"
    test_page_id = 12345
    test_page_space = "ABC"
    test_return_value = {"results": [{"id": test_page_id}]}

    requests_mock.get(
        TEST_HOST
        + f"content?title={test_page_title}&type=page&spaceKey={test_page_space}",
        complete_qs=True,
        json=test_return_value,
    )
    requests_mock.get(TEST_HOST + f"content/{test_page_id}", json=test_return_value)
    page = confluence.get_page(title=test_page_title, space_key=test_page_space)

    assert page == bunchify(test_return_value)


def test_get_page_with_all_parameters(confluence, mocker, requests_mock):
    test_page_title = "hellothere"
    test_page_id = 12345
    test_page_space = "ABC"
    test_return_value = {"results": [{"id": test_page_id}]}

    requests_mock.get(
        TEST_HOST + f"content/{test_page_id}?expand=history",
        complete_qs=True,
        json=test_return_value,
    )

    page = confluence.get_page(
        page_id=test_page_id,
        title=test_page_title,
        space_key=test_page_space,
        additional_expansions=["history"],
    )

    assert page == test_return_value


def test_get_page_without_any_parameters(confluence, requests_mock):
    with pytest.raises(ValueError):
        confluence.get_page()


def test_get_page_without_title_or_id(confluence, requests_mock):
    with pytest.raises(ValueError):
        confluence.get_page(space_key="ABC")


def test_create_page(confluence, requests_mock):
    test_title = "This is a title"
    test_space = "ABC"
    test_body = "<p>This is some content</p>"

    page_structure = {
        "title": test_title,
        "type": "page",
        "space": {"key": test_space},
        "body": {"storage": {"value": test_body, "representation": "storage"}},
    }

    created_page = {"test": 1}

    requests_mock.post(
        TEST_HOST + "content",
        complete_qs=True,
        json=created_page,
        additional_matcher=lambda x: x.json() == page_structure,
    )
    page = confluence.create_page(space=test_space, title=test_title, body=test_body)

    assert page == created_page


def test_create_page_with_parent(confluence, requests_mock):
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

    created_page = {"test": 1}
    requests_mock.post(
        TEST_HOST + "content",
        complete_qs=True,
        json=created_page,
        additional_matcher=lambda x: x.json() == page_structure,
    )

    page = confluence.create_page(
        space=test_space, title=test_title, body=test_body, parent_id=test_parent_id
    )

    assert page == created_page


def test_create_page_with_string_parent(confluence, requests_mock):
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

    created_page = {"test": 1}
    requests_mock.post(
        TEST_HOST + "content",
        complete_qs=True,
        json=created_page,
        additional_matcher=lambda x: x.json() == page_structure,
    )

    page = confluence.create_page(
        space=test_space, title=test_title, body=test_body, parent_id=test_parent_id
    )

    assert page == created_page


def test_create_page_with_message(confluence, requests_mock):
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

    created_page = {"test": 1}
    requests_mock.post(
        TEST_HOST + "content",
        complete_qs=True,
        json=created_page,
        additional_matcher=lambda x: x.json() == page_structure,
    )

    page = confluence.create_page(
        space=test_space,
        title=test_title,
        body=test_body,
        update_message=test_update_message,
    )

    assert page == created_page


def test_update_page(confluence, requests_mock):
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
        "version": {"number": test_page_version + 1, "minorEdit": False},
        "title": test_page_title,
        "type": "page",
        "body": {"storage": {"value": test_new_body, "representation": "storage"}},
    }

    updated_page = {"test": 1}
    requests_mock.put(
        TEST_HOST + f"content/{test_page_id}",
        complete_qs=True,
        json=updated_page,
        additional_matcher=lambda x: x.json() == update_structure,
    )

    page = confluence.update_page(test_page_object, body=test_new_body)

    assert page == updated_page

def test_update_page_with_status(confluence, requests_mock):
    test_page_id = 12345
    test_page_title = "This is a title"
    test_page_version = 1
    test_page_status = "trashed"

    test_page_object = bunchify(
        {
            "id": test_page_id,
            "title": test_page_title,
            "version": {"number": test_page_version},
        }
    )

    test_new_body = "<p>This is my new body</p>"

    update_structure = {
        "version": {"number": test_page_version + 1, "minorEdit": False},
        "title": test_page_title,
        "type": "page",
        "body": {"storage": {"value": test_new_body, "representation": "storage"}},
        "status": test_page_status
    }

    updated_page = {"test": 1}
    requests_mock.put(
        TEST_HOST + f"content/{test_page_id}",
        complete_qs=True,
        json=updated_page,
        additional_matcher=lambda x: x.json() == update_structure,
    )

    page = confluence.update_page(test_page_object, body=test_new_body, status=test_page_status)

    assert page == updated_page

def test_update_page_with_wrong_status(confluence, requests_mock):
    test_page_id = 12345
    test_page_title = "This is a title"
    test_page_version = 1
    test_page_status = "I do not exist"

    test_page_object = bunchify(
        {
            "id": test_page_id,
            "title": test_page_title,
            "version": {"number": test_page_version},
        }
    )

    test_new_body = "<p>This is my new body</p>"

    with pytest.raises(ValueError):
        confluence.update_page(test_page_object, body=test_new_body, status=test_page_status)

def test_update_page_with_message(confluence, requests_mock):
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
        "version": {
            "number": test_page_version + 1,
            "message": test_page_message,
            "minorEdit": False,
        },
        "title": test_page_title,
        "type": "page",
        "body": {"storage": {"value": test_new_body, "representation": "storage"}},
    }

    updated_page = {"test": 1}
    requests_mock.put(
        TEST_HOST + f"content/{test_page_id}",
        complete_qs=True,
        json=updated_page,
        additional_matcher=lambda x: x.json() == update_structure,
    )

    page = confluence.update_page(
        test_page_object, body=test_new_body, update_message=test_page_message
    )

    assert page == updated_page


def test_create_attachment(mocker, confluence, requests_mock):
    test_page = bunchify({"id": 123})
    file_contents = b"12345"
    test_fp = io.BytesIO(file_contents)

    test_response = {"test": 1}
    requests_mock.post(
        TEST_HOST + f"content/{test_page.id}/child/attachment?allowDuplicated=true",
        complete_qs=True,
        json=test_response,
        headers={"X-Atlassian-Token": "nocheck"},
    )
    response = confluence.create_attachment(test_page, test_fp)

    assert response == test_response


def test_update_attachment(mocker, confluence, requests_mock):
    test_page = bunchify({"id": 123})
    test_attachment = bunchify({"id": 3241})
    file_contents = b"12345"
    test_fp = io.BytesIO(file_contents)

    test_response = {"test": 1}
    requests_mock.post(
        TEST_HOST
        + f"content/{test_page.id}/child/attachment/{test_attachment.id}/data",
        complete_qs=True,
        json=test_response,
        headers={"X-Atlassian-Token": "nocheck"},
    )
    response = confluence.update_attachment(test_page, test_fp, test_attachment)

    assert response == test_response

def test_get_content_descendant_with_page_id(confluence, requests_mock):
    test_page_id = 12345
    test_content_type = "page"
    test_return_value = { "results": [{"some_stuff": 1}] }

    requests_mock.get(TEST_HOST + f"content/{test_page_id}/descendant/{test_content_type}", json=test_return_value)
    page = confluence.get_content_descendant(page_id=test_page_id)

    assert page == bunchify(test_return_value["results"])

def test_get_content_descendant_with_page_id_and_next_link(confluence, requests_mock):
    test_page_id = 12345
    test_content_type = "page"
    test_return_value2_next_url = TEST_HOST + "/next-api-call"
    test_return_value1 = { 
        "results": [{"id": 1}],
        "_links": {
            "next": test_return_value2_next_url
        }    
    }
    test_return_value2 = {
        "results": [{"id": 2}],
    }
    expected_result = [{ "id": 1 }, { "id": 2 }]
    
    requests_mock.get(TEST_HOST + f"content/{test_page_id}/descendant/{test_content_type}", json=test_return_value1)
    requests_mock.get(f"{test_return_value2_next_url}", json=test_return_value2)
    page = confluence.get_content_descendant(page_id=test_page_id)

    assert page == bunchify(expected_result)

def test_get_content_descendant_with_title(confluence, requests_mock):
    test_page_title = "test title"
    test_page_id = 12345
    test_content_type = "page"
    test_return_value = { "results": [{"some_stuff": 1}] }
    test_get_page_from_title_return_value = {"results": [{"id": test_page_id}]}
    requests_mock.get(
        TEST_HOST + f"content?title={test_page_title}&type=page",
        complete_qs=True,
        json=test_get_page_from_title_return_value,
    )
    requests_mock.get(TEST_HOST + f"content/{test_page_id}/descendant/{test_content_type}", json=test_return_value)

    page = confluence.get_content_descendant(title=test_page_title)

    assert page == bunchify(test_return_value["results"])

def test_get_content_descendant_without_page_id_or_title(confluence, requests_mock):
    test_space_key = "ABC"
    test_homepage_id = 54321
    test_space_return_value = { "_expandable": { "homepage": f"/rest/api/content/{test_homepage_id}"}}

    test_content_type = "page"
    test_return_value = { "results": [{"some_stuff": 1}] }

    requests_mock.get(
        TEST_HOST + f"space/{test_space_key}",
        complete_qs=True,
        json=test_space_return_value,
    )

    requests_mock.get(TEST_HOST + f"content/{test_homepage_id}/descendant/{test_content_type}", json=test_return_value)

    page = confluence.get_content_descendant(space_key=test_space_key)

    assert page == bunchify(test_return_value["results"])

def test_get_content_descendant_without_any_parameters(confluence):
    with pytest.raises(ValueError):
        confluence.get_content_descendant()

def test_purge_page(confluence, requests_mock):
    test_page_id = 12345
    test_page_title = "This is a title"
    test_page_version = 1
    test_page_body = ""
    test_page_status = "trashed"
    test_get_page_return_value = bunchify(
        {
            "id": test_page_id,
            "title": test_page_title,
            "version": {"number": test_page_version},
        }
    )

    test_get_descendant_page_object = bunchify(
        {
            "id": test_page_id,
            "title": test_page_title,
            "_expandable": { "body": test_page_body }
        }
    )

    update_structure = {
        "version": {
            "number": test_page_version + 1,
            "minorEdit": False,
        },
        "title": test_page_title,
        "type": "page",
        "body": {"storage": {"value": test_page_body, "representation": "storage"}},
        "status": test_page_status
    }


    requests_mock.get(TEST_HOST + f"content/{test_page_id}", json=test_get_page_return_value)
    requests_mock.put(
        TEST_HOST + f"content/{test_page_id}",
        json=update_structure,
        additional_matcher=lambda x: x.json() == update_structure,
    )

    requests_mock.delete(TEST_HOST + f"content/{test_page_id}")
    response = confluence.purge_page(test_get_descendant_page_object)

    assert response.status_code == 200

def test_purge_page_without_any_parameters(confluence):
    with pytest.raises(ValueError):
        confluence.purge_page()
