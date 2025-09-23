
import os

import nibabel as nib
import numpy as np
import pandas as pd

from atstaging.config import get, set_config

set_config('main')

root_output = get('output_directory')
indir = os.path.join(root_output, 'plots', 'sustain', 'atrophy', 'tmaps')
odir = os.path.join(root_output, 'plots', 'sustain', 'atrophy', 'niftis')
os.makedirs(odir, exist_ok=True)

wta_path = os.path.join(root_output, 'muse', 'training_control_n493_wta.nii.gz')

infiles = [f for f in os.listdir(indir) if f.endswith('csv')]

for file in infiles:
    fullfile = os.path.join(indir, file)
    df = pd.read_csv(fullfile)
    wta = nib.load(wta_path )

    wta_data = wta.get_fdata()
    painted = np.zeros(wta.shape)

    print()
    print(f'> Creating NIFTI image for "{file}"...')

    for roi, value in zip(df['ROI'], df['TVal']):
        value = 0 if np.isnan(value) else value
        painted = np.where(wta_data == roi, value, painted)

    nii = nib.Nifti1Image(dataobj=painted, affine=wta.affine)
    stub = os.path.splitext(file)[0]
    output = os.path.join(odir, f'{stub}.nii.gz')
    nib.save(nii, output)

    print(f'> Done. [{output}]')
