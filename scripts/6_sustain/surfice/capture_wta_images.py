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
from surfice_helpers import plot_both_hemispheres

# get paths
indir = os.path.join(ATSTAGING_OUTPUT_ROOT, 'images', 'wta_paint')
outdir = os.path.join(ATSTAGING_OUTPUT_ROOT, 'plots', 'surfice')
os.makedirs(outdir, exist_ok=True)

# function for getting specific arguments for different images
def classifier(image):
    bname = os.path.basename(image)

    if 'ols_surfice_coefficients' in image:
        split = 'training' if 'training' in image else 'validation'
        biomarker = 'amyloid' if 'amyloid' in image else 'tau'
        subdir = f'{split}-{biomarker}'
        args = {
            'output_directory': os.path.join(outdir, 'ols_coefficients', subdir),
            'colormap': 'custom-tmap_2_22',
            'overlayminmax': (0.1, 22)
        }
    elif 'wscores' in image:
        subdir = bname[:-7]
        colormap = 'viridis' if 'amyloid' in bname else 'inferno'
        args = {
            'output_directory': os.path.join(outdir, 'wscore_subtype_progression', subdir),
            'colormap': colormap,
            'overlayminmax': (2, 7),
            'overlayextreme': 1
        }
    elif 'wpositivity' in image:
        rng = (0.4, 0.85) if 'amyloid' in image else (0.1, 0.25)
        colormap = 'blue-green' if 'amyloid' in image else 'red-yellow'
        args = {
            'output_directory': os.path.join(outdir, 'wscore_positivity'),
            'colormap':colormap,
            'overlayminmax': rng,
            'overlayextreme': 1
        }
    else:
        raise ValueError('No arguments detected for image: ', bname)

    odir = args['output_directory']
    os.makedirs(odir, exist_ok=True)

    return args

# run

for subfolder in os.listdir(indir):
    subfolder_fullpath = os.path.join(indir, subfolder)
    if not os.path.isdir(subfolder_fullpath):
        continue

    images = [x for x in os.listdir(subfolder_fullpath) if x.endswith('.nii.gz')]

    for image in images:
        image_fullpath = os.path.join(subfolder_fullpath, image)
        args = classifier(image_fullpath)
        plot_both_hemispheres(nifti_path=image_fullpath, overwrite=False, **args)
