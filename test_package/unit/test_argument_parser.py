import pytest

from md2cf.__main__ import get_parser


def test_specify_both_title_and_title_from_filename_does_exit():
    parser = get_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--title", "some-title", "--title-from-filename"])


def test_specify_only_title_does_not_exit():
    parser = get_parser()

    parser.parse_args(["--title", "some-title"])


def test_specify_only_title_from_filename_does_not_exit():
    parser = get_parser()

    parser.parse_args(["--title-from-filename"])
