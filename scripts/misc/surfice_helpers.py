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

def plot_hemisphere(nifti_path, side, output_directory, output_name=None,
                    colormap='actc', overlayminmax=None, overlayextreme=None,
                    overwrite=True, smoothed=True):

    # screen arguments
    side = side.lower()
    if side == 'l':
        side = 'left'
    if side == 'r':
        side = 'right'
    if side not in ['left', 'right']:
        raise ValueError('`side` must be "left" or "right".')

    smoothed = '_smoothed' if smoothed else ''
    if side == 'left':
        mesh_path = f'/Applications/Surfice/BrainNet/BrainMesh_ICBM152{smoothed}.lh.mz3'
        sagittal_lateral_view = 0
        sagittal_medial_view = 1
        sidetag = 'LH'
    else:
        mesh_path = f'/Applications/Surfice/BrainNet/BrainMesh_ICBM152{smoothed}.rh.mz3'
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
        
    # setup output names
    outname_lateral = f'{name}_{sidetag}_lateral.png'
    outpath_lateral = os.path.join(output_directory, outname_lateral)

    outname_medial = f'{name}_{sidetag}_medial.png'
    outpath_medial  = os.path.join(output_directory, outname_medial)

    if os.path.exists(outpath_lateral) and os.path.exists(outpath_medial) and not overwrite:
        bname = os.path.basename(nifti_path)
        print(f'Existing lateral and medial outputs for "{bname}"; not rerunning.')
        return

    # setup output folder
    os.makedirs(output_directory, exist_ok=True)

    # begin plotting
    print(mesh_path)
    gl.meshload(mesh_path)

    # add image
    gl.overlayload(nifti_path)
    gl.overlaycolorname(1, colormap)
    gl.overlayopacity(1, 100)
    if overlayminmax is not None:
        a, b = overlayminmax
        gl.overlayminmax(1, a, b)
    if overlayextreme is not None:
        gl.overlayextreme(1, overlayextreme)

    # lateral view
    gl.viewsagittal(sagittal_lateral_view)
    gl.cameradistance(.8)
    gl.savebmpxy(outpath_lateral, 1000, 1000)

    # medial view
    gl.viewsagittal(sagittal_medial_view)
    gl.cameradistance(.8)
    gl.savebmpxy(outpath_medial, 1000, 1000)

def plot_both_hemispheres(nifti_path, output_directory, output_name=None, colormap='actc',
                          overlayminmax=None, overlayextreme=None, smoothed=True, overwrite=True):
    plot_hemisphere(
        nifti_path=nifti_path,
        side='left',
        colormap=colormap,
        output_directory=output_directory,
        output_name=output_name,
        overlayminmax=overlayminmax,
        overlayextreme=overlayextreme,
        overwrite=overwrite,
        smoothed=smoothed
        )

    plot_hemisphere(
        nifti_path=nifti_path,
        side='right',
        colormap=colormap,
        output_directory=output_directory,
        output_name=output_name,
        overlayminmax=overlayminmax,
        overlayextreme=overlayextreme,
        overwrite=overwrite,
        smoothed=smoothed
        )

