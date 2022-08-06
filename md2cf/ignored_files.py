"""
Allow checking files for ignored status in gitignore files in the repo.
"""
from pathlib import Path
from typing import List

from gitignore_parser import parse_gitignore


class GitRepository:
    """
    Represents a Git repository by finding the .git folder at the root
    of the tree. Note that there are cases where .git folders may exist
    in other parts of the tree. For example in terraform repositories
    the .terraform folder may contain copies of the tree including the .git
    folder.
    """
    def __init__(self, repo_path: Path):
        self.root_dir = self._find_root_dir(repo_path)

    @staticmethod
    def _find_root_dir(start_path: Path) -> Path:
        """
        Traverse the parents of the start_path until we find a .git directory
        :param start_path: A file or directory path to start searching from
        :return: The root directory of the git repo.
        """
        p = start_path.absolute()
        if p.is_file():
            p = p.parent
        while str(p) != '/':
            git_dir = p.joinpath('.git')
            if git_dir.exists() and git_dir.is_dir():
                return p
            p = p.parent
        raise Exception(f"Failed to locate .git dir for {start_path}")

    def collect_gitignores(self, filepath: Path) -> List[Path]:
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
            if p == self.root_dir:
                return ret
            p = p.parent

        # if not .git directory found, we're not in a git repo and gitignore files cannot
        # be trusted.
        return list()

    def is_ignored(self, filepath: Path) -> bool:
        """
        Check if filepath is ignored in the git repository
        :param filepath: Path to the file to check if it is ignored.
        :return: True if the file is ignored in any .gitignore file
        """
        gitignores = self.collect_gitignores(filepath)
        matchers = [parse_gitignore(str(g)) for g in gitignores]
        return any([m(filepath) for m in matchers])
