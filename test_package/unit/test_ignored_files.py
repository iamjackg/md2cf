from pathlib import Path

from pyfakefs.fake_filesystem import FakeFilesystem

from md2cf.ignored_files import GitRepository

README = """# Title

Lorem ipsum
"""

GITIGNORE = """README.md
"""

ROOT_GITIGNORE = """subdir_root_ignore/README.md
"""


def _create_test_project(fs: FakeFilesystem, root_path: Path):
    """
    Create a test project with:
    * A root README that should be parsed,
    * A subdir_included with a readme that should be parsed
    * A subdir_local_ignore with a README and a .gitignore that ignores that README
    * A subdir_root_ignore with a README that is ignored in the root .gitignore
    """
    fs.create_dir(root_path / ".git")
    fs.create_file(root_path / "README.md", contents=README)
    fs.create_file(root_path / ".gitignore", contents=ROOT_GITIGNORE)

    fs.create_file(root_path / "subdir_included/README.md", contents=README)
    fs.create_file(root_path / "subdir_root_ignore/README.md", contents=README)
    fs.create_file(root_path / "subdir_local_ignore/README.md", contents=README)
    fs.create_file(root_path / "subdir_local_ignore/.gitignore", contents=GITIGNORE)


def test_collect_gitignores(fs):
    root_path = Path("/repo")
    _create_test_project(fs, root_path)
    git_repo = GitRepository(root_path)

    expected_root_gitignore = root_path / ".gitignore"
    expected_subdir_gitignore = root_path / "subdir_local_ignore/.gitignore"

    gitignores = git_repo.collect_gitignores(root_path)
    assert gitignores == [expected_root_gitignore]

    gitignores = git_repo.collect_gitignores(root_path / "subdir_included")
    assert gitignores == [expected_root_gitignore]

    gitignores = git_repo.collect_gitignores(root_path / "subdir_root_ignore")
    assert gitignores == [expected_root_gitignore]

    gitignores = git_repo.collect_gitignores(root_path / "subdir_local_ignore")
    assert gitignores == [expected_subdir_gitignore, expected_root_gitignore]


def test_is_ignored(fs):
    root_path = Path("/repo")
    _create_test_project(fs, root_path)
    git_repo = GitRepository(root_path)

    assert not git_repo.is_ignored(root_path / "README.md")
    assert not git_repo.is_ignored(root_path / "subdir_included/README.md")

    assert git_repo.is_ignored(root_path / "subdir_root_ignore/README.md")
    assert git_repo.is_ignored(root_path / "subdir_local_ignore/README.md")


def test_is_ignored_with_disabled_gitignores(fs):
    root_path = Path("/repo")
    _create_test_project(fs, root_path)
    git_repo = GitRepository(root_path, use_gitignore=False)

    assert not git_repo.is_ignored(root_path / "README.md")
    assert not git_repo.is_ignored(root_path / "subdir_included/README.md")
    assert not git_repo.is_ignored(root_path / "subdir_root_ignore/README.md")
    assert not git_repo.is_ignored(root_path / "subdir_local_ignore/README.md")
