import os

import nibabel as nib
import numpy as np

from atstaging.config import set_config, get

set_config('main')

# variables
registered_gmmask_dir = '/scratch/tom.earnest/atstaging/nmf/gmmask/registered_masks/'
final_mask_dir = '/scratch/tom.earnest/atstaging/nmf/gmmask/final'
thresholds = [1, .9, .85, .8, .75, .7, .65, .6, .55, .5]
mni_path = get('mni152_brain')

# create output dir
os.makedirs(final_mask_dir, exist_ok=True)

# get MNI parameters
mni = nib.load(mni_path)
mni_shape = mni.shape
mni_affine = mni.affine

# list all the registered GM Mask images to include
registered_masks = sorted([os.path.join(registered_gmmask_dir, mask) for mask in os.listdir(registered_gmmask_dir)])
n = len(registered_masks)

# create output image
image_sum = np.zeros(mni_shape)

print()
print('Starting main loop:')
for i, path in enumerate(registered_masks):
    print(f'  > [{i+1}/{n}] {path}')
    gm = nib.load(path)
    image_sum += gm.get_fdata()

image_sum /= n

# save the average image
avg_outpath = os.path.join(final_mask_dir, 'average_gm.nii.gz')
img = nib.Nifti1Image(dataobj=image_sum, affine=mni_affine)
nib.save(img, avg_outpath)
print()
print(f'Saved average image [{avg_outpath}].')

# save the thresholded images
print()
for t in thresholds:
    thresholded = np.where(image_sum >= t, 1.0, 0.0)
    # from scipy.ndimage import binary_closing
    # thresholded = binary_closing(thresholded, iterations=1).astype(float)
    nii = nib.Nifti1Image(thresholded, affine=mni_affine)
    outpath = os.path.join(final_mask_dir, f'threshold_gm_{t}.nii.gz')
    nib.save(nii, outpath)
    print(f'Saved binarized image at {t} ({thresholded.sum()} mask voxels) [{outpath}].')