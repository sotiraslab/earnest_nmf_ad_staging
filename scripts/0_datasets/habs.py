#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prep the HABS dataset for preprocessing.  Requires the following inputs:

    - TAU_DOWNLOADS: path to the folder containing FTP images
    - AMY_DOWNLOADS: path to the folder containing PIB images (non-dynamic)
    - T1_DOWNLOADS: path to the folder containing T1 images
    - OUTPUT_FOLDER: directory to output derivative files

"""

import os

from atstaging.dataorg.habs import create_preproc_table, create_feature_table
from atstaging.config import get
from atstaging.outputs import setup_outputs_folder

# INPUTS (see docstring above)
TAU_DOWNLOADS = '/scratch/tom.earnest/HABS/images/ftp/'
AMY_DOWNLOADS = '/scratch/tom.earnest/HABS/images/pib/'
T1_DOWNLOADS = '/scratch/tom.earnest/HABS/images/mprage/'
TABULAR_DIRECTORY = '/scratch/tom.earnest/HABS/tabular/'
OUTPUT_FOLDER = get('output_directory')

setup_outputs_folder(OUTPUT_FOLDER)

preproc_table = create_preproc_table(TAU_DOWNLOADS, AMY_DOWNLOADS, T1_DOWNLOADS)
preproc_table.insert(0, 'DataSet', 'HABS')
features = create_feature_table(preproc_table, habs_tabular_directory=TABULAR_DIRECTORY)
features.to_csv(os.path.join(OUTPUT_FOLDER, 'datasetTables', 'habs.csv'), index=False)