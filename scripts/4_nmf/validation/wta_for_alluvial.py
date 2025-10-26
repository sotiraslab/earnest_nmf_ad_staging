#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 25 12:43:39 2025

@author: earnestt1234
"""

import os

import pandas as pd
import numpy as np

from atstaging.config import get, set_config
from atstaging.nmf.utils import load_results

set_config('main')
root_output = get('output_directory')

# Set paths to NMF solutions
path_training_amyloid = os.path.join(root_output, 'images', 'amyloid_components', 'rank11', 'ResultsExtractBases.mat')
path_validation_amyloid = os.path.join(root_output, 'images', 'validationAll_amyloid_components', 'rank11', 'ResultsExtractBases.mat')

path_training_tau = os.path.join(root_output, 'images', 'tau_components', 'rank12', 'ResultsExtractBases.mat')
path_validation_tau = os.path.join(root_output, 'images', 'validationAll_tau_components', 'rank12', 'ResultsExtractBases.mat')

# This is basically the same WTA method used in atstaging.plotting.paint_winner_take_all
def winner_take_all(path, threshold=0.5, subset=None, reset_indices=False):

    W, _ = load_results(path)
    if subset is None:
        subset = range(W.shape[1])
    W = W[:, subset]

    m, k = W.shape
    extents = W.max(axis=0) - W.min(axis=0)
    cutoffs = (extents * threshold) + W.min(axis=0)
    W_thresholded = np.where(W > cutoffs.reshape([1, k]), W, 0)

    W_unit = W_thresholded / np.sqrt(np.sum(W_thresholded  ** 2, axis=0))
    wta1D = W_unit.argmax(axis=1).astype('single')
    zero_mask = np.all(W_thresholded == 0, axis=1)
    wta1D = np.where(zero_mask, 0., wta1D+1)

    return wta1D

# Indices of the components to kepe
amy_training_wta = winner_take_all(path_training_amyloid, subset=[1, 2, 5, 6])
amy_validation_wta = winner_take_all(path_validation_amyloid, subset=[1, 4, 5])

tau_training_wta = winner_take_all(path_training_tau, subset=[1, 3, 4, 6, 9, 10, 11])
tau_validation_wta = winner_take_all(path_validation_tau, subset=[0, 4, 5, 6, 8, 10])

amy = pd.DataFrame(
    {'voxel': range(len(amy_training_wta)),
     'training': amy_training_wta,
     'validation': amy_validation_wta
     }
    )

tau = pd.DataFrame(
    {'voxel': range(len(tau_training_wta)),
     'training': tau_training_wta,
     'validation': tau_validation_wta
     }
    )

odir = os.path.join(root_output, 'plots', 'validation_nmf_similarity')
os.makedirs(odir, exist_ok=True)
amy.to_csv(os.path.join(odir, 'amyloid_wta_for_alluvial_data.csv'), index=False)
tau.to_csv(os.path.join(odir, 'tau_wta_for_alluvial_data.csv'), index=False)
