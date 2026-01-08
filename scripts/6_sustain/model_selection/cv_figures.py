import os

import matplotlib.pyplot as plt
import numpy as np

from atstaging.config import get, set_config
from atstaging.plotting import set_font_properties
from atstaging.sustain import SustainManager

# set configuration
set_config('main')
cv_folds = 10

# Load sustain models
root_output = get('output_directory')
training_dir = os.path.join(root_output, 'sustain', 'training')
training = SustainManager(training_dir)

# update path for working off of CHPC
ofolder = os.path.join(root_output, 'sustain', 'training')
training.update_output_folder(ofolder)

# load CV results (takes a bit of time)
opath_cvic = os.path.join(ofolder, 'cvic', 'cvic.npy')
opath_llmat = os.path.join(ofolder, 'cvic', 'llmat.npy')

if os.path.isfile(opath_cvic) and os.path.isfile(opath_llmat):
    training_CVIC = np.load(opath_cvic)
    training_loglike_matrix = np.load(opath_llmat)
else:
    training_test_idxs = training.load_test_indices(cv_folds)
    training_CVIC, training_loglike_matrix = training.sustain.cross_validate_sustain_model(training_test_idxs)

    os.makedirs(os.path.join(ofolder, 'cvic'), exist_ok=True)
    np.save(opath_cvic, training_CVIC)
    np.save(opath_llmat, training_loglike_matrix)

set_font_properties(6)

# plotting output
odir = os.path.join(root_output, 'plots', 'sustain', 'model_selection')
os.makedirs(odir, exist_ok=True)

# CVIC curve
plt.figure(figsize=(3.46, 3.46))
_ = training.plot_cvic(training_CVIC)
plt.tight_layout()
plt.savefig(os.path.join(odir, 'training_cvic.svg'))

# CV likelihood
plt.figure(figsize=(3.46, 3.46))
_ = training.plot_cv_loglikelihood(training_loglike_matrix)
plt.tight_layout()
plt.savefig(os.path.join(odir, 'training_cv_likelihood.svg'))
