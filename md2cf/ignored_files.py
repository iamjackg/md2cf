"""
Allow checking files for ignored status in gitignore files in the repo.
"""
from pathlib import Path
from typing import List

from gitignore_parser import parse_gitignore


class IgnoredFiles:
    """
    Use .is_ignored(p) to check path p against all
    found gitignore files in the parent paths of the repo.
    """
    def __init__(self, start_path):
        gitignores = _collect_gitignores(start_path)
        self.matchers = [parse_gitignore(str(g)) for g in gitignores]

    def is_ignored(self, p: Path):
        """
        :param p: The path to the file to check
        :return: True if the filepath is matched in any .gitignore matchers.
        """
        return any([m(str(p)) for m in self.matchers])


def _collect_gitignores(start_path: Path) -> List[Path]:
    """
    Collect all .gitignore files from start location to the root of the
    repository. Note that a .git directory must be present in the parent tree
    for the .gitignore files to be respected.

    :param start_path: The path to start searching for .gitignore files
    :return:
    """

    ret = list()

    p = start_path.absolute()
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
