import os

import nibabel as nib
import numpy as np

from atstaging.config import set_config, get
from atstaging.outputs import load_master_splits, load_paths_tables
from atstaging.preprocessing.execute import execute
from atstaging.preprocessing.segmentation import load_muse_roi_table_cleaned

set_config('main')

# variables
gmmask_dir = '/scratch/tom.earnest/atstaging/nmf/gmmask/'
mni152 = get('mni152_brain')

# load datasets
master = load_master_splits()
training = master.loc[master['Split'].eq('TrainingBaseline'), ['Subject', 'Session']]
paths = load_paths_tables()
paths = paths[['Subject', 'Session', 't1_muse', 't1_fullwarp']].copy()
df = training.merge(paths, on=['Subject', 'Session'], how='left')

# create output directories
indvl_mask_dir = os.path.join(gmmask_dir, 'individual_masks')
reg_mask_dir = os.path.join(gmmask_dir, 'registered_masks')
os.makedirs(indvl_mask_dir, exist_ok=True)
os.makedirs(reg_mask_dir, exist_ok=True)

# Create the individual masks
muse = load_muse_roi_table_cleaned()
muse = muse[muse['IsBrain'] & muse['TissueType'].eq('GM')]
keep_rois = list(muse['ROI'])

for i, row in enumerate(df.itertuples()):
    subject = row.Subject
    session = row.Session
    seg = row.t1_muse
    warp = row.t1_fullwarp
    print(f'[{i+1}/{len(df)}] Subject={subject}, Session={session}')

    # t1-space mask
    gm_t1space = os.path.join(indvl_mask_dir, f'sub-{subject}_ses-{session}_space-orig_desc-gmmask_mask.nii.gz')
    if os.path.isfile(gm_t1space):
        print(f"  > Existing output at {gm_t1space}; skipping.")
    else:
        image = nib.load(seg)
        data = image.get_fdata()
        masked_data = np.where(np.isin(data, keep_rois), 1.0, 0.0)
        newimage = nib.Nifti1Image(dataobj=masked_data, affine=image.affine)
        nib.save(newimage, gm_t1space)

    # mni-space mask
    gm_mnispace = os.path.join(reg_mask_dir, f'sub-{subject}_ses-{session}_space-MNI152NLin6ASym_desc-gmmask_mask.nii.gz')
    if os.path.isfile(gm_mnispace):
        print(f"  > Existing output at {gm_mnispace}; skipping.")
    else:
        command = [
            '/export/ants/ants-2.4.0/bin/antsApplyTransforms',
            '-d', '3',
            '-i', gm_t1space,
            '-r', mni152,
            '-t', warp,
            '-o', gm_mnispace,
            '-n', 'NearestNeighbor'
        ]
        execute(command)