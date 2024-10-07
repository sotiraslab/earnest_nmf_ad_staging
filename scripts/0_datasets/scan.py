#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prep the SCAN dataset for preprocessing.  Requires the following inputs:

    - TAU_SEARCH: path to the CSV record of the LONI collection containing tau images
    - AMY_SEARCH: path to the CSV record of the LONI collection containing amyloid images
    - T1_SEARCH: path to the CSV record of the LONI collection containing T1w images
    - DOWNLOAD_FOLDER: path to images download folder from SCAN
    - USE CACHED: uses the saved download list, if found
    - OUTPUT_FOLDER: directory to output derivative files

"""

import os

from atstaging.dataorg.utils import load_loni_downloads_with_caching
from atstaging.dataorg.scan import create_subject_table, create_preproc_table
from atstaging.config import get
from atstaging.outputs import setup_outputs_folder

# INPUTS (see docstring above)
TAU_SEARCH = '/scratch/tom.earnest/atstaging/searches/scan_tau_092424_10_07_2024.csv'
AMY_SEARCH = '/scratch/tom.earnest/atstaging/searches/scan_amy_092424_10_07_2024.csv'
T1_SEARCH = '/scratch/tom.earnest/atstaging/searches/scan_t1_092424_10_07_2024.csv'
DOWNLAD_FOLDER = '/scratch/tom.earnest/SCAN/images/rawdata'
USE_CACHED = True
OUTPUT_FOLDER = get('output_directory')

# MAIN
setup_outputs_folder(OUTPUT_FOLDER)
cachedir = os.path.join(OUTPUT_FOLDER, 'downloadlists')

# preprocessing table
downloads = load_loni_downloads_with_caching('scan', cachedir=cachedir, download_folder=DOWNLAD_FOLDER, use_cached=USE_CACHED)
subject_table = create_subject_table(AMY_SEARCH, TAU_SEARCH, T1_SEARCH)
preproc_table = create_preproc_table(subject_table, downloads)
preproc_table.to_csv(os.path.join(OUTPUT_FOLDER, 'preproc_tables', 'scan_preproc_table.csv'), index=False)

