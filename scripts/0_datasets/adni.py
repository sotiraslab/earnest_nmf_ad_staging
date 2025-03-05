#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prep the ADNI dataset for preprocessing.  Requires the following inputs:

    - SELECTED_AMYLOID_SEARCH / SELECTED_TAU_SEARCH / SELECTED_T1_SEARCH: CSVs containing the LONI search results (not collection CSV)
    for the amyloid, tau, and T1 searches generated with the `adni_images_to_download.py` script.  You can generate these by doing the following:
        - For each of the text files outputing the Image IDs, plug these into the "Image ID" field in the advanced search, with each as a separate search
        - On the ADNI LONI search, make sure to include "Study Date", "Image ID", and Original/Pre-processed
        - For PET, make sure to check to include the radiopharmaceutical
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

from atstaging.dataorg.adni import create_subject_table, create_preproc_table, create_feature_table
from atstaging.dataorg.utils import load_loni_downloads_with_caching
from atstaging.config import get, set_config
from atstaging.outputs import setup_outputs_folder

# INPUTS (see docstring above)
SELECTED_AMYLOID_SEARCH = '/scratch/tom.earnest/atstaging/searches/adni_selected_amyloid_search.csv'
SELECTED_TAU_SEARCH = '/scratch/tom.earnest/atstaging/searches/adni_selected_tau_search.csv'
SELECTED_T1_SEARCH = '/scratch/tom.earnest/atstaging/searches/adni_selected_t1_search.csv'
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
subject_table = create_subject_table(
    selected_amyloid_search=SELECTED_AMYLOID_SEARCH,
    selected_tau_search=SELECTED_TAU_SEARCH,
    selected_t1_search=SELECTED_T1_SEARCH)
preproc_table = create_preproc_table(subject_table=subject_table, download_table=downloads)
preproc_table.insert(0, 'DataSet', 'ADNI')
features = create_feature_table(preproc_table, tabular_folder=TABULAR_FOLDER)

# save
features.to_csv(os.path.join(OUTPUT_FOLDER, 'datasetTables', 'adni.csv'), index=False)