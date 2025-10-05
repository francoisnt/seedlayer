import os
import subprocess
import sys
from pathlib import Path

import toml
from git import Repo
from sphinx.application import Sphinx

# Add project root (Git root) to sys.path
repo = Repo(Path.cwd(), search_parent_directories=True)
if repo.working_tree_dir is None:
    raise RuntimeError("Repository is bare")

project_root = Path(repo.working_tree_dir)
sys.path.insert(0, str(project_root))

# Read version from pyproject.toml
pyproject_path = os.path.join(project_root, "pyproject.toml")
try:
    with open(pyproject_path) as f:
        pyproject_data = toml.load(f)
except (FileNotFoundError, KeyError) as err:
    raise RuntimeError("pyproject.toml file not found") from err

try:
    project_version = pyproject_data["project"]["version"]
    project_authors = [
        author["name"] for author in pyproject_data.get("project", {}).get("authors", [])
    ]
    project_name = pyproject_data["project"]["name"]
except KeyError as err:
    raise RuntimeError("could not read values from pyproject.toml") from err


# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = project_name
author = ", ".join(project_authors)
copyright = ", ".join(["2025-%Y", author])
release = project_version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
    "faker": ("https://faker.readthedocs.io/en/master/", None),
}

needs_sphinx = "8.2.3"

templates_path = ["_templates"]
exclude_patterns = ["Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]

# Mock dependencies to avoid import errors
# sys.modules["sqlalchemy"] = MagicMock()
# sys.modules["faker"] = MagicMock()
autodoc_mock_imports = ["sqlalchemy", "faker"]

# Autosummary/Autodoc settings
autosummary_generate = True
autodoc_typehints = "both"  # render hints in the signature and body
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}


# Auto-generate .rst files during build
def run_apidoc(app: Sphinx) -> None:
    """Generate .rst files with sphinx-apidoc before building."""
    source_dir = os.path.join(project_root, "docs", "source", "api")
    package_dir = os.path.join(project_root, "src", "seedlayer")
    cmd = [
        "sphinx-apidoc",
        "-f",  # Force overwrite
        "-e",  # separate module pages
        "-M",  # put module doc at top of page
        "-o",
        str(source_dir),
        str(package_dir),
    ]
    subprocess.check_call(cmd)  # noqa S603


def setup(app: Sphinx) -> None:
    """Register the apidoc generation for the builder-inited event."""
    app.connect("builder-inited", run_apidoc)
