"""Code for generating starting tables for the OASIS3 dataset.

NOTE: You should run `oasis_pull_frames.py` prior to this.

Takes the following as inputs:

    - AMY_CONVERSION_CSV: CSV output by `oasis_pull_frames.py` containing paths to OASIS3 amyloid-PET images with frames of interest already selected.
    - TAU_CONVERSION_CSV: CSV output by `oasis_pull_frames.py` containing paths to OASIS3 tau-PET images with frames of interest already selected.
    - MRI_CONVERSION_CSV: CSV output by `oasis_pull_frames.py` containing paths to OASIS3 T1 images.
    - OASIS_DEMOGRAPHICS: path to the OASIS3 demographics CSV
    - OASIS3_CDR: path to the OASIS3 CDR CSV
    - OASIS3_CENTILOID: path to the OASIS3 Centiloid CSV
    - BASEDATE: date to use for converting OASIS3 days-since-baseline to dates.  This shouldn't need to be changed, and shouldn't bear on the analysis."""

import os
import pandas as pd

from atstaging.config import get,set_config
from atstaging.dataorg.oasis import create_feature_table, create_preproc_table
from atstaging.outputs import setup_outputs_folder

AMY_CONVERSION_CSV = '/scratch/tom.earnest/atstaging/downloadLists/oasis3_amyloid_conversion.csv'
TAU_CONVERSION_CSV = '/scratch/tom.earnest/atstaging/downloadLists/oasis3_tau_conversion.csv'
MRI_CONVERSION_CSV = '/scratch/tom.earnest/atstaging/downloadLists/oasis3_mri_conversion.csv'
OASIS3_DEMOGRAPHICS = '/ceph/chpc/rcif_datasets/oasis/OASIS3/OASIS3_data_files/SCANS/demo/csv/OASIS3_demographics.csv'
OASIS3_CDR = '/ceph/chpc/rcif_datasets/oasis/OASIS3/OASIS3_data_files/SCANS/UDSb4/csv/OASIS3_UDSb4_cdr.csv'
OASIS3_CENTILOID = '/ceph/chpc/rcif_datasets/oasis/OASIS3/OASIS3_data_files/SCANS/Centiloid/csv/OASIS3_amyloid_centiloid.csv'
BASEDATE = pd.Timestamp(year=2001, month=1, day=1)

# SETUP
set_config('main')
OUTPUT_FOLDER = get('output_directory')
setup_outputs_folder(OUTPUT_FOLDER)

# MAIN
preproc_table = create_preproc_table(AMY_CONVERSION_CSV, TAU_CONVERSION_CSV, MRI_CONVERSION_CSV, basedate=BASEDATE)
features = create_feature_table(
    preproc_table=preproc_table,
    oasis3_demographics=OASIS3_DEMOGRAPHICS,
    oasis3_cdr=OASIS3_CDR,
    oasis3_centiloid=OASIS3_CENTILOID,
    basedate=BASEDATE)
features.insert(0, 'DataSet', 'OASIS')
features.to_csv(os.path.join(OUTPUT_FOLDER, 'datasetTables', 'oasis.csv'), index=False)