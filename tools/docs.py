#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["gitpython"]
# ///
"""Clean API docs directory and build Sphinx HTML documentation."""

import shutil
import subprocess
from pathlib import Path

from .utils import get_repo_absolute_path


def main() -> None:
    """Find the repository, clean the API docs directory, and build Sphinx HTML documentation."""
    docs_root = Path(get_repo_absolute_path()) / "docs"

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
