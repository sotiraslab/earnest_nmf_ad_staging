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

# import gl
# gl.resetdefaults()

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

# Maximum stages for amyloid and tau, needed for setting colormap appropriately
AMY_VMAX = 2
TAU_VMAX = 4

# MAIN
############

# Load helper function
sys.path.append(SURFICE_HELPERS_DIR)
from surfice_helpers import plot_both_hemispheres

# get paths
staging_folder = os.path.join(ATSTAGING_OUTPUT_ROOT, 'images/staging_brains')
outdir = os.path.join(ATSTAGING_OUTPUT_ROOT, 'plots', 'surfice', 'staging')
os.makedirs(outdir, exist_ok=True)

# sort out the amyloid & tau images
all_images = [x for x in os.listdir(staging_folder) if x.endswith('.nii.gz')]
stage_images = [x for x in all_images if 'stage' in x]
amyloid_images = sorted([x for x in stage_images if 'amyloid' in x])
tau_images = sorted([x for x in stage_images if 'tau' in x])

# index of sorted images is used to label the stages
# this is used b/c re (regex) is not available with surf ice python
# this will fail with 2-digit stages but is fine for under that
for i, img in enumerate(amyloid_images):

    fullimg = os.path.join(staging_folder, img)
    stage = str(i)
    name = f'amyloid_stage{stage}'

    this_outfolder = os.path.join(outdir, name)
    os.makedirs(this_outfolder, exist_ok=True)

    plot_both_hemispheres(
        nifti_path=fullimg,
        output_directory=this_outfolder,
        output_name=name,
        colormap=AMY_CMAP,
        overlayminmax=(1, AMY_VMAX)
        )

for i, img in enumerate(tau_images):

    fullimg = os.path.join(staging_folder, img)
    stage = str(i)
    name = f'tau_stage{stage}'

    this_outfolder = os.path.join(outdir, name)
    os.makedirs(this_outfolder, exist_ok=True)

    plot_both_hemispheres(
        nifti_path=fullimg,
        output_directory=this_outfolder,
        output_name=name,
        colormap=TAU_CMAP,
        overlayminmax=(1, TAU_VMAX)
        )
