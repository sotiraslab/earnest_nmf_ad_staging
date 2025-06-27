# IMPORTS
import os

import pandas as pd

from atstaging.config import get, set_config
from atstaging.nmf.utils import load_nmf_runner
from atstaging.outputs import load_paths_tables, load_split

# PARAMETERS
tau_nmf_name = 'training_tau'
tau_rank = 12
tau_component_indices = [
    1, 3, 4, 6,
    9, 10, 11
    ]
tau_component_names = [
    'LeftParietalTemporal', 'Occipital', 'RightParietalTemporal', 'MedialTemporal',
    'Sensorimotor', 'Frontal', 'InsularMedialFrontal'
    ]

amy_nmf_name = 'training_amyloid'
amy_rank = 11
amy_component_indices = [1, 2, 5, 6]
amy_component_names = ['Frontal', 'Parietal', 'Occipital', 'Sensorimotor']

# CONFIG
set_config('main')
output_directory = get('output_directory')

# LOAD NMF RUNNERS
taunmf = load_nmf_runner(os.path.join(output_directory, 'nmf', 'runs', tau_nmf_name))
amynmf = load_nmf_runner(os.path.join(output_directory, 'nmf', 'runs', amy_nmf_name))

# LOAD PATHS TO PREPROCESSED IMAGES
# filtered to be only the images in the final dataset
maindata = load_split(None, None)
paths = load_paths_tables()
paths = paths[(paths['Subject'] + paths['Session']).isin(maindata['Subject'] + maindata['Session'])].copy()

# TAU LOADINGS
images = list(paths['tau_registered'])
tau_loadings_cache = os.path.join(output_directory, 'masterTables', '_tau_loadings.csv')
if os.path.isfile(tau_loadings_cache):
    print()
    print(f'>  Using cached tau loadings at {tau_loadings_cache}.')
    tau_loadings = pd.read_csv(tau_loadings_cache)
else:
    print()
    print('>  No cached tau loadings found; recomputing..')
    tau_loadings = taunmf.compute_loadings_dataframe(rank=tau_rank, images=images, keep_indices=tau_component_indices, keep_names=tau_component_names, prefix='PTC', suffix='SUVR')
    tau_loadings.to_csv(tau_loadings_cache, index=False)

# AMYLOID LOADINGS
images = list(paths['amyloid_registered'])
amy_loadings_cache = os.path.join(output_directory, 'masterTables', '_amyloid_loadings.csv')
if os.path.isfile(amy_loadings_cache):
    print()
    print(f'>  Using cached amyloid loadings at {amy_loadings_cache}.')
    amy_loadings = pd.read_csv(amy_loadings_cache)
else:
    print()
    print('>  No cached amyloid loadings found; recomputing..')
    amy_loadings = amynmf.compute_loadings_dataframe(rank=amy_rank, images=images, keep_indices=amy_component_indices, keep_names=amy_component_names, prefix='PAC', suffix='SUVR')
    amy_loadings.to_csv(amy_loadings_cache, index=False)

# CREATE FEATURES
# reset index is used to ensure we are just pasting things in the same order as the images being iterated over
features = pd.concat([paths[['Subject', 'Session']].reset_index(drop=True), tau_loadings.reset_index(drop=True), amy_loadings.reset_index(drop=True)], axis=1)
outpath = os.path.join(output_directory, 'masterTables', 'FEATURE_NMFLOADINGS.csv')
features.to_csv(outpath, index=False)