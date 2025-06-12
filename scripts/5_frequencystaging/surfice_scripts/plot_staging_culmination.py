#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SURF ICE SCRIPT
# ------------------------------
#
# This script is intended to be run in the program Surf Ice.
# It is run with its Python interpreter, as such it does not have
# access to all libraries used in the rest of this repo.
# As a result, some paths are hardcoded.

# Note that opening this script in Surf Ice will run it.
# You can instead create a new script and copy/paste the contents.

import gl
gl.resetdefaults()

# IMPORTS
############

import gl
import os
import sys

# VARIABLES
############

# Manually set the output directory
# Should be the same as the output_directory entry of the atstaging config
# This is used to automatically find the needed images to plot
# And direct the outputs
ATSTAGING_OUTPUT_ROOT = '/Users/earnestt1234/Desktop/atstaging/'

# directory with script containing helper functions for surf ice
# in this repo, its under scripts/misc
SURFICE_HELPERS_DIR = '/Users/earnestt1234/Documents/GitHub/at_nmf_sustain/scripts/misc'

# names of custom created color maps for representing the staging
AMY_CMAP = 'custom-amyloidstaging'
TAU_CMAP = 'custom-taustaging'

# MAIN
############

# Load helper function
sys.path.append(SURFICE_HELPERS_DIR)
from surfice_helpers import plot_both_hemispheres

# get paths
path_amy_brain = os.path.join(ATSTAGING_OUTPUT_ROOT, 'images/staging_brains/training_staging_amyloid.nii.gz')
path_tau_brain = os.path.join(ATSTAGING_OUTPUT_ROOT, 'images/staging_brains/training_staging_tau.nii.gz')
outdir = os.path.join(ATSTAGING_OUTPUT_ROOT, 'plots', 'surfice', 'staging')
os.makedirs(outdir, exist_ok=True)

# run
plot_both_hemispheres(
    nifti_path=path_amy_brain,
    output_directory=outdir,
    output_name='amyloid_stages',
    colormap=AMY_CMAP)

plot_both_hemispheres(
    nifti_path=path_tau_brain,
    output_directory=outdir,
    output_name='tau_stages',
    colormap=TAU_CMAP)
