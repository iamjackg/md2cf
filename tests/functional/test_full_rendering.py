import pytest

from md2cf.confluence_renderer import ConfluenceRenderer
import mistune


@pytest.fixture(scope="module")
def script_loc(request):
    """Return the directory of the currently running test script"""

    # uses .join instead of .dirname so we get a LocalPath object instead of
    # a string. LocalPath.join calls normpath for us when joining the path
    return request.fspath.join('..')


def test_full_document(script_loc):
    with open(str(script_loc.join('test.md'))) as test_file:
        markdown_data = test_file.read()

    with open(str(script_loc.join('result.xml'))) as result_file:
        result_data = result_file.read()

    renderer = ConfluenceRenderer(use_xhtml=True)
    confluence_mistune = mistune.Markdown(renderer=renderer)
    confluence_content = confluence_mistune(markdown_data)

    assert confluence_content == result_data
