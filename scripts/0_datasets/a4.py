# imports
import os

import pandas as pd

from atstaging.dataorg.a4 import create_preproc_table, create_feature_table
from atstaging.config import get, set_config
from atstaging.outputs import setup_outputs_folder

# variables
A4_FBP = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/A4/rawdata/FBP'
A4_FTP = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/A4/rawdata/FTP'
A4_T1 = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/A4/rawdata/T1'
A4_SUBJINFO = '/home/tom.earnest/a4_clinical/DerivedData/SUBJINFO.csv'
A4_PET_VA = '/home/tom.earnest/a4_clinical/ExternalData/imaging_PET_VA.csv'
A4_CDR = '/home/tom.earnest/a4_clinical/RawData/cdr.csv'
BASEDATE = pd.Timestamp(year=2001, month=1, day=1)

# SETUP
set_config('main')
OUTPUT_FOLDER = get('output_directory')
setup_outputs_folder(OUTPUT_FOLDER)

# MAIN
preproc = create_preproc_table(
    fbp_directory=A4_FBP,
    ftp_directory=A4_FTP,
    t1_directory=A4_T1,
    basedate=BASEDATE
)
preproc.insert(0, 'DataSet', 'A4')
features = create_feature_table(
    preproc=preproc,
    path_a4_subjinfo=A4_SUBJINFO,
    path_a4_petva=A4_PET_VA,
    path_a4_cdr=A4_CDR,
    basedate=BASEDATE
)
features.to_csv(os.path.join(OUTPUT_FOLDER, 'datasetTables', 'a4.csv'), index=False)