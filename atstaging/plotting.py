
import os

from matplotlib.colors import to_hex
import matplotlib.pyplot as plt
import nibabel as nib
from nifti_overlay import NiftiOverlay
import numpy as np
import pandas as pd

def freesurfer_cortical_colors():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'freesurfer_cortical_colors.csv')
    colors = pd.read_csv(path)
    colors = colors / 255.
    array = colors.to_numpy()
    return [to_hex(array[i, :]) for i in range(len(array))]

def make_average_pet_image(images, out_nii=None, out_figure=None, reuse=True):
    if out_nii is None and out_figure is None:
        raise ValueError('Must specify `out_nii` or `out_figure`.')

    if os.path.isfile(out_nii) and reuse:
        print()
        print(f'> Using existing image at {out_nii}')
        dataimage = nib.load(out_nii)
    else:
        n = len(images)
        example = nib.load(images[0])
        shape = example.shape
        
        dataimage = np.zeros(shape, dtype='single')
        
        print()
        print(f'Looping through {n} images: ')
        print()
        
        for i, path in enumerate(images):
        
            print(f'+ Count={i+1}, Path={path}')
            nii = nib.load(path)
            data = nii.get_fdata()
            dataimage += data
        
        dataimage /= n
        dataimage = nib.Nifti1Image(dataimage, affine=example.affine)

        if out_nii:
            nib.save(dataimage, out_nii)

    if out_figure:
        overlay = NiftiOverlay()
        overlay.add_anat(dataimage, color='nipy_spectral', vmin=0.0, vmax=2.5, drop_zero=True)
        overlay.generate(out_figure)

    return dataimage, overlay

def set_font_properties():
    plt.rcParams.update({
        'font.size': 14,
        'font.family': 'FreeSans'})
