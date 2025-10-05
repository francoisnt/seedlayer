#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["gitpython"]
# ///
"""Clean API docs directory and build Sphinx HTML documentation."""

import shutil
import subprocess
from pathlib import Path

from git import Repo


def main() -> None:
    """Find the repository, clean the API docs directory, and build Sphinx HTML documentation."""
    # Find repo root
    try:
        repo = Repo(Path.cwd(), search_parent_directories=True)
    except Exception as err:
        raise RuntimeError("No valid Git repository found") from err

    if repo.working_tree_dir is None:
        raise RuntimeError("Repository is bare, cannot find working tree directory")

    docs_root = Path(repo.working_tree_dir) / "docs"

    # Define paths
    src = docs_root / "source"
    build = docs_root / "build"
    api = src / "api"

    # Clean docs/source/api
    if api.exists():
        shutil.rmtree(api)
    api.mkdir(parents=True)

    # Build Sphinx docs
    sphinx_build_path = shutil.which("sphinx-build")
    if sphinx_build_path is None:
        raise RuntimeError("sphinx-build not found in PATH")
    subprocess.run([sphinx_build_path, "-b", "html", str(src), str(build)]).check_returncode()  # noqa: S603


if __name__ == "__main__":
    main()
