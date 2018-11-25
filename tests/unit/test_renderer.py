import pytest
from md2cf.confluence_renderer import ConfluenceTag, ConfluenceRenderer


def test_add_namespace():
    assert ConfluenceTag.add_namespace('tagname', 'namespace') == 'namespace:tagname'


def test_tag_append():
    tag = ConfluenceTag('irrelevant')
    other_tag = ConfluenceTag('alsoirrelevant')

    tag.append(other_tag)

    assert tag.children == [other_tag]


def test_tag_render():
    test_tag_type = 'structured-macro'
    test_tag_markup = '<ac:structured-macro></ac:structured-macro>\n'

    tag = ConfluenceTag(test_tag_type)
    output = tag.render()

    assert output == test_tag_markup


def test_tag_render_with_text():
    test_tag_type = 'structured-macro'
    test_text_content = 'This is some text'
    test_tag_markup = '<ac:structured-macro>This is some text</ac:structured-macro>\n'

    tag = ConfluenceTag(test_tag_type, text=test_text_content)
    output = tag.render()

    assert output == test_tag_markup


def test_tag_render_with_cdata_text():
    test_tag_type = 'structured-macro'
    test_text_content = 'This is some text\nwith newlines'
    test_tag_markup = '<ac:structured-macro><![CDATA[This is some text\nwith newlines]]></ac:structured-macro>\n'

    tag = ConfluenceTag(test_tag_type, text=test_text_content, cdata=True)
    output = tag.render()

    assert output == test_tag_markup


def test_tag_render_with_attribute():
    test_tag_type = 'structured-macro'
    test_tag_attrib = {'name': 'code'}
    test_tag_markup = '<ac:structured-macro ac:name="code"></ac:structured-macro>\n'

    tag = ConfluenceTag(test_tag_type, attrib=test_tag_attrib)
    output = tag.render()

    assert output == test_tag_markup


def test_tag_render_with_multiple_attributes():
    test_tag_type = 'structured-macro'
    test_tag_attrib = {'name': 'code', 'foo': 'bar'}
    test_tag_markup = '<ac:structured-macro ac:name="code" ac:foo="bar"></ac:structured-macro>\n'

    tag = ConfluenceTag(test_tag_type, attrib=test_tag_attrib)
    output = tag.render()

    assert output == test_tag_markup


def test_tag_render_with_child():
    test_tag_type = 'structured-macro'
    test_other_tag_type = 'unstructured-macro'
    test_tag_markup = '<ac:structured-macro><ac:unstructured-macro></ac:unstructured-macro>\n</ac:structured-macro>\n'

    tag = ConfluenceTag(test_tag_type)
    child_tag = ConfluenceTag(test_other_tag_type)
    tag.children = [child_tag]
    output = tag.render()

    assert output == test_tag_markup


def test_tag_render_with_child_and_text():
    test_tag_type = 'structured-macro'
    test_tag_text = 'This is some text'
    test_other_tag_type = 'unstructured-macro'
    test_tag_markup = '<ac:structured-macro><ac:unstructured-macro></ac:unstructured-macro>\nThis is some text</ac:structured-macro>\n'

    tag = ConfluenceTag(test_tag_type, text=test_tag_text)
    child_tag = ConfluenceTag(test_other_tag_type)
    tag.children = [child_tag]
    output = tag.render()

    assert output == test_tag_markup


def test_renderer_block_code():
    test_code = 'this is a piece of code'
    test_markup = '<ac:structured-macro ac:name="code"><ac:parameter ac:name="linenumbers">true</ac:parameter>\n' \
                  '<ac:plain-text-body><![CDATA[this is a piece of code]]></ac:plain-text-body>\n' \
                  '</ac:structured-macro>\n'

    renderer = ConfluenceRenderer()

    assert renderer.block_code(test_code) == test_markup


def test_renderer_block_code_with_language():
    test_code = 'this is a piece of code'
    test_language = 'whitespace'
    test_markup = '<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">whitespace</ac:parameter>\n' \
                  '<ac:parameter ac:name="linenumbers">true</ac:parameter>\n' \
                  '<ac:plain-text-body><![CDATA[this is a piece of code]]></ac:plain-text-body>\n' \
                  '</ac:structured-macro>\n'

    renderer = ConfluenceRenderer()

    assert renderer.block_code(test_code, lang=test_language) == test_markup
