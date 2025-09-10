
import os

import numpy as np
from pySuStaIn import ZscoreSustain
from sklearn.model_selection import StratifiedKFold

from atstaging.config import get, set_config
from atstaging.outputs import load_split
from atstaging.sustain import SustainManager

# CONFIG
set_config('main')
root_output_directory = get('output_directory')

# LOAD DATA
df = load_split('training', 'baseline', verbose=False)
control_mask = df['ControlForStaging']
df = df[~control_mask].copy()
biomarker_labels = list(df.columns[df.columns.str.contains('WScore')])
sustain_data = df[biomarker_labels].copy().to_numpy()
n_biomarkers = len(biomarker_labels)

# PARAMETERS

# z-score stuff
Z_vals = np.zeros((n_biomarkers, 1))
Z_vals[:] = 2.5
Z_max = np.zeros(n_biomarkers)
Z_max[:] = 5

# other parameters
N_startpoints = 25
N_S_max = 10
N_iterations_MCMC = int(1e5)

# i/o
output_folder = os.path.join(root_output_directory, 'sustain', 'training')
os.makedirs(output_folder)
dataset_name = 'atstaging'

# random state
seed = 42

# Establish model
sustain = ZscoreSustain(
    data=sustain_data,
    Z_vals=Z_vals,
    Z_max=Z_max,
    biomarker_labels=biomarker_labels,
    N_startpoints=N_startpoints,
    N_S_max=N_S_max,
    N_iterations_MCMC=N_iterations_MCMC,
    output_folder=output_folder,
    dataset_name=dataset_name,
    use_parallel_startpoints=False,
    seed=seed
    )

manager = SustainManager(sustain)

# Establish CV
N_folds = 10
labels = df['CDRBinned'].isin(['0.5', '1.0+']).astype(float).values
cv = StratifiedKFold(n_splits=N_folds, shuffle=True)
cv_it = cv.split(sustain_data, labels)

test_indices = []
for train, test in cv_it:
    test_indices.append(test)
test_indices = np.array(test_indices, dtype='object')

# RUN
manager.run_main()
manager.run_cv(test_indices)