from pathlib import Path

import md2cf.document as doc
from tests.utils import FakePage

ROOT_GITIGNORE = """.git
"""


def test_page_get_content_hash():
    p = doc.Page(title="test title", body="test content")

    assert p.get_content_hash() == "1eebdf4fdc9fc7bf283031b93f9aef3338de9052"


def test_get_pages_from_directory(fs):
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_dir("/root-folder/empty-dir")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"))
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(title="parent", file_path=None, parent_title=None),
        FakePage(title="child", file_path=None, parent_title="parent"),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_use_pages(fs):
    fs.create_file("/root-folder/.gitignore", contents=ROOT_GITIGNORE)
    fs.create_dir("/root-folder/.git")
    fs.create_dir("/root-folder/.git/refs")
    fs.create_file("/root-folder/.git/refs/test.md")
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_dir("/root-folder/empty-dir")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(
        Path("/root-folder"), use_pages_file=True, enable_relative_links=True
    )
    print(result)
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(title="parent", file_path=None, parent_title=None),
        FakePage(title="child", file_path=None, parent_title="parent"),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_collapse_single_pages(fs):
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(
        Path("/root-folder"), collapse_single_pages=True
    )
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(title="parent", file_path=None, parent_title=None),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="parent",
        ),
    ]


def test_get_pages_from_directory_collapse_single_pages_no_non_empty_parent(fs):
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(
        Path("/root-folder"), collapse_single_pages=True
    )
    assert result == [
        FakePage(
            title="parent",
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="parent",
        ),
    ]


def test_get_pages_from_directory_skip_empty(fs):
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), skip_empty=True)
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(
            title="child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_skip_empty_no_non_empty_parent(fs):
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), skip_empty=True)
    assert result == [
        FakePage(
            title="child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_collapse_empty(fs):
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), collapse_empty=True)
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(
            title="parent/child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="parent/child",
        ),
    ]


def test_get_pages_from_directory_collapse_empty_no_non_empty_parent(fs):
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), collapse_empty=True)
    assert result == [
        FakePage(
            title="parent/child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="parent/child",
        ),
    ]


def test_get_pages_from_directory_beautify_folders(fs):
    fs.create_file("/root-folder/ugly-folder/another_yucky_folder/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), beautify_folders=True)
    assert result == [
        FakePage(
            title="Ugly folder",
        ),
        FakePage(
            title="Another yucky folder",
        ),
        FakePage(
            title="child-file",
            file_path=Path(
                "/root-folder/ugly-folder/another_yucky_folder/child-file.md"
            ),
            parent_title="Another yucky folder",
        ),
    ]


def test_get_document_frontmatter():
    source_markdown = """---
title: This is a title
labels:
  - label1
  - label2
---
# This is normal markdown content

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {
        "title": "This is a title",
        "labels": ["label1", "label2"],
        "frontmatter_end_line": 6,
    }


def test_get_document_frontmatter_only_first():
    source_markdown = """---
title: This is a title
---
# This is normal markdown content

---

With other triple dashes!

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {
        "title": "This is a title",
        "frontmatter_end_line": 3,
    }


def test_get_document_frontmatter_no_closing():
    source_markdown = """---
# This is normal markdown content

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {}


def test_get_document_frontmatter_extra_whitespace():
    source_markdown = """

---
title: This is a title
---
# This is normal markdown content

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {}


def test_get_document_frontmatter_empty():
    source_markdown = """---
---
# This is normal markdown content

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {}
