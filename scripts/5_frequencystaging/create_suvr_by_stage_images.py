import os

from atstaging.config import get, set_config
from atstaging.outputs import load_split, load_paths_tables

import numpy as np
import nibabel as nib

set_config('main')

# Paths
preproc_folder = '/ceph/chpc/shared/aristeidis_sotiras_group/tom_pet_processing/'

# load data
master = load_split(None, None, verbose=False)
paths = load_paths_tables(output_directory=preproc_folder)
joiner = paths[['Subject', 'Session', 'amyloid_registered', 'tau_registered']]

df = master[['Subject', 'Session', 'StageLabeled', 'Split', 'ControlForStaging']].merge(joiner, on=['Subject', 'Session'], how='left')
df['Stage'] = df['StageLabeled'].replace(['A0T+', 'A1T+', 'NS'], 'Atypical')

training = df[df['ControlForStaging'].eq(False) & df['Split'].eq('TrainingBaseline')]
validation = df[df['ControlForStaging'].eq(False) & df['Split'].eq('ValidationBaseline')]

# Setup output
root_output = get('output_directory')
odir = os.path.join(root_output, 'images', 'suvr_by_stage')
os.makedirs(odir, exist_ok=True)

# get MNI shape
mni_path = get('mni152_brain')
mni = nib.load(mni_path)
mni_shape = mni.shape
mni_affine = mni.affine

# main
cohorts = {'training': training, 'validation':validation}
stages = set(training['Stage'].unique()) | set(validation['Stage'].unique())

def create_average_image(paths, shape, affine, outpath):

    arr = np.zeros(shape)
    n = len(paths)
    
    for i, path in enumerate(paths):
        print(f'  - [{i+1}/{n}] {path}')
        nii = nib.load(path)
        data = nii.get_fdata()
        arr += data

    arr /= n
    out_nii = nib.Nifti1Image(arr, affine=affine)

    nib.save(out_nii, outpath)

for key, data in cohorts.items():
    for stage in stages:
        amy_images = data.loc[data['Stage'].eq(stage), 'amyloid_registered']
        tau_images = data.loc[data['Stage'].eq(stage), 'tau_registered']
        n = len(amy_images)
        opath_amy = os.path.join(odir, f'{key}_{stage}_n{n}_amyloid.nii.gz')
        opath_tau = os.path.join(odir, f'{key}_{stage}_n{n}_tau.nii.gz')
        print()
        print(f'> COHORT={key}, STAGE={stage}, N={n}')

        # amyloid
        if os.path.isfile(opath_amy):
            print(f'  - Existing image at {opath_amy}; skipping')
        else:
            print(f'  - Creating average image. [{opath_amy}]')
            create_average_image(amy_images, shape=mni_shape, affine=mni_affine, outpath=opath_amy)

        # tau
        if os.path.isfile(opath_tau):
            print(f'  - Existing image at {opath_tau}; skipping')
        else:
            print(f'  - Creating average image. [{opath_tau}]')
            create_average_image(tau_images, shape=mni_shape, affine=mni_affine, outpath=opath_tau)
        