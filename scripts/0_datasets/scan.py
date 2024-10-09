#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prep the SCAN dataset for preprocessing.  Requires the following inputs:

    - TAU_SEARCH: path to the CSV record of the LONI collection containing tau images
    - AMY_SEARCH: path to the CSV record of the LONI collection containing amyloid images
    - T1_SEARCH: path to the CSV record of the LONI collection containing T1w images
    - DOWNLOAD_FOLDER: path to images download folder from SCAN
    - USE CACHED: uses the saved download list, if found
    - NACC_DATASET: path to the NACC UDS dataset containing demographic/clinical/cognitive variables
    - OUTPUT_FOLDER: directory to output derivative files

"""

import os

from atstaging.dataorg.utils import load_loni_downloads_with_caching
from atstaging.dataorg.scan import create_subject_table, create_preproc_table, create_feature_table
from atstaging.config import get
from atstaging.outputs import setup_outputs_folder

import pandas as pd

# INPUTS (see docstring above)
TAU_SEARCH = '/scratch/tom.earnest/atstaging/searches/scan_tau_092424_10_07_2024.csv'
AMY_SEARCH = '/scratch/tom.earnest/atstaging/searches/scan_amy_092424_10_07_2024.csv'
T1_SEARCH = '/scratch/tom.earnest/atstaging/searches/scan_t1_092424_10_07_2024.csv'
DOWNLAD_FOLDER = '/scratch/tom.earnest/SCAN/images/rawdata'
NACC_DATASET = '/scratch/tom.earnest/SCAN/tabular/investigator_nacc66_atsubset.csv'
USE_CACHED = True
OUTPUT_FOLDER = get('output_directory')

# MAIN
setup_outputs_folder(OUTPUT_FOLDER)
cachedir = os.path.join(OUTPUT_FOLDER, 'downloadLists')
nacc_uds = pd.read_csv(NACC_DATASET)

# preprocessing table
downloads = load_loni_downloads_with_caching('scan', cachedir=cachedir, download_folder=DOWNLAD_FOLDER, use_cached=USE_CACHED)
subject_table = create_subject_table(AMY_SEARCH, TAU_SEARCH, T1_SEARCH)
preproc_table = create_preproc_table(subject_table, downloads)
preproc_table.insert(0, 'DataSet', 'NACC')
feature_table = create_feature_table(preproc_table, nacc_uds=nacc_uds)

# save
feature_table.to_csv(os.path.join(OUTPUT_FOLDER, 'datasetTables', 'scan.csv'), index=False)