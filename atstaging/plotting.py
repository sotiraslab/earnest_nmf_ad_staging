
import os

import matplotlib as mpl
from matplotlib import font_manager
from matplotlib.colors import to_hex
import matplotlib.pyplot as plt
import nibabel as nib
from nifti_overlay import NiftiOverlay
import numpy as np
import pandas as pd

from atstaging.config import get
from atstaging.nmf.utils import load_results

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

def paint_winner_take_all(biomarker, assignments, threshold, use_saved=True, outpath=None,
                          return_type='nii'):

    ###### NMF SETTINGS SPECIFIC TO THE PROJECT ##############

    # These could be moved to the configuration (also elswhere in code)
    # If these settings are changed, all cached WTA images should be removed

    selected_tau_rank = 12
    selected_amyloid_rank = 11

    # Map component names to indices of the W matrix
    amy_mapping = {
        'PACParietal': 2,
        'PACFrontal': 1,
        'PACSensorimotor': 6,
        'PACOccipital': 5
        }

    tau_mapping = {
        'PTCMedialTemporal': 6,
        'PTCRightParietalTemporal': 4,
        'PTCLeftParietalTemporal': 1,
        'PTCOccipital': 3,
        'PTCFrontal': 10,
        'PTCSensorimotor': 9,
        'PTCInsularMedialFrontal': 11
        }
    ###### NMF SETTINGS SPECIFIC TO THE PROJECT ##############

    # screen arguments
    if biomarker.lower() == 'a':
        biomarker = 'amyloid'
    if biomarker.lower() == 't':
        biomarker = 'tau'
    if biomarker not in ['tau', 'amyloid']:
        raise ValueError('`biomarker` must be "tau" or "amyloid"')

    threshold = round(threshold, 2)
    if not isinstance(threshold, float) or not (0 < threshold < 1):
        raise ValueError('`threshold` must be a float between 0 and 1 (exclusive on both sides).')

    return_type = return_type.lower()
    if return_type not in ['1d', '3d', 'nii']:
        raise ValueError('`return_type` must be "1d", "3d", or "nii".')

    mapping = amy_mapping if biomarker == 'amyloid' else tau_mapping

    # set some paths
    output_directory = get('output_directory')
    amy_results_mat = os.path.join(output_directory, 'images', 'amyloid_components', f'rank{selected_amyloid_rank}', 'ResultsExtractBases.mat')
    tau_results_mat = os.path.join(output_directory, 'images', 'tau_components', f'rank{selected_tau_rank}', 'ResultsExtractBases.mat')
    save_wta_directory = os.path.join(output_directory, 'images', 'winner_take_all')

    # get the winner take all image
    cache_image_path = os.path.join(save_wta_directory, f'{biomarker}_thresh{threshold}.nii.gz')
    if use_saved and os.path.exists(cache_image_path):
        print()
        print(f'Using saved winner take all image for biomarker={biomarker} and threshold={threshold} ({cache_image_path}).')
        wta_nii = nib.load(cache_image_path)
        wta3D = wta_nii.get_fdata()
        wta1D = wta3D.flatten(order='F')
    else:
        print()
        print(f'Constructing winner take all image for biomarker={biomarker} and threshold={threshold}.')

        mat = amy_results_mat if biomarker == 'amyloid' else tau_results_mat
        comp_indices = list(mapping.values())

        W, H = load_results(mat, transpose=True)
        W = W[:, comp_indices]

        m, k = W.shape
        extents = W.max(axis=0) - W.min(axis=0)
        cutoffs = (extents * threshold) + W.min(axis=0)
        W_thresholded = np.where(W > cutoffs.reshape([1, k]), W, 0)

        W_unit = W_thresholded / np.sqrt(np.sum(W_thresholded  ** 2, axis=0))
        wta1D = W_unit.argmax(axis=1).astype('single')
        zero_mask = np.all(W_thresholded == 0, axis=1)
        wta1D = np.where(zero_mask, 0., wta1D+1)

        # save

        # load mni for affine & shape
        mni_path = get('mni152_brain')
        mni = nib.load(mni_path)
        shape = mni.shape
        affine = mni.affine

        wta_nii = nib.Nifti1Image(
            dataobj=np.reshape(wta1D, shape, order='F'),
            affine=affine)

        os.makedirs(save_wta_directory, exist_ok=True)
        nib.save(wta_nii, cache_image_path)

    # WTA image/array is loaded, but its values are ascending integers
    # Need to map them to the indices contained in the mapping dictionary
    wta1Dremap = np.copy(wta1D)
    remapper = dict(zip(np.arange(len(mapping)) + 1, list(mapping.values())))
    for k, v in remapper.items():
        wta1Dremap[wta1D == k] = v

    # Now apply the assignments
    output1D = np.zeros(shape=wta1Dremap.shape)
    for name, value in assignments.items():
        value = np.nan if value is None else value
        index = mapping[name]
        output1D[wta1Dremap == index] = value

    shape = wta_nii.shape
    affine = wta_nii.affine
    output3D = np.reshape(output1D, shape, order='F')
    output_nii = nib.Nifti1Image(dataobj=output3D, affine=affine)

    return_value = {
        '1d': output1D,
        '3d': output3D,
        'nii': output_nii
        }[return_type]

    # save if requested
    if outpath:
        nib.save(output_nii, outpath)

    return return_value

def set_font_properties():

    def _register_font(font_path):
        font_manager.fontManager.addfont(font_path)
        font_prop = font_manager.FontProperties(fname=font_path)
        font_name = font_prop.get_name()
        return font_name

    font_path = get('font_for_plots')
    font_path_bold = get('font_for_plots_bold')

    if font_path:
        font_name = _register_font(font_path)
    else:
        font_name = 'Arial'

    if font_path_bold:
        _ = _register_font(font_path_bold)

    plt.rcParams.update({
        'font.size': 14,
        'font.family': font_name
        })

def staging_colors():
    t_cmap = mpl.colormaps['YlOrRd']
    ns_cmap = mpl.colormaps['Purples']
    colors = {
        'A0T0': 'white',
        'A1T0': '#5FABF7',
        'A2T0': '#1F4AD8',
        'A2T1': t_cmap(.2),
        'A2T2': t_cmap(.4),
        'A2T3': t_cmap(.6),
        'A2T4': t_cmap(.8),
        'Atypical': '#A661C9',
        'Other': ns_cmap(0.),
        'A0T+': ns_cmap(1/3),
        'A1T+': ns_cmap(2/3),
        'MTL-': ns_cmap(1.)
        }

    colors = {k: to_hex(v) for k, v in colors.items()}

    return colors
