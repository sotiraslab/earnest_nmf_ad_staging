"""Runs a few things after NMF has been run: 

- post NMF routine (deleting NIFTI images, creating filtered components, creating NiftiOverlay plots)
- reconstruction error analyses
- reproducibility analysis

The reconstruction error needs a lot of memory to run for images in MNI 1mm space - I usually use 64 GB.

Most of these things are set up so that results are saved, and will run quickly the second time.  But these
outputs need to be deleted if one wishes for analyses to be reran."""

# IMPORTS
import os

from atstaging.config import get, set_config
from atstaging.nmf.utils import load_nmf_runner

# CONFIG
set_config('main')
output_directory = get('output_directory')

# VARIABLES
nmf_name_tau = 'tau1390'
nmf_name_amyloid = 'amyloidCN1183'

# TAU
path_tau_nmf = os.path.join(output_directory, 'nmf', 'runs', nmf_name_tau)
taunmf = load_nmf_runner(path_tau_nmf)
taunmf.post_main()
taunmf.reconstruction_error_analysis()
taunmf.reproducibility_analysis()

# AMYLOID
path_amy_nmf = os.path.join(output_directory, 'nmf', 'runs', nmf_name_amyloid)
amynmf = load_nmf_runner(path_amy_nmf)
amynmf.post_main()
amynmf.reconstruction_error_analysis()
amynmf.reproducibility_analysis()

