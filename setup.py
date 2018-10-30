#!/usr/bin/env python
# coding: utf-8

import os, sys
from setuptools import setup, find_packages


HERE = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(HERE, 'README.md')) as fd:
    md = fd.read()

with open(os.path.join(HERE, 'src/devapps/version.py')) as fd:
    version = fd.read().split('=', 1)[1].split('\n', 1)[0]

# images hack for pypi - uncomment, replace:
# gh = 'https://raw.githubusercontent.com/axiros/terminal_markdown_viewer/master'
# md = md.replace('src="./', 'src="%s/' % gh)

PY2 = sys.version_info[0] < 3
INST_REQ = ['attrs', 'structlog', 'appdirs', 'colorama']
if PY2:
    INST_REQ.append('funcsigs')

EXTRA_REQ = {'tests': ['coverage', 'pytest_to_md', 'pytest>=3.3.0']}
try:
    PACKAGES
except NameError:
    PACKAGES = find_packages(where='src')


setup(
    name='devapps',
    version=version,
    packages=PACKAGES,
    package_dir={'': 'src'},
    author='Axiros GmbH',
    author_email='gk@axiros.com',
    description='Application Config',
    install_requires=INST_REQ,
    extras_require=EXTRA_REQ,
    long_description=md,
    long_description_content_type='text/markdown',
    include_package_data=True,
    url='http://github.com/axiros/DevApps',
    # download_url='http://github.com/axiros/DevApps/tarball/',
    keywords=['app', 'config', 'source code'],
    test_suite='nose.collector',
    tests_require=['nose', 'unittest2', 'coveralls'],
    classifiers=[
        'Programming Language :: Python',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Topic :: Software Development :: Pre-processors',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Code Generators',
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    entry_points={'console_scripts': ['devapp = devapps.app:run']},
    zip_safe=False,
)
