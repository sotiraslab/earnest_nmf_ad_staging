import os

import matplotlib.pyplot as plt

from atstaging.config import get, set_config
from atstaging.plotting import set_font_properties
from atstaging.sustain import SustainManager

# set configuration
set_config('main')
set_font_properties()

# Load sustain models
root_output = get('output_directory')
training_dir = os.path.join(root_output, 'sustain', 'training')
validation_dir = os.path.join(root_output, 'sustain', 'validation')

training = SustainManager(training_dir)
validation = SustainManager(validation_dir)

# plotting output
odir = os.path.join(root_output, 'plots', 'sustain', 'model_selection')
os.makedirs(odir, exist_ok=True)

# Histograms of likelihood
plt.figure(figsize=(8, 6))
_ = training.plot_likelihood_histogram()
plt.tight_layout()
plt.savefig(os.path.join(odir, 'training_likelihood_hist.svg'))

plt.figure(figsize=(8, 6))
_ = validation.plot_likelihood_histogram()
plt.tight_layout()
plt.savefig(os.path.join(odir, 'validation_likelihood_hist.svg'))

# MCMC tracers
plt.figure(figsize=(8, 6))
_ = training.plot_mcmc_trace()
plt.tight_layout()
plt.savefig(os.path.join(odir, 'training_mcmc_trace.svg'))

plt.figure(figsize=(8, 6))
_ = validation.plot_mcmc_trace()
plt.tight_layout()
plt.savefig(os.path.join(odir, 'validation_mcmc_trace.svg'))