from pathlib import Path
from os import mkdir

from tempfile import TemporaryDirectory
from md2cf.ignored_files import GitRepository

README = """# Title

Lorem ipsum
"""

GITIGNORE = """README.md
"""

ROOT_GITIGNORE = """subdir_root_ignore/README.md
"""


def _create_readme(dirpath: Path):
    """
    :param dirpath: Create a README.md in the directory
    :return:
    """
    filepath = dirpath.joinpath("README.md")
    with open(filepath, mode="w") as f:
        f.write(README)


def _create_gitignore(dirpath: Path, content: str = GITIGNORE):
    """
    Create a .gitignore file that ignores the local README file
    :param dirpath:
    :return:
    """
    filepath = dirpath.joinpath(".gitignore")
    with open(filepath, mode="w") as f:
        f.write(content)


def _create_subdir(root_path: Path, name: str, ignore_readme=False):
    """
    Create a subdirectory <name> with a README.md and optionally a .gitignore
    :param root_path:
    :param name:
    :param ignore_readme:
    :return:
    """
    subdir_path = root_path.joinpath(name)
    mkdir(subdir_path)
    _create_readme(subdir_path)
    print(f"created {subdir_path}")
    if ignore_readme:
        _create_gitignore(subdir_path)


def _create_test_project(root_path: Path):
    """
    Create a test project with:
    * A root README that should be parsed,
    * A subdir_included with a readme that should be parsed
    * A subdir_local_ignore with a README and a .gitignore that ignores that README
    * A subdir_root_ignore with a README that is ignored in the root .gitignore

    :param root_path: The dir to create the project in
    """
    mkdir(root_path.joinpath(".git"))
    _create_readme(root_path)
    _create_gitignore(root_path, content=ROOT_GITIGNORE)

    _create_subdir(root_path, "subdir_included")
    _create_subdir(root_path, "subdir_local_ignore", ignore_readme=True)
    _create_subdir(root_path, "subdir_root_ignore")


def test_collect_gitignores():
    with TemporaryDirectory(prefix="test_ignored_files_") as root_dir:
        root_path = Path(root_dir)
        _create_test_project(root_path)
        git_repo = GitRepository(root_path)

        expected_root_gitignore = root_path.joinpath(".gitignore")
        expected_subdir_gitignore = root_path.joinpath(
            "subdir_local_ignore", ".gitignore"
        )

        gitignores = git_repo.collect_gitignores(root_path)
        assert gitignores == [expected_root_gitignore]

        gitignores = git_repo.collect_gitignores(root_path.joinpath("subdir_included"))
        assert gitignores == [expected_root_gitignore]

        gitignores = git_repo.collect_gitignores(
            root_path.joinpath("subdir_root_ignore")
        )
        assert gitignores == [expected_root_gitignore]

        gitignores = git_repo.collect_gitignores(
            root_path.joinpath("subdir_local_ignore")
        )
        assert gitignores == [expected_subdir_gitignore, expected_root_gitignore]


def test_is_ignored():
    with TemporaryDirectory(prefix="test_ignored_files_") as root_dir:
        root_path = Path(root_dir)
        _create_test_project(root_path)
        git_repo = GitRepository(root_path)

        expected_root_readme = root_path.joinpath("README.md")
        assert not git_repo.is_ignored(expected_root_readme)

        expected_included_readme = root_path.joinpath("subdir_included", "README.md")
        assert not git_repo.is_ignored(expected_included_readme)

        expected_root_excluded_readme = root_path.joinpath(
            "subdir_root_ignore", "README.md"
        )
        assert git_repo.is_ignored(expected_root_excluded_readme)

        expected_local_excluded_readme = root_path.joinpath(
            "subdir_local_ignore", "README.md"
        )
        assert git_repo.is_ignored(expected_local_excluded_readme)


def test_is_ignored_with_disabled_gitignores():
    with TemporaryDirectory(prefix="test_ignored_files_") as root_dir:
        root_path = Path(root_dir)
        _create_test_project(root_path)
        git_repo = GitRepository(root_path, use_gitignore=False)

        expected_root_readme = root_path.joinpath("README.md")
        assert not git_repo.is_ignored(expected_root_readme)

        expected_included_readme = root_path.joinpath("subdir_included", "README.md")
        assert not git_repo.is_ignored(expected_included_readme)

        expected_root_excluded_readme = root_path.joinpath(
            "subdir_root_ignore", "README.md"
        )
        assert not git_repo.is_ignored(expected_root_excluded_readme)

        expected_local_excluded_readme = root_path.joinpath(
            "subdir_local_ignore", "README.md"
        )
        assert not git_repo.is_ignored(expected_local_excluded_readme)
