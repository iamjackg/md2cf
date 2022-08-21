import md2cf.document as doc
from pathlib import Path

from tests.utils import FakePage


def test_page_get_content_hash():
    p = doc.Page(title="test title", body="test content")

    assert p.get_content_hash() == "1eebdf4fdc9fc7bf283031b93f9aef3338de9052"


def test_get_pages_from_directory(fs):
    fs.create_file("/rootfolder/rootfolderfile.md")
    fs.create_dir("/rootfolder/emptydir")
    fs.create_file("/rootfolder/parent/child/childfile.md")

    result = doc.get_pages_from_directory(Path("/rootfolder"))
    assert result == [
        FakePage(
            title="rootfolderfile",
            file_path=Path("/rootfolder/rootfolderfile.md", parent_title=None),
        ),
        FakePage(title="parent", file_path=None, parent_title=None),
        FakePage(title="child", file_path=None, parent_title="parent"),
        FakePage(
            title="childfile",
            file_path=Path("/rootfolder/parent/child/childfile.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_collapse_single_pages(fs):
    fs.create_file("/rootfolder/rootfolderfile.md")
    fs.create_file("/rootfolder/parent/child/childfile.md")

    result = doc.get_pages_from_directory(
        Path("/rootfolder"), collapse_single_pages=True
    )
    assert result == [
        FakePage(
            title="rootfolderfile",
            file_path=Path("/rootfolder/rootfolderfile.md", parent_title=None),
        ),
        FakePage(title="parent", file_path=None, parent_title=None),
        FakePage(
            title="childfile",
            file_path=Path("/rootfolder/parent/child/childfile.md"),
            parent_title="parent",
        ),
    ]


def test_get_pages_from_directory_collapse_single_pages_no_non_empty_parent(fs):
    fs.create_file("/rootfolder/parent/child/childfile.md")

    result = doc.get_pages_from_directory(
        Path("/rootfolder"), collapse_single_pages=True
    )
    assert result == [
        FakePage(
            title="parent",
        ),
        FakePage(
            title="childfile",
            file_path=Path("/rootfolder/parent/child/childfile.md"),
            parent_title="parent",
        ),
    ]


def test_get_pages_from_directory_skip_empty(fs):
    fs.create_file("/rootfolder/rootfolderfile.md")
    fs.create_file("/rootfolder/parent/child/childfile.md")

    result = doc.get_pages_from_directory(Path("/rootfolder"), skip_empty=True)
    assert result == [
        FakePage(
            title="rootfolderfile",
            file_path=Path("/rootfolder/rootfolderfile.md", parent_title=None),
        ),
        FakePage(
            title="child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="childfile",
            file_path=Path("/rootfolder/parent/child/childfile.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_skip_empty_no_non_empty_parent(fs):
    fs.create_file("/rootfolder/parent/child/childfile.md")

    result = doc.get_pages_from_directory(Path("/rootfolder"), skip_empty=True)
    assert result == [
        FakePage(
            title="child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="childfile",
            file_path=Path("/rootfolder/parent/child/childfile.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_collapse_empty(fs):
    fs.create_file("/rootfolder/rootfolderfile.md")
    fs.create_file("/rootfolder/parent/child/childfile.md")

    result = doc.get_pages_from_directory(Path("/rootfolder"), collapse_empty=True)
    assert result == [
        FakePage(
            title="rootfolderfile",
            file_path=Path("/rootfolder/rootfolderfile.md", parent_title=None),
        ),
        FakePage(
            title="parent/child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="childfile",
            file_path=Path("/rootfolder/parent/child/childfile.md"),
            parent_title="parent/child",
        ),
    ]


def test_get_pages_from_directory_collapse_empty_no_non_empty_parent(fs):
    fs.create_file("/rootfolder/parent/child/childfile.md")

    result = doc.get_pages_from_directory(Path("/rootfolder"), collapse_empty=True)
    assert result == [
        FakePage(
            title="parent/child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="childfile",
            file_path=Path("/rootfolder/parent/child/childfile.md"),
            parent_title="parent/child",
        ),
    ]


def test_get_pages_from_directory_beautify_folders(fs):
    fs.create_file("/rootfolder/ugly-folder/another_yucky_folder/childfile.md")

    result = doc.get_pages_from_directory(Path("/rootfolder"), beautify_folders=True)
    assert result == [
        FakePage(
            title="Ugly folder",
        ),
        FakePage(
            title="Another yucky folder",
        ),
        FakePage(
            title="childfile",
            file_path=Path("/rootfolder/ugly-folder/another_yucky_folder/childfile.md"),
            parent_title="Another yucky folder",
        ),
    ]
