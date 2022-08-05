"""
Allow checking files for ignored status in gitignore files in the repo.
"""
from pathlib import Path
from typing import List

from gitignore_parser import parse_gitignore


def is_ignored(filepath: Path) -> bool:
    """
    Checks a file against all relevant .gitignore files in the tree
    and returns true if any of them ignores the file.
    :param filepath: a path representing a file on the filesystem
    :return: True if the file is ignored by git.
    """
    gitignores = collect_gitignores(filepath)
    matchers = [parse_gitignore(str(g)) for g in gitignores]
    return any([m(filepath) for m in matchers])


def collect_gitignores(filepath: Path) -> List[Path]:
    """
    Collect all .gitignore files from start location to the root of the
    repository. Note that a .git directory must be present in the parent tree
    for the .gitignore files to be respected.

    :param filepath: The path to start searching for .gitignore files
    :return: List of paths to .gitignore files relevant for start_path
    """

    ret = list()

    p = filepath.absolute()
    if p.is_file():
        p = p.parent
    while str(p) != '/':
        gitignore_file = p.joinpath('.gitignore')
        if gitignore_file.exists() and gitignore_file.is_file():
            ret.append(gitignore_file)
        git_dir = p.joinpath('.git')
        if git_dir.exists() and git_dir.is_dir():
            return ret
        p = p.parent

    # if not .git directory found, we're not in a git repo and gitignore files cannot
    # be trusted.
    return list()
