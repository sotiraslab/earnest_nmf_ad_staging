#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prep the SCAN dataset for preprocessing.  Requires the following inputs:

    - TAU_SEARCH: path to the CSV record of the LONI collection containing tau images
    - AMY_SEARCH: path to the CSV record of the LONI collection containing amyloid images
    - T1_SEARCH: path to the CSV record of the LONI collection containing T1w images
    - DOWNLOAD_FOLDER: path to images download folder from SCAN
    - OUTPUT_FOLDER: directory to output derivative files

"""

import os

from atstaging.dataorg.utils import list_loni_images
from atstaging.dataorg.scan import create_subject_table, create_preproc_table
from atstaging.config import get

# INPUTS (see docstring above)
TAU_SEARCH = '/scratch/tom.earnest/atstaging/searches/scan_tau_092424_10_07_2024.csv'
AMY_SEARCH = '/scratch/tom.earnest/atstaging/searches/scan_amy_092424_10_07_2024.csv'
T1_SEARCH = '/scratch/tom.earnest/atstaging/searches/scan_t1_092424_10_07_2024.csv'
DOWNLAD_FOLDER = '/scratch/tom.earnest/SCAN/images/rawdata'
OUTPUT_FOLDER = get('output_directory')

# MAIN

# preprocessing table
downloads = list_loni_images(DOWNLAD_FOLDER)
subject_table = create_subject_table(AMY_SEARCH, TAU_SEARCH, T1_SEARCH)
preproc_table = create_preproc_table(subject_table, downloads)
preproc_table.to_csv(os.path.join(OUTPUT_FOLDER, 'scan_preproc_table.csv'), index=False)

