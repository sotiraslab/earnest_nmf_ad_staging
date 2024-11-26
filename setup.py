#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from os import path

from setuptools import setup, find_packages

# read the contents of your README file
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# read version
with open(path.join(this_directory, 'atstaging', 'version.py'), encoding='utf-8') as f:
    version = f.read().split('=')[1].strip('\'"\n')

requirements = [
    'colorama',
    'nibabel',
    'nilearn',
    'pandas'
]

setup(name='atstaging',
      version=version,
      description="Code for Tom's NMF & SuStaIn PET staging work.",
      url='https://github.com/sotiraslab/at_nmf_sustain',
      author='Tom Earnest',
      author_email='tom.earnest@wustl.edu',
      packages=find_packages(),
      install_requires=requirements,
      include_package_data=True,
      zip_safe=False,
      long_description=long_description,
      long_description_content_type='text/markdown',
      entry_points = {
        'console_scripts': ['atproc_subject=atstaging.cli.atproc_subject:main',
                            'atproc_table=atstaging.cli.atproc_table:main',
                            'catalogue_loni=atstaging.cli.catalogue_loni:main'],
        }
      )
