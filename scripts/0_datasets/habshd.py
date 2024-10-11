#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prep the HABS-HD (not HABS!) dataset for preprocessing.  Requires the following inputs:

    - TAU_SEARCH: path to the CSV record of the LONI collection containing tau images
    - AMY_SEARCH: path to the CSV record of the LONI collection containing amyloid images
    - T1_SEARCH: path to the CSV record of the LONI collection containing T1w images
    - DOWNLOAD_FOLDER: path to images download folder from HABS-HD
    - USE CACHED: uses the saved download list, if found
    - TABULAR_FOLDER: path to the folder containing HABS-HD tabular data
    - OUTPUT_FOLDER: directory to output derivative files
"""

import os

import pandas as pd

from atstaging.dataorg.habshd import create_subject_table, create_feature_table
from atstaging.dataorg.utils import load_csv_by_match
from atstaging.config import get
from atstaging.outputs import setup_outputs_folder

# INPUTS (see docstring above)
TAU_SEARCH = '/scratch/tom.earnest/atstaging/searches/habshd_tau_10102024_10_10_2024.csv'
AMY_SEARCH = '/scratch/tom.earnest/atstaging/searches/habshd_amy_10102024_10_10_2024.csv'
T1_SEARCH = '/scratch/tom.earnest/atstaging/searches/habshd_t1_10102024_10_10_2024.csv'
DOWNLAD_FOLDER = 'TBA'
TABULAR_FOLDER = '/scratch/tom.earnest/HABS-HD/tabular/'
USE_CACHED = True
OUTPUT_FOLDER = get('output_directory')

# load HABS-HD subject tables
tables = [
    'HD_1_African',
    'HD_1_Mexican',
    'HD_1_Non',
    'HD_2_Mexican',
    'HD_2_Non',
    'HD_3_Mexican',
    'HD_3_Non']
habshd = pd.concat([load_csv_by_match(TABULAR_FOLDER, t) for t in tables])

# MAIN
setup_outputs_folder(OUTPUT_FOLDER)
cachedir = os.path.join(OUTPUT_FOLDER, 'downloadLists')
subject_table = create_subject_table(AMY_SEARCH, TAU_SEARCH, T1_SEARCH)

# TODO: add download paths
preproc_table = subject_table.copy()
preproc_table.insert(0, 'DataSet', 'HABS-HD')
# ^^^^^^

features = create_feature_table(preproc_table=preproc_table, habshd_uds=habshd, verbose=True)

# save
features.to_csv(os.path.join(OUTPUT_FOLDER, 'datasetTables', 'habshd.csv'), index=False)