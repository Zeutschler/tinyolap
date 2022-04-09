
# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(1, os.path.abspath('../../'))
sys.path.insert(2, os.path.abspath('../../tinyolap'))
sys.path.insert(2, os.path.abspath('../../venv/lib/python3.9/site-packages'))

# -- Project information -----------------------------------------------------

project = 'TinyOlap'
copyright = '2021, Thomas Zeutschler'
author = 'Thomas Zeutschler'

# The full version, including alpha/beta/rc tags
release = '0.1.0'

github_username = "zeutschler"
github_repository = "tinyolap"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosectionlabel',
    'myst_parser',
    'enum_tools.autoenum',   # install via: python3 -m pip install enum_tools --user
    'sphinx_toolbox.shields'
]

# Make sure the target is unique
autosectionlabel_prefix_document = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

html_logo = "_logos/cube128.png"
html_title = "TinyOlap"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This trigger also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'furo'  # 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']