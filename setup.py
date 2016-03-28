#!/usr/bin/env python

import re
import ast

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# extract the version from the aeriscloud folder
_version_re = re.compile(r'__version__\s+=\s+(.*)')
with open('aeriscloud/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

setup(
    name='aeriscloud',
    version=version,
    description='AerisCloud implementation in Python',
    long_description=(open('README.rst').read() + '\n\n' +
                      open('CHANGELOG.md').read()),
    url='https://aeriscloud.github.io/',
    packages=['aeriscloud'],
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Installation/Setup',
    ],
    entry_points={
        'console_scripts': [
            'aeris = aeriscloud.cli.main:main',
            'cloud = aeriscloud.cli.main:main',
            # autocomplete
            'aeris-complete = aeriscloud.cli.complete:main'
        ]
    }
)
