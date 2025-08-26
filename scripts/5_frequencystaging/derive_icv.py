import os 

import nibabel as nib
import pandas as pd

from atstaging.config import get, set_config
from atstaging.outputs import load_split, load_paths_tables

set_config('main')

preproc_directory = '/ceph/chpc/shared/aristeidis_sotiras_group/tom_pet_processing/'

master = load_split(None, None, verbose=False)
paths = load_paths_tables(output_directory=preproc_directory)

merge = master[['Subject', 'Session']].merge(paths[['Subject', 'Session', 't1_brainmask']], on=['Subject', 'Session'], how='left')

rows = []
for i, index in enumerate(merge.index):
    sub = merge.loc[index, 'Subject']
    ses = merge.loc[index, 'Session']
    path = merge.loc[index, 't1_brainmask']

    nii = nib.load(path)
    x, y, z = nii.header.get_zooms()
    voxvol = x * y * z
    count_pos = (nii.get_fdata() == 1).sum()
    icv = count_pos * voxvol

    print(f'[{i+1}/{len(merge)}] SUBJECT={sub}, SESSION={ses} >>>>> ICV={round(icv, 2)}, dims={(x, y, z)}')

    rows.append({'Subject': sub, 'Session': ses, 'Path': path, 'ICV': icv, 'Xlen': x, 'Ylen': y, 'Zlen': z})

root_output = get('output_directory')
opath = os.path.join(root_output, 'masterTables', 'FEATURE_ICV.csv')

df = pd.DataFrame(rows)
df.to_csv(opath, index=False)