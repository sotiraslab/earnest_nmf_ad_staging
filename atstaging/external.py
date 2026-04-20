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

# Define the names of the PACs/PTCs
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
    '''
    Generate W-scores for data that have been projected onto PACs and/or
    PTCs.

    The input data must include columns with the explicit names of PACs
    and/or PTCs - see `atstaging.external.PACS` and `atstaging.external.PTCS`.
    See the `pacs` and `ptcs` arguments for specifying whether to do
    amyloid or tau W-scoring.

    Parameters
    ----------
    df : pandas.core.frame.DataFrame
        DataFrame containing the data to be W-scored.
    model : str, optional
        W-scoring model to use. The default is 'training', which is the
        model learned from training data with FBP/FTP.  Other options
        are models learned in validation data: "validationA" (PIB/FTP),
        "validationB" (FBB/P26), or "validationC" (FBB/FTP).
    pacs : bool, optional
        Generate W-scores for amyloid (PACs). The default is True.
    ptcs : bool, optional
        Generate W-scores for tau (PTCs) The default is True.

    Raises
    ------
    ValueError
        Provided value for `model` not recognized.
        Neither `pacs=True` nor `ptcs=True`.

    Returns
    -------
    wdf : pandas.core.frame.DataFrame
        DataFrame containing W-scores.

    '''
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
    '''
    Helper function for converting binary positivity measures into stages.

    Parameters
    ----------
    data : numpy.ndarray
        Array of shape (n, m), containing binary indicators of pathology
        (1=above threshold, 0=below threshold) across *m* regions for *n* subjects.
    groupings : list, optional
        List assigning which regions are part of the same disease stage.
        Length should be equal to *m*, the number of regions (columns)
        in the input `data`.  Use ascending integers to group regions into
        stages.  E.g., for 6 regions, you could provide `[0, 0, 1, 2, 2, 2]`,
        or `[0, 0, 0, 1, 0, 0]`.  The default is None, in which case it is
        assumed each region is a unique stage.
    p : str or int, optional
        Proprtion of regions part of a stage needed to meet positivty criteria for
        the stage.  Two string values can be provided: 'any' (Default: positivity
        in any region indicates stage positivity) or 'all' (positivity for a stage
        requires positivity for all contained regions).  Otherwise, a float between
        0 and 1 can be provided, indicating the proportion of regions for which
        regional positivity indicates stage positivity.
    atypical : str, optional
        String to use when labeling cases which do not meet stageable critera.
        The default is 'NS'.

    Returns
    -------
    pandas.Categorical
        Series indicating the stage assignment for each subject.

    '''

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
    '''
    Determine amyloid-tau stages for a dataset.  

    Parameters
    ----------
    factor_positivity_df : pandas.core.frame.DataFrame
        DataFrame containing positivity (0=below threshold, 1=above threshold)
        measures for PACs and PTCs.  The DataFrame should at least contain 11
        columns containing the determination of positivity/negativity in each
        PAC (4 columns) and PTC (7 columns).  See `atstaging.external.PACS`
        and `atstaging.external.PTCS` for how these should be named.

    Returns
    -------
    stages : pandas.Series
        Pandas Series containing string data and stage assignments.  Possible 
        values are A0T0 (no pathology), A1T0, A2T0, A2T1, A2T2, A2T3, A2T4,
        and NS (non-stageable).

    '''

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
    '''
    Project new data onto NMF factor.  Basically a weighted
    avearge of image voxels, with weights determined by voxel
    intensities in each NMF factor.
    
    Input images must be in 1mm MNI space (182, 218, 182).

    Parameters
    ----------
    images : str or iterable
        Paths to images to generate NMF projections for.  Can be a single
        image (str) or a collection of multiple (iterable).
    nmf_factors_directory : str
        Path to the directory containing compressed NIFTI images for 
        PACs & PTCs.  See https://github.com/sotiraslab/earnest_nmf_ad_staging/tree/main/nmf_factors.
    pathology : str
        Either "amyloid" for the projection onto PACs or "tau" for the projection onto PTCs.
    normalize : bool, optional
        Normalize components to sum to 1. The default is True.  When True,
        the projection value will result in values in the original units of the image.
        E.g., if inputting an SUVR map, SUVR values will be output.  With `normalize=False`,
        the output values are loadings (in NMF terms, elements of the H matrix) which,
        when matrix multipled with factors (W matrix) generate the individual image reconstruction.
    only_gm : bool, optional
        Only generate the projection for the cortical gray matter factors, namely the
        PACs and PTCs. The default is True.  When `only_gm=False`, the additional 
        7 amyloid and 5 tau factors will be loaded and used for projecting the data.
        These extra factors are mostly white matter, subcortical areas, and reference regions.
    verbose : bool, optional
        Print progress while running. The default is True.

    Raises
    ------
    ValueError
        Value for `pathology` is not "amyloid" or "tau".

    Returns
    -------
    df : pandas.core.frame.DataFrame
        DataFrame containing the requested NMF projection value for every image provided.

    '''

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
    '''Load the NMF factors (stored as images) into a numpy array
    which can be used for matrix multiplication.'''
    
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
