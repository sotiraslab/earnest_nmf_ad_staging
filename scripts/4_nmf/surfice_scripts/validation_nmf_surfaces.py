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

# colormap
COLORMAP = 'x-rain'

# MAIN
############

# Load helper function
sys.path.append(SURFICE_HELPERS_DIR)
from surfice_helpers import plot_both_hemispheres

# main
outdir = os.path.join(ATSTAGING_OUTPUT_ROOT, 'plots', 'surfice', 'validation_components')
os.makedirs(outdir, exist_ok=True)

images_dir = os.path.join(ATSTAGING_OUTPUT_ROOT, 'images')
image_subdirs = os.listdir(images_dir)
validation_subdirs = [d for d in  image_subdirs if d.startswith('validation')]

for i, valfolder in enumerate(validation_subdirs):
    valfolder_fullpath = os.path.join(images_dir, valfolder)
    rankfolders = os.listdir(valfolder_fullpath)
    rankfolders = [d for d in rankfolders if d.startswith('rank')]

    for j, rankfolder in enumerate(rankfolders):
        rankfolder_fullpath = os.path.join(valfolder_fullpath, rankfolder)
        niftis = sorted([x for x in os.listdir(rankfolder_fullpath) if x.endswith('.nii.gz')])

        for k, img in enumerate(niftis):

            fullimg = os.path.join(rankfolder_fullpath, img)
            name = img[:-7] # removes .nii.gz extension

            this_outfolder = os.path.join(outdir, f'{valfolder}_{rankfolder}', name)
            os.makedirs(this_outfolder, exist_ok=True)

            plot_both_hemispheres(
                nifti_path=fullimg,
                output_directory=this_outfolder,
                output_name=name,
                colormap=COLORMAP,
                overlayextreme=1
                )
