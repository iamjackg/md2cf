import pytest

from md2cf import document
import mistune


@pytest.fixture(scope="module")
def script_loc(request):
    """Return the directory of the currently running test script"""

    # uses .join instead of .dirname so we get a LocalPath object instead of
    # a string. LocalPath.join calls normpath for us when joining the path
    return request.fspath.join("..")


def test_full_document(script_loc):
    with open(str(script_loc.join("test.md"))) as test_file:
        markdown_data = test_file.read()

    with open(str(script_loc.join("result.xml"))) as result_file:
        result_data = result_file.read()

    page = document.parse_page(markdown_data)

    assert page.body == result_data
    assert page.title == "Markdown: Syntax"
