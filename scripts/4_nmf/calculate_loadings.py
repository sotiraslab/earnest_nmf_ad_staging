# IMPORTS
import os

import pandas as pd

from atstaging.config import get, set_config
from atstaging.nmf.utils import load_nmf_runner
from atstaging.outputs import load_paths_tables, load_split

# PARAMETERS
tau_nmf_name = 'tau1390'
tau_rank = 11
tau_component_indices = [3, 4, 5, 6, 7, 9, 10]
tau_component_names = ['LeftParietlTemporal', 'Occipital', 'RightParietalTemporal', 'Frontal', 'MedialTemporal', 'Sensorimotor', 'Orbitofrontal']

amy_nmf_name = 'amyloidCN1183'
amy_rank = 12
amy_component_indices = [1, 3, 5, 8, 10]
amy_component_names = ['FrontalCingulatePrecuneus', 'Parietal', 'Occipital', 'Sensorimotor', 'Insular']

# CONFIG
set_config('main')
output_directory = get('output_directory')

# LOAD NMF RUNNERS
taunmf = load_nmf_runner(os.path.join(output_directory, 'nmf', 'runs', 'tau1390'))
amynmf = load_nmf_runner(os.path.join(output_directory, 'nmf', 'runs', 'amyloid1390'))

# LOAD PATHS TO PREPROCESSED IMAGES
# filtered to be only the images in the final dataset
maindata = load_split(None, None)
paths = load_paths_tables()
paths = paths[(paths['Subject'] + paths['Session']).isin(maindata['Subject'] + maindata['Session'])].copy()

# TAU LOADINGS
images = list(paths['tau_registered'])
tau_loadings = taunmf.compute_loadings_dataframe(rank=tau_rank, images=images, keep_indices=tau_component_indices, keep_names=tau_component_names, prefix='PTC', suffix='SUVR')

# AMYLOID LOADINGS
images = list(paths['amyloid_registered'])
amy_loadings = amynmf.compute_loadings_dataframe(rank=amy_rank, images=images, keep_indices=amy_component_indices, keep_names=amy_component_names, prefix='PAC', suffix='SUVR')

# CREATE FEATURES
features = pd.concat([paths[['Subject', 'Session']], tau_loadings, amy_loadings], axis=1)
outpath = os.path.join(output_directory, 'masterTables', 'FEATURE_NMFLOADINGS.csv')
features.to_csv(outpath, index=False)