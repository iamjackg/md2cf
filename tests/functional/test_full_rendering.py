import pytest

from md2cf import document


@pytest.fixture(scope="module")
def script_loc(request):
    """Return the directory of the currently running test script"""

    # uses .join instead of .dirname so we get a LocalPath object instead of
    # a string. LocalPath.join calls normpath for us when joining the path
    return request.fspath.join("..")


def test_full_document(script_loc):
    markdown_path = script_loc.join("test.md")

    with open(str(script_loc.join("result.xml"))) as result_file:
        result_data = result_file.read()

    page = document.get_page_data_from_file_path(markdown_path)

    assert page.body == result_data
    assert page.title == "Markdown: Syntax"
