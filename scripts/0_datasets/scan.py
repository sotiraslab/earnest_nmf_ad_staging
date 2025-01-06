#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prep the SCAN dataset for preprocessing.  Requires the following inputs:

    - PET_SEARCH: path to the CSV record of the LONI search (NOT collection) containing original PET images
    - MRI_SEARCH: path to the CSV record of the LONI search (NOT collection) containing MRI images
    - DOWNLOAD_FOLDER: path to images download folder from SCAN
    - USE CACHED: uses the saved download list, if found
    - NACC_DATASET: path to the NACC UDS dataset containing demographic/clinical/cognitive variables
    - OUTPUT_FOLDER: directory to output derivative files

"""

import os

from atstaging.dataorg.utils import load_loni_downloads_with_caching
from atstaging.dataorg.scan import create_subject_table, create_preproc_table, create_feature_table
from atstaging.config import get, set_config
from atstaging.outputs import setup_outputs_folder

import pandas as pd

# INPUTS (see docstring above)
PET_SEARCH = '/scratch/tom.earnest/atstaging/searches/scan_original_pet.csv'
MRI_SEARCH = '/scratch/tom.earnest/atstaging/searches/scan_mri.csv'
DOWNLAD_FOLDER = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/NACC_SCAN/images/SCAN'
NACC_DATASET = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/NACC_SCAN/tabular/investigator_nacc66_atsubset.csv'
USE_CACHED = True

# SETUP
set_config()
OUTPUT_FOLDER = get('output_directory')
setup_outputs_folder(OUTPUT_FOLDER)
cachedir = os.path.join(OUTPUT_FOLDER, 'downloadLists')
nacc_uds = pd.read_csv(NACC_DATASET)

# MAIN
# preprocessing table
downloads = load_loni_downloads_with_caching('scan', cachedir=cachedir, download_folder=DOWNLAD_FOLDER, use_cached=USE_CACHED)
subject_table = create_subject_table(PET_SEARCH, MRI_SEARCH)
preproc_table = create_preproc_table(subject_table, downloads)
preproc_table.insert(0, 'DataSet', 'SCAN')
feature_table = create_feature_table(preproc_table, nacc_uds=nacc_uds)

# save
feature_table.to_csv(os.path.join(OUTPUT_FOLDER, 'datasetTables', 'scan.csv'), index=False)