from setuptools import setup
import os
import sys

_here = os.path.abspath(os.path.dirname(__file__))

if sys.version_info[0] < 3:
    with open(os.path.join(_here, 'readme.md')) as f:
        long_description = f.read()
else:
    with open(os.path.join(_here, 'readme.md'), encoding='utf-8') as f:
        long_description = f.read()

version = {}
with open(os.path.join(_here, 'paceline', 'version.py')) as f:
    exec(f.read(), version)

setup(
    name='paceline',
    version=version['__version__'],
    description=('Beautiful Python performance measurement.'),
    long_description=long_description,
    author='Thomas Zeutschler',
    author_email='',
    url='https://github.com/Zeutschler/paceline',
    license='MIT',
    packages=['paceline'],
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX'
        ]
    )