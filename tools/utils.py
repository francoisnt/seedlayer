from pathlib import Path

from git import Repo


def get_repo_absolute_path() -> Path:
    """Find the repository, clean the API docs directory, and build Sphinx HTML documentation."""
    # Find repo root
    try:
        repo = Repo(Path.cwd(), search_parent_directories=True)
    except Exception as err:
        raise RuntimeError("No valid Git repository found") from err

    if repo.working_tree_dir is None:
        raise RuntimeError("Repository is bare, cannot find working tree directory")

    return Path(repo.working_tree_dir)
