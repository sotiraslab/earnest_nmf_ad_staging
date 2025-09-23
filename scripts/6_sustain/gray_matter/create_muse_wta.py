import os

from atstaging.config import get, set_config
from atstaging.outputs import load_subtyped_data
from atstaging.preprocessing.bids import ATPreprocMRINamer

import nibabel as nib
import numpy as np
from scipy.stats import mode

set_config('main')

preproc_dir = '/ceph/chpc/shared/aristeidis_sotiras_group/tom_pet_processing/'

# Load the training-control subjects, n=493
df = load_subtyped_data('training', load_controls=True)[['Subject', 'Session', 'DataSet']]
df['Path'] = [ATPreprocMRINamer(subject=sub, session=ses, modality='anat', directory=os.path.join(preproc_dir, 'preprocessing', 'images', dataset)).get_path('muse-registered')
              for sub, ses, dataset in zip(df['Subject'], df['Session'], df['DataSet'])]

# Actually load the images
# this needs to be done with a fair amount of memory
mni_path = get('mni152_brain')
mni = nib.load(mni_path)
mni_affine = mni.affine
mni_shape = mni.shape

n = len(df)
m = int(np.prod(mni_shape))

data = np.zeros((n, m), dtype='half')

for i, path in enumerate(df['Path'].values):

    # Try/except was implemented to catch one failed load at runtime
    try:
        nii = nib.load(path)
        data[i, :] = nii.get_fdata().flatten()
    except:
        print(f'Error for {i}: {path}')
        pass

    if i % 10 == 0:
        print(f'[{i+1} / {n}]')

# calculate the mode across subjects for each voxel
res = mode(data, axis=0)

# save
output = nib.Nifti1Image(dataobj=res.mode.reshape(mni_shape), affine=mni_affine)
outpath = os.path.join(get('output_directory'), 'muse', f'training_control_n{n}_wta.nii.gz')
nib.save(output, outpath)