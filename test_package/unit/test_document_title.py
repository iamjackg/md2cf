from pathlib import Path

import md2cf.document as doc
from test_package.utils import FakePage


def test_get_page_title_from_file(fs):
    fs.create_file("/root-folder/some-page.md", contents="# Title from within file")

    result = doc.get_page_data_from_file_path(
        Path("/root-folder/some-page.md"), page_title_from_filename=False
    )
    assert result == FakePage(
        title="Title from within file",
    )


def test_get_page_title_from_filename_if_no_title_in_file(fs):
    fs.create_file("/root-folder/some-page.md")

    result = doc.get_page_data_from_file_path(
        Path("/root-folder/some-page.md"), page_title_from_filename=False
    )
    assert result == FakePage(
        title="some-page",
    )


def test_get_page_title_from_filename_if_no_page_title_in_file(fs):
    fs.create_file("/root-folder/some-page.md", contents="")

    result = doc.get_page_data_from_file_path(
        Path("/root-folder/some-page.md"), page_title_from_filename=True
    )
    assert result == FakePage(
        title="some-page",
    )


def test_get_page_title_from_filename_if_page_title_in_file(fs):
    fs.create_file("/root-folder/some-page.md", contents="# Title from within file")

    result = doc.get_page_data_from_file_path(
        Path("/root-folder/some-page.md"), page_title_from_filename=True
    )
    assert result == FakePage(
        title="some-page",
    )
