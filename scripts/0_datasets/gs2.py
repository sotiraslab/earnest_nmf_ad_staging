#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prep the GS2 dataset for preprocessing.  Requires the following inputs:

    - PET_SEARCH: path to CSV containing the *search results* (not collection) for GS2 PET data (with tracer & image ID fields)
    - MRI_SEARCH: path to CSV containing the *search results* (not collection) for GS2 MRI data (with image ID fields)
    - GS2_NIFTI_CSV: path to the CSV containing the paths to GS2 images reorganized as NIFTI (see gs2_reorganize_images.py)
    - TABULAR_FOLDER: path to the folder containing GS2 tabular data
    - OUTPUT_FOLDER: directory to output derivative files
"""

import os

from atstaging.config import get, set_config
from atstaging.dataorg.gs2 import (
    create_preproc_table,
    create_feature_table
)
from atstaging.outputs import setup_outputs_folder

# INPUTS (see docstring above)
PET_SEARCH = '/scratch/tom.earnest/atstaging/searches/gs2_allpet_search.csv'
MRI_SEARCH = '/scratch/tom.earnest/atstaging/searches/gs2_allmri_search.csv'
GS2_NIFTI_CSV = '/scratch/tom.earnest/atstaging/downloadLists/gs2_nifti_images.csv'
TABULAR_FOLDER = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/GS2/tabular/raw_sdtm/csv/'

# SETUP
set_config('main')
OUTPUT_FOLDER = get('output_directory')
setup_outputs_folder(OUTPUT_FOLDER)
CACHEDIR = os.path.join(OUTPUT_FOLDER, 'downloadLists')

# MAIN
preproc_table = create_preproc_table(pet_search=PET_SEARCH, mri_search=MRI_SEARCH, gs2_reorganize_images_csv=GS2_NIFTI_CSV)
preproc_table.insert(0, 'DataSet', 'GS2')
features = create_feature_table(preproc_table, tabular_folder=TABULAR_FOLDER)

# # save
features.to_csv(os.path.join(OUTPUT_FOLDER, 'datasetTables', 'gs2.csv'), index=False)