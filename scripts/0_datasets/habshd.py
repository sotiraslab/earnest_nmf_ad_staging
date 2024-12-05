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

from atstaging.dataorg.habshd import create_subject_table, create_preproc_table, create_feature_table
from atstaging.dataorg.utils import load_csv_by_match, load_loni_downloads_with_caching
from atstaging.config import get
from atstaging.outputs import setup_outputs_folder

# INPUTS (see docstring above)
TAU_SEARCH = '/scratch/tom.earnest/atstaging/searches/habshd_search_pi2620_12_05_2024.csv'
AMY_SEARCH = '/scratch/tom.earnest/atstaging/searches/habshd_search_fbb_12_05_2024.csv'
T1_SEARCH = '/scratch/tom.earnest/atstaging/searches/habshd_t1_10102024_12_05_2024.csv'
DOWNLAD_FOLDER = '/scratch/tom.earnest/HABS-HD/images/HABS_HD'
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
downloads = load_loni_downloads_with_caching('habshd', cachedir=cachedir, download_folder=DOWNLAD_FOLDER, use_cached=USE_CACHED)
subject_table = create_subject_table(AMY_SEARCH, TAU_SEARCH, T1_SEARCH, tabular_folder=TABULAR_FOLDER)
preproc_table = create_preproc_table(subject_table=subject_table, download_table=downloads)
preproc_table.insert(0, 'DataSet', 'HABS-HD')
features = create_feature_table(preproc_table=preproc_table, habshd_uds=habshd, verbose=True)

# save
features.to_csv(os.path.join(OUTPUT_FOLDER, 'datasetTables', 'habshd.csv'), index=False)

# some scratch code for looking at the mapping of Clinical Visits to T1 LONI visit labels
# t1 = pd.read_csv(T1_SEARCH)
# t1 = t1[['Subject', 'Visit', 'Acq Date', 'Age']]
# t1['ClinicalVisit'] = t1['Visit'].map({'BL': 1, 'M24': 2, 'M48': 3, 'M72': 4})

# merger = habshd[['Med_ID', 'Visit_ID', 'Age']].copy()
# merger.columns = ['Subject', 'ClinicalVisit', 'AgeTable']

# merged = t1.merge(merger, how='left', on=['Subject', 'ClinicalVisit'])
# merged['Diff'] = (merged['Age'] - merged['AgeTable']).abs()
# merged.dropna().sort_values('Diff').tail(20)