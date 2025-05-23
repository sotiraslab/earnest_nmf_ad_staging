"""This is very similar to the code for creating an MNI space gray matter mask,
but it moves the whole segmentation."""

import os

import nibabel as nib
import numpy as np
from scipy.stats import mode

from atstaging.config import set_config, get
from atstaging.outputs import load_split, load_paths_tables
from atstaging.preprocessing.execute import execute

set_config('main')

# variables
gmmask_dir = '/scratch/tom.earnest/atstaging/nmf/gmmask/'
mni152 = get('mni152_brain')

# load datasets
training = load_split('training', 'baseline')
training = training[['Subject', 'Session']].copy()
paths = load_paths_tables()
paths = paths[['Subject', 'Session', 't1_muse', 't1_fullwarp']].copy()
df = training.merge(paths, on=['Subject', 'Session'], how='left')

# create output directories
reg_seg_dir = os.path.join(gmmask_dir, 'registered_segmentations')
avg_seg_dir = os.path.join(gmmask_dir, 'average_segmentation_MNI')
os.makedirs(reg_seg_dir, exist_ok=True)
os.makedirs(avg_seg_dir, exist_ok=True)

# Create the individual masks
for i, row in enumerate(df.itertuples()):
    subject = row.Subject
    session = row.Session
    seg = row.t1_muse
    warp = row.t1_fullwarp
    print(f'[{i+1}/{len(df)}] Subject={subject}, Session={session}')

    # mni-space segmentation
    seg_mnispace = os.path.join(reg_seg_dir, f'sub-{subject}_ses-{session}_space-MNI152NLin6ASym_desc-MUSE_seg.nii.gz')
    if os.path.isfile(seg_mnispace):
        print(f"  > Existing output at {seg_mnispace}; skipping.")
    else:
        command = [
            '/export/ants/ants-2.4.0/bin/antsApplyTransforms',
            '-d', '3',
            '-i', seg,
            '-r', mni152,
            '-t', warp,
            '-o', seg_mnispace,
            '-n', 'NearestNeighbor'
        ]
        execute(command)

# create average segementation
# NOTE: this actually doesn't complete with the full set of traiing images
# Seems to run into a memory issue - calculating mode across ~1400 observations for ~7million voxels
# Thought about alternative ways to do this, but actually seems moderately complicated
# For now, just limiting the images calculated from
_cap = 100

segs = os.listdir(reg_seg_dir)
segs = [os.path.join(reg_seg_dir, seg) for seg in segs if seg.endswith('.nii.gz')]
segs = segs[:_cap]

arr = np.zeros((len(segs), 182 * 218 * 182), dtype='single')

print()
print('Loading images to create average (winner take all)')
for i, img in enumerate(segs):
    print(f'[{i+1}/{len(df)}] Img={img}')

    nii = nib.load(img)
    flat = nii.get_fdata().flatten().astype('single')
    arr[i, :] = flat

print('> Calculating mode across images.')
wta = mode(arr, axis=0).mode
print('> Reshaping.')
wta3d = np.reshape(wta, (182, 218, 182))
print('> Constructing NIFTI.')
wta_nii = nib.Nifti1Image(wta3d, affine=nib.load(mni152).affine)

print('> Saving.')
outpath = os.path.join(avg_seg_dir, 'winner_take_all_segmentation_MNI.nii.gz')
nib.save(wta_nii, outpath)
print(f'> Done [{outpath}].')