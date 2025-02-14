#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 23 10:59:35 2024

@author: earnestt1234
"""

# def iterative_smoothing(imgpath, target_fwhm, max_fwhm=):
#     pass

import itertools as it
import os
import tempfile

import nibabel as nib
from nilearn.image import smooth_img

from atstaging.preprocessing.execute import execute, get_cli_path

def _get_next_smoothing_dimension(measured, target, xyz_cycle, tolerance=0.5):
    smoothness_complete = _smoothness_achieved_by_dimension(measured, target, tolerance)
    for _ in range(len(smoothness_complete)):
        dim = next(xyz_cycle)
        if not smoothness_complete[dim]:
            return dim

    raise RuntimeError('Unable to find a dimension for smoothing! '
                       f'Measured: {measured}',
                       f'Target: {target}')

def _smoothness_achieved_by_dimension(measured, target, tolerance=0.5):
    return [((targ - meas) <= tolerance) for meas, targ in zip(measured, target)]

def _smoothness_achieved(measured, target, tolerance=0.5):
    return all(_smoothness_achieved_by_dimension(measured=measured, target=target, tolerance=tolerance))

def _get_next_smoothing_filter(current_filter, stepsize, measured, target, xyz_cycle, tolerance=0.5):
    dim = _get_next_smoothing_dimension(measured=measured,
                                        target=target,
                                        xyz_cycle=xyz_cycle,
                                        tolerance=tolerance)
    new_filter = current_filter[:]
    new_filter[dim] += stepsize
    return new_filter

def apply_3dFWHMx(imgpath, automask=True, difMAD=True, verbose=False):

    with tempfile.TemporaryDirectory() as WORKINGDIR:
        PROG = get_cli_path('3dFWHMx')
        OUTPUT = os.path.join(WORKINGDIR, '3dfwhm.txt')
        command = [PROG,
                   '-input', imgpath,
                   '-out', OUTPUT,
                   '-acf', 'NULL']
        if automask:
            command += ['-automask']
        if difMAD:
            command += ['-2difMAD']

        execute(command, verbose=verbose)

        with open(OUTPUT, 'r') as f:
            result = f.read()

        return tuple(float(i) for i in result.split())

def apply_3dFWHMx_NIFTI(nifti, automask=True, difMAD=True, verbose=False):

    with tempfile.TemporaryDirectory() as WORKINGDIR:
        path = os.path.join(WORKINGDIR, 'img.nii.gz')
        nib.save(nifti, path)
        fwhm = apply_3dFWHMx(path, automask=automask, difMAD=difMAD, verbose=verbose)
    return fwhm

def iterative_smoothing(imgpath, outpath, target_fwhm=(8, 8, 8),
                        start_fwhm=(0, 0, 0), stepsize=0.5,
                        tolerance=0.5, max_iterations=60,
                        automask=True, difMAD=True, verbose=True):

    vprint = print if verbose else lambda *args, **kwargs: None

    vprint()
    vprint('========================')
    vprint('= ITERATIVE SMOOTHING =')
    vprint('=======================')

    vprint()
    vprint('Parameters:')
    vprint()
    vprint(f'Image: {imgpath}')
    vprint(f'Target resoltion (FWHM): {target_fwhm}')
    vprint(f'Starting filter (FWHM): {start_fwhm}')
    vprint(f'Stepsize (mm): {stepsize}')
    vprint(f'Tolerance (mm): {tolerance}')
    vprint(f'Max iterations: {max_iterations}')

    orig_nii = nib.load(imgpath)
    orig_fwhm = apply_3dFWHMx(imgpath, automask=automask, difMAD=difMAD)
    vprint()
    vprint(f'Initial smoothness estimation: {orig_fwhm}')

    if _smoothness_achieved(measured=orig_fwhm,
                            target=target_fwhm,
                            tolerance=tolerance):
        print()
        print(f'Estimated smoothess {orig_fwhm} is already smoother than target {tuple(target_fwhm)}; ',
              'no smoothing applied.')
        nib.save(orig_nii, outpath)
        info = {'original_fwhm_x': orig_fwhm[0],
                'original_fwhm_y': orig_fwhm[1],
                'original_fwhm_z': orig_fwhm[2],
                'final_fwhm_x': orig_fwhm[0],
                'final_fwhm_y': orig_fwhm[1],
                'final_fwhm_z': orig_fwhm[2],
                'kernel_x': 0,
                'kernel_y': 0,
                'kernel_z': 0,
                'target_fwhm': target_fwhm,
                'smoothing_applied': False}
        return info

    c = 0
    xyz_cycle = it.cycle([0, 1, 2])
    current_filter = list(start_fwhm)

    vprint()
    vprint('Initating algorithm...')

    while c < max_iterations:

        vprint()
        vprint( '----------------')
        vprint(f'Iteration #{c+1}')
        vprint( '----------------')

        vprint(f'Applying smoothing kernel: {current_filter}')
        smoothed = smooth_img(orig_nii, fwhm=current_filter)
        smoothed_fwhm = apply_3dFWHMx_NIFTI(smoothed, automask=automask, difMAD=difMAD)
        vprint(f'Estimated resolution after smoothing: {smoothed_fwhm}')

        if _smoothness_achieved(measured=smoothed_fwhm,
                                target=target_fwhm,
                                tolerance=tolerance):
            vprint('Target smoothness achieved in all dimensions; exiting.')
            break

        vprint('Proceeding to next iteration.')
        current_filter = _get_next_smoothing_filter(current_filter=current_filter,
                                                    stepsize=stepsize,
                                                    measured=smoothed_fwhm,
                                                    target=target_fwhm,
                                                    xyz_cycle=xyz_cycle)
        c += 1
    else:
        vprint()
        vprint('*** WARNING ***')
        vprint('Max iterations reached; target smoothing not achieved.')
        vprint('Either increase iterations, increase stepsize, or lower tolerance.')
        vprint('***************')

    vprint()
    vprint(f'Final resolution: {smoothed_fwhm}')

    vprint()
    vprint(f'Saving image at {outpath}...')
    nib.save(smoothed, outpath)
    vprint('Done.')

    info = {'original_fwhm_x': orig_fwhm[0],
            'original_fwhm_y': orig_fwhm[1],
            'original_fwhm_z': orig_fwhm[2],
            'final_fwhm_x': smoothed_fwhm[0],
            'final_fwhm_y': smoothed_fwhm[1],
            'final_fwhm_z': smoothed_fwhm[2],
            'kernel_x': current_filter[0],
            'kernel_y': current_filter[1],
            'kernel_z': current_filter[2],
            'target_fwhm': target_fwhm,
            'smoothing_applied': True}

    return info
