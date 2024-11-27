# -*- coding: utf-8 -*-
"""
Created on Wed Sep  4 13:53:34 2024

@author: earne
"""

import os
from pathlib import Path

import nibabel as nib

from atstaging.preprocessing.execute import execute

def ecat_to_nifti(inimg, outimg):
    # https://neurostars.org/t/how-can-i-convert-ecat-v-file-to-nifti-nii-file-in-python/27297/2
    ecat = nib.ecat.load(inimg)
    nii = nib.Nifti1Image(
        ecat.get_fdata(),
        ecat.affine
    )
    nib.save(nii, outimg)

def run_dcm2niix(indir, outdir, name, silent=False):

    call = [
        'dcm2niix', 
        '-a', 'y',
        '-z', 'y',
        '-w', '1',
        '-f', name,
        '-o', outdir,
        indir
        ]

    execute(call, verbose=not silent)

def recursive_dcm2niix(indir, outdir, name_fmt=r'sub-%i_ses-%t_desc-%p'):

    for root, _, files in os.walk(indir):
        contains_dicoms = any([f.lower().endswith('dcm') for f in files])
        if not contains_dicoms:
            continue
        relpath = os.path.relpath(root, indir)
        output_folder = os.path.join(outdir, relpath)
        Path(output_folder).mkdir(exist_ok=True, parents=True)
        run_dcm2niix(root, output_folder, name=name_fmt)

