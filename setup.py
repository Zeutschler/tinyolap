#!/usr/bin/env python
from setuptools import setup

# ...to run the build and deploy process to PyPi.org:
# python3 setup.py sdist bdist_wheel   # note: Wheel need to be installed: pip install wheel
# twine upload dist/*                  # note: Twine need to be installed pip install twine

# ... via Github actions
# https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/

VERSION = '0.8.0'
DESCRIPTION = "TinyOlap: A multi-dimensional in-memory OLAP database in plain Python 3."
LONG_DESCRIPTION = """
TinyOlap is a minimal in-process in-memory multi-dimensional database with numerical aggregations 
and calculations in mind. First a multi-dimensional data model needs to be defined, consisting of 
cubes, dimensions, members, hierarchies etc. Afterwards additional calculation logic can be added 
through arbitrary Python code. Data access is cell-based or range-based. A minimal support for SQL 
in also provided. All calculations will be executed on the fly. Optionally, persistence is provided
through SQLite. TinyOlap is a byproduct of a research project, intended to mimic the behavior and 
capabilities of real-world MOLAP databases (e.g. IBM TM/1, SAP HANA or Jedox PALO) but with a super 
minimal footprint. TinyOlap is best suited for interactive planning, forecasting, simulation and 
general multidimensional numerical problems.          
"""

setup(
    name="tinyolap",
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
        "Topic :: Database :: Database Engines/Servers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    author="Thomas Zeutschler",
    keywords=['database', 'olap', 'molap', 'planning', 'simulation', 'forecasting',
              'multidimensional', 'cube', 'business rules', 'calculation'],
    author_email="margins.roadmap_0t@icloud.com",
    url="http://github.com/zeutschler/tinyolap/",
    license="MIT License",
    platforms=['any'],
    zip_safe=True,
    python_requires='>=3.8',
    install_requires=[
        'cryptography',
        'sqlparse'
    ],
    test_suite="tinyolap.tests",
    packages=['tinyolap'],
    project_urls={
        'Homepage': 'https://tinyolap.com',
        'Documentation': 'https://tinyolap.com/docs',
        'GitHub': 'https://github.com/Zeutschler/tinyolap',
    },
)