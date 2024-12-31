# -*- coding: utf-8 -*-
# Copyright (C) 2024
#   Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
#   Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger
#

"""Configuration file for the Sphinx documentation builder.

This module configures Sphinx to generate documentation for the GenAI project.

"""

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "GenAI"  # pylint: disable=invalid-name

copyright = (  # noqa: A001 # pylint: disable=redefined-builtin, invalid-name
    "2024, Leonhard Thomas Schwertfeger and Benjamin Thomas Schwertfeger"
)

author = "Leonhard Thomas Schwertfeger and Benjamin Thomas Schwertfeger"  # pylint: disable=invalid-name

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "nbsphinx",
    "sphinx_click",
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    "IPython.sphinxext.ipython_console_highlighting",
]

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "links.rst",
    "**.ipynb_checkpoints",
]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"  # pylint: disable=invalid-name
html_context = {
    "display_github": True,
    "github_user": "LeonhardSchwertfeger",
    "github_repo": "genai",
    "github_version": "master/docs/",
}
html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 4,
}
