#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code intended for others to make use of this repository.

@author: earnestt1234
"""

import os

import nibabel as nib
import numpy as np
import pandas as pd

from atstaging.nmf.utils import load_results


def load_nmf_niftis_as_matrix(directory, only_gm=True):
    files = os.listdir(directory)
    files = [file for file in files if file.endswith('.nii.gz')]
    if only_gm:
        files = [file for file in files if not 'Omit' in file]
    k= len(files)
    m = 182 * 218 * 182 # MNI 1mm shape
    W = np.zeros((m, k))

    names = []
    for i, file in enumerate(files):
        name = file.removesuffix('.nii.gz')
        fullfile = os.path.join(directory, file)
        nii = nib.load(fullfile)
        data3d = nii.get_fdata()
        data1d = data3d.flatten(order='F')
        W[:, i] = data1d
        names.append(name)

    return W, names

def compute_nmf_loadings(images, nmf_factors_directory, pathology,
                         normalize=True, only_gm=True, verbose=True):

    vprint = print if verbose else lambda *args, **kwargs: None

    # Screen the pathology argument
    if pathology not in ['amyloid', 'tau']:
        raise ValueError(f'`pathology` must be "amyloid" or "tau", not {pathology}')

    # Screen the input images
    if isinstance(images, str): # single image passed
        images = [images]

    # Load W matrix
    vprint()
    vprint(f'Loading NMF factors for {pathology} into matrix...')
    directory = os.path.join(nmf_factors_directory, pathology)
    W, names = load_nmf_niftis_as_matrix(directory, only_gm=only_gm)
    nvoxels, nfactors = W.shape
    vprint('Done.')

    if normalize:
        W /= W.sum(axis=0)

    # Generate ouptut array
    nimages = len(images)
    loadings = np.zeros((nimages, nfactors))

    vprint()
    vprint(f'> Beginning main loop to derive {pathology} loadings for {nimages} image(s).')
    vprint()

    for i, image in enumerate(images):
        vprint(f'  + [{i+1}/{nimages}] {image}')
        nii = nib.load(image)
        data3d = nii.get_fdata()
        data1d = data3d.flatten(order='F')
        vsize = len(data1d)
        projection = np.matmul(data1d.reshape((1, vsize)), W)
        loadings[i, :] = projection

    # convert to dataframe
    df = pd.DataFrame(loadings)
    df.columns = names

    return df

