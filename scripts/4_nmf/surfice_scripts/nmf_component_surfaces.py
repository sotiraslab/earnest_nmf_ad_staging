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

# NMF ranks
AMY_RANK = 11
TAU_RANK = 12

# colormap
COLORMAP = 'x-rain'

# MAIN
############

# Load helper function
sys.path.append(SURFICE_HELPERS_DIR)
from surfice_helpers import plot_both_hemispheres

# get paths
amyloid_components = os.path.join(ATSTAGING_OUTPUT_ROOT, 'images', 'amyloid_components', f'rank{AMY_RANK}')
tau_components = os.path.join(ATSTAGING_OUTPUT_ROOT, 'images', 'tau_components', f'rank{TAU_RANK}')
outdir = os.path.join(ATSTAGING_OUTPUT_ROOT, 'plots', 'surfice', 'components')
os.makedirs(outdir, exist_ok=True)

# sort out the amyloid & tau images
amyloid_images = sorted([x for x in os.listdir(amyloid_components) if x.endswith('.nii.gz')])
tau_images = sorted([x for x in os.listdir(tau_components) if x.endswith('.nii.gz')])

for i, img in enumerate(amyloid_images):

    fullimg = os.path.join(amyloid_components, img)
    name = img[:-7] # removes .nii.gz extension

    this_outfolder = os.path.join(outdir, 'amyloid', name)
    os.makedirs(this_outfolder, exist_ok=True)

    plot_both_hemispheres(
        nifti_path=fullimg,
        output_directory=this_outfolder,
        output_name=name,
        colormap=COLORMAP,
        overlayextreme=1
        )

for i, img in enumerate(tau_images):

    fullimg = os.path.join(tau_components, img)
    name = img[:-7] # removes .nii.gz extension

    this_outfolder = os.path.join(outdir, 'tau', name)
    os.makedirs(this_outfolder, exist_ok=True)

    plot_both_hemispheres(
        nifti_path=fullimg,
        output_directory=this_outfolder,
        output_name=name,
        colormap=COLORMAP,
        overlayextreme=1
        )
