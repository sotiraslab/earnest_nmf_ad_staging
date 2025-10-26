
# IMPORTS
import os

import nibabel as nib
from nifti_overlay import NiftiOverlay
import numpy as np

from atstaging.config import get, set_config

# CONFIG
set_config('main')
root_output = get('output_directory')

# INPUT DATA
amyloid_components = os.path.join(root_output, 'images', 'amyloid_components','rank11')
tau_components = os.path.join(root_output, 'images', 'tau_components','rank12')
mni = nib.load(os.path.join(root_output, 'images', 'downloaded', 'MNI152_T1_1mm_Brain_FAST_pve_1.nii.gz'))

# SET THRESHOLD FOR PLOTTING

# HELPER FUNC FOR LOADING IMAGE AND THRESHOLDING
def load_component(path, threshold=0.5):

    nii = nib.load(path)
    data = nii.get_fdata()

    mini = data.min()
    maxi = data.max()
    rng = maxi - mini
    cutoff = (rng * threshold) + mini
    newdata = np.where(data < cutoff, 0, data)

    output = nib.Nifti1Image(newdata, affine=nii.affine)

    # get slices to sample
    maxipos = data.argmax()
    x, y, z = np.unravel_index(maxipos, data.shape)
    x = x / data.shape[0]
    y = y / data.shape[1]
    z = z / data.shape[2]


    return output, x, y, z

# PLOT AMYLOID
odir = os.path.join(root_output, 'plots', 'components_nifti_overlay', 'training_amyloid')
os.makedirs(odir, exist_ok=True)

for img in os.listdir(amyloid_components):

    if not img.endswith('.nii.gz'):
        continue

    print(f'plotting amyloid {img}...')

    fullpath = os.path.join(amyloid_components, img)
    comp,x, y, z = load_component(fullpath)

    overlay = NiftiOverlay(
        nslices=1, transpose=True,
        minx=x, miny=y, minz=z, maxx=x, maxy=y, maxz=z,
        figsize=(3, 1)
        )
    overlay.add_anat(mni, color='gist_gray')
    overlay.add_anat(comp, color='jet', drop_zero=True, alpha=0.7)

    bname = img.removesuffix('.nii.gz')
    overlay.generate(os.path.join(odir, f'{bname}.png'))

# PLOT TAU
odir = os.path.join(root_output, 'plots', 'components_nifti_overlay', 'training_tau')
os.makedirs(odir, exist_ok=True)

for img in os.listdir(tau_components):

    if not img.endswith('.nii.gz'):
        continue

    print(f'plotting tau {img}...')

    fullpath = os.path.join(tau_components, img)
    comp,x, y, z = load_component(fullpath)

    overlay = NiftiOverlay(
        nslices=1, transpose=True,
        minx=x, miny=y, minz=z, maxx=x, maxy=y, maxz=z,
        figsize=(3, 1)
        )
    overlay.add_anat(mni, color='gist_gray')
    overlay.add_anat(comp, color='jet', drop_zero=True, alpha=0.7)

    bname = img.removesuffix('.nii.gz')
    overlay.generate(os.path.join(odir, f'{bname}.png'))
