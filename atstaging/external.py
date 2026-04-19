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

PACS = [
    'PACParietal',
    'PACFrontal',
    'PACSensorimotor',
    'PACOccipital'
        ]

PTCS = [
    'PTCMedialTemporal',
    'PTCRightParietalTemporal',
    'PTCLeftParietalTemporal',
    'PTCOccipital',
    'PTCFrontal',
    'PTCSensorimotor',
    'PTCInsularMedialFrontal'
        ]

# Path to WScore parameters
WPARAMS_TRAIN = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'wscore_parameters', 'training')
WPARAMS_VALA = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'wscore_parameters', 'validationA')
WPARAMS_VALB = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'wscore_parameters', 'validationB')
WPARAMS_VALC = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'wscore_parameters', 'validationC')

WPARAMS_DICT = {
    'training': WPARAMS_TRAIN,
    'validationA': WPARAMS_VALA,
    'validationB': WPARAMS_VALB,
    'validationC': WPARAMS_VALC,
    }

def apply_wscore_model(df, model='training', pacs=True, ptcs=True):

    n = len(df)
    parameters_order = ['Intercept', 'Age', 'SexMale']

    if model not in ['training', 'validationA', 'validationB', 'validationC']:
        raise ValueError('`model` must be "training", "validationA", "validationB", or "validationC".')

    if pacs == False and ptcs == False:
        raise ValueError("Either `pacs` or `ptcs` must be set to True")

    factors = []
    if pacs:
        factors += PACS
    if ptcs:
        factors += PTCS

    wscores = np.zeros((n, len(factors)))

    for i, factor in enumerate(factors):

        # Value observed in the new data
        observed_uptake = df[factor].to_numpy()
        observed_predictors = np.zeros((n, 3))
        observed_predictors[:, 0] = 1. # Intercept
        observed_predictors[:, 1] = df['Age'].to_numpy()
        observed_predictors[:, 2] = df['SexMale'].to_numpy()

        # Extract model parameters
        csv_name = f'{factor}SUVR.csv'
        params_folder = WPARAMS_DICT[model]
        csv_path = os.path.join(params_folder, csv_name)
        parameters = pd.read_csv(csv_path)
        parameters_array = parameters[parameters_order].to_numpy()
        w_residual = parameters['Residual'].to_numpy()

        # Apply model
        linear_predictions = np.matmul(observed_predictors, parameters_array.T) # (n x 3) * (3 x 200)
        prediction_residuals = observed_uptake[:, np.newaxis] - linear_predictions
        scaled_residuals = prediction_residuals / w_residual[np.newaxis, :]
        w = scaled_residuals.mean(axis=1)

        wscores[:, i] = w

    wdf = pd.DataFrame(wscores)
    wdf.columns = factors

    return wdf

def _assign_frequency_stage(data, groupings=None, p='any', atypical='NS'):

    if groupings == None:
        groupings = list(range(data.shape[1]))

    unique_stages = sorted(list(set(groupings)))
    n = len(unique_stages)
    stage_mat = np.zeros((len(data), n))

    for i in unique_stages:
        regions_in_stage = (np.array(groupings) == i)
        n_regions_in_stage = regions_in_stage.sum()
        sub = data[:, regions_in_stage]
        freqs = sub.sum(axis=1) / n_regions_in_stage

        if p == 'any':
            positive = freqs > 0
        elif p == 'all':
            positive = freqs == 1
        else:
            positive = freqs >= p

        stage_mat[:, i] = positive

    diffs = np.diff(stage_mat, axis=1)
    if n == 2:
        increasing = diffs <= 0
    else:
        increasing = np.all(diffs <= 0, axis=1)
    stage = np.where(increasing, stage_mat.sum(axis=1).astype(int), atypical)

    cats = [str(i) for i in range(0, len(unique_stages) + 1)] + [str(atypical)]
    return pd.Categorical(stage, categories=cats)

def apply_atstaging(factor_positivity_df):

    factor_order = PACS + PTCS
    groupings = [0, 0, 1, 1, 2, 3, 3, 4, 5, 5, 5]
    ordered_data = factor_positivity_df[factor_order].to_numpy()
    stages = _assign_frequency_stage(
        data=ordered_data,
        groupings=groupings,
        p='any',
        atypical='NS'
        )

    # formatting
    stages = pd.Series(stages.astype(str), index=factor_positivity_df.index)
    stages = stages.map(
        {
            '0': 'A0T0',
            '1': 'A1T0',
            '2': 'A2T0',
            '3': 'A2T1',
            '4': 'A2T2',
            '5': 'A2T3',
            '6': 'A2T4',
            'NS': 'NS'
            }
        )

    return stages

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
