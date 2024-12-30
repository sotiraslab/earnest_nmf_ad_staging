#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prep the ADNI dataset for preprocessing.  Requires the following inputs:

    - IMAGE_SEARCH: path to CSV containing the LONI collection record for all required PET & T1 images.
    This can be generated with help from /scripts/misc/adni_images_to_download.py
    - DOWNLOAD_FOLDER: path to images download folder from ADNI
    - USE CACHED: uses the saved download list, if found
    - TABULAR_FOLDER: path to the folder containing ADNI tabular data
    - OUTPUT_FOLDER: directory to output derivative files

The TABULAR_FOLDER must contain the following files, which are searched for with the text indicated in brackets:
    - UC Berkeley amyloid FreeSurfer outputs [UCBERKELEY_AMY]
    - APOE genotyping results [APOERES]
    - CDR [CDR]
    - Demographics [PTDEMOG]
    - Information on the first visit [First_Visit]
"""

import os

from atstaging.dataorg.adni import create_subject_table_from_combined_search, create_preproc_table, create_feature_table
from atstaging.dataorg.utils import load_loni_downloads_with_caching
from atstaging.config import get, set_config
from atstaging.outputs import setup_outputs_folder

# INPUTS (see docstring above)
IMAGE_SEARCH = '/scratch/tom.earnest/atstaging/searches/adni_all3_10282024_10_29_2024.csv'
DOWNLAD_FOLDER = '/ceph/chpc/shared/aristeidis_sotiras_group/tom.earnest_scratch/ADNI/images/ADNI'
TABULAR_FOLDER = '/ceph/chpc/shared/aristeidis_sotiras_group/tom.earnest_scratch/ADNI/tabular'
USE_CACHED = True

# SETUP
set_config('main')
OUTPUT_FOLDER = get('output_directory')
setup_outputs_folder(OUTPUT_FOLDER)
CACHEDIR = os.path.join(OUTPUT_FOLDER, 'downloadLists')

# # MAIN
setup_outputs_folder(OUTPUT_FOLDER)
downloads = load_loni_downloads_with_caching('adni', cachedir=CACHEDIR, download_folder=DOWNLAD_FOLDER, use_cached=USE_CACHED)
subject_table = create_subject_table_from_combined_search(IMAGE_SEARCH)
preproc_table = create_preproc_table(subject_table=subject_table, download_table=downloads)
preproc_table.insert(0, 'DataSet', 'ADNI')
features = create_feature_table(preproc_table, tabular_folder=TABULAR_FOLDER)

# save
features.to_csv(os.path.join(OUTPUT_FOLDER, 'datasetTables', 'adni.csv'), index=False)