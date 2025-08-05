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

# MAIN
############

# Load helper function
sys.path.append(SURFICE_HELPERS_DIR)
from surfice_helpers import plot_hemisphere

# get paths
indir = os.path.join(ATSTAGING_OUTPUT_ROOT, 'images', 'suvr_by_stage')
outdir = os.path.join(ATSTAGING_OUTPUT_ROOT, 'plots', 'surfice', 'suvr_by_stage')
os.makedirs(outdir, exist_ok=True)

# run
images = [x for x in os.listdir(indir) if x.endswith('.nii.gz')]

for image in images:
    image = os.path.join(indir, image)
    plot_hemisphere(
        nifti_path=image,
        side='left',
        colormap='actc',
        output_directory=outdir,
        overlayminmax=(1, 2)
        )
