#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prep the GS1 dataset for preprocessing.  Requires the following inputs:

    - PET_SEARCH: path to CSV containing the *search results* (not collection) for GS1 PET data (with tracer & image ID fields)
    - MRI_SEARCH: path to CSV containing the *search results* (not collection) for GS1 MRI data (with image ID fields)
    - DOWNLOAD_FOLDER: path to images download folder from GS1
    - USE CACHED: uses the saved download list, if found
    - TABULAR_FOLDER: path to the folder containing GS1 tabular
    - OUTPUT_FOLDER: directory to output derivative files
"""

import os

from atstaging.config import get, set_config
from atstaging.dataorg.gs1 import (
    create_feature_table,
    create_preproc_table,
    create_subject_table
)
from atstaging.dataorg.utils import load_loni_downloads_with_caching
from atstaging.outputs import setup_outputs_folder

# INPUTS (see docstring above)
PET_SEARCH = '/scratch/tom.earnest/atstaging/searches/gs1_allpet_search.csv'
MRI_SEARCH = '/scratch/tom.earnest/atstaging/searches/gs1_allmri_search.csv'
DOWNLAD_FOLDER = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/GS1/images/GS1/'
TABULAR_FOLDER = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/GS1/tabular/raw_sdtm/csv'
USE_CACHED = True

# SETUP
set_config('main')
OUTPUT_FOLDER = get('output_directory')
setup_outputs_folder(OUTPUT_FOLDER)
CACHEDIR = os.path.join(OUTPUT_FOLDER, 'downloadLists')

# MAIN
downloads = load_loni_downloads_with_caching('gs1', cachedir=CACHEDIR, download_folder=DOWNLAD_FOLDER, use_cached=USE_CACHED)
subject_table = create_subject_table(pet_search=PET_SEARCH, mri_search=MRI_SEARCH)
preproc_table = create_preproc_table(subject_table=subject_table, download_table=downloads)
preproc_table.insert(0, 'DataSet', 'GS1')
features = create_feature_table(preproc_table, tabular_folder=TABULAR_FOLDER)

# save
features.to_csv(os.path.join(OUTPUT_FOLDER, 'datasetTables', 'gs1.csv'), index=False)