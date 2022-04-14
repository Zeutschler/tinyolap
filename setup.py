#!/usr/bin/env python
from setuptools import setup

# ...to run the build and deploy process to PyPi.org:
# python3 setup.py sdist bdist_wheel   # note: Wheel need to be installed: pip install wheel
# twine upload dist/*                  # note: Twine need to be installed pip install twine

# ... via Github actions
# https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/

VERSION = '0.8.13'
DESCRIPTION = "TinyOlap: A multi-dimensional in-memory OLAP database in plain Python 3."
LONG_DESCRIPTION = """
TinyOlap is a light-weight, in-process, multi-dimensional, model-first OLAP 
engine for planning, budgeting, reporting, analysis and many other numerical purposes. 
Although this sounds very complicated, TinyOlap is actually very easy to use and should 
be suitable for all levels of Python and database skills.

TinyOlap is also quite handy as a smart alternative to Pandas DataFrames when your data
is multidimensional, requires hierarchical aggregations or complex calculations.          
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
        'sqlparse',
        'enum_tools'
    ],
    test_suite="tinyolap.tests",
    packages=['tinyolap', 'tinyolap.storage'],
    project_urls={
        'Homepage': 'https://tinyolap.com',
        'Documentation': 'https://tinyolap.com/docs',
        'GitHub': 'https://github.com/Zeutschler/tinyolap',
    },
)