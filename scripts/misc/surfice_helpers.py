#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 12 12:17:20 2025

@author: earnestt1234

"""

# Other than gl, only standard library should be used
# (not sure what packages are available with Surf Ice)
import os

import gl

def plot_hemisphere(nifti_path, side, output_directory, output_name=None, colormap='actc'):

    # screen arguments
    side = side.lower()
    if side == 'l':
        side = 'left'
    if side == 'r':
        side = 'right'
    if side not in ['left', 'right']:
        raise ValueError('`side` must be "left" or "right".')

    if side == 'left':
        mesh_path = '/Applications/Surfice/BrainNet/BrainMesh_ICBM152_smoothed.lh.mz3'
        sagittal_lateral_view = 0
        sagittal_medial_view = 1
        sidetag = 'LH'
    else:
        mesh_path = '/Applications/Surfice/BrainNet/BrainMesh_ICBM152_smoothed.rh.mz3'
        sagittal_lateral_view = 1
        sagittal_medial_view = 0
        sidetag = 'RH'

    if output_name is not None:
        name = output_name
    else:
        basename = os.path.basename(nifti_path)
        if basename.endswith('.nii.gz'):
            name = basename[:-7]
        elif basename.endswith('.nii'):
            name = basename[:-4]
        else:
            raise ValueError('Did not recognized `nifti_path` as NIFTI or compressed NIFTI.')

    # setup output folder
    os.makedirs(output_directory, exist_ok=True)

    # begin plotting
    gl.meshload(mesh_path)

    # add image
    gl.overlayload(nifti_path)
    gl.overlaycolorname(1, colormap)
    gl.overlayopacity(1, 100)

    # lateral view
    gl.viewsagittal(sagittal_lateral_view)
    gl.cameradistance(.8)
    outname = f'{name}_{sidetag}_lateral.png'
    outpath = os.path.join(output_directory, outname)
    gl.savebmpxy(outpath, 1000, 1000)

    # medial view
    gl.viewsagittal(sagittal_medial_view)
    gl.cameradistance(.8)
    outname = f'{name}_{sidetag}_medial.png'
    outpath = os.path.join(output_directory, outname)
    gl.savebmpxy(outpath, 1000, 1000)


def plot_both_hemispheres(nifti_path, output_directory, output_name=None, colormap='actc'):
    plot_hemisphere(
        nifti_path=nifti_path,
        side='left',
        colormap=colormap,
        output_directory=output_directory,
        output_name=output_name
        )

    plot_hemisphere(
        nifti_path=nifti_path,
        side='right',
        colormap=colormap,
        output_directory=output_directory,
        output_name=output_name
        )

