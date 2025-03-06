# -*- coding: utf-8 -*-
"""
Created on Wed Sep  4 13:53:34 2024

@author: earne
"""

import os
from pathlib import Path
import tempfile

import nibabel as nib
import nibabel.ecat as ecat

from atstaging.preprocessing.execute import execute

def ecat_to_nifti(inimg, outimg):
    # The previous implementation was based on this
    # https://neurostars.org/t/how-can-i-convert-ecat-v-file-to-nifti-nii-file-in-python/27297/2

    # But that seemed to screw up the axis labels for many images (not all, mostly older ones)

    # This approach, for whatever reason, seems to be doing better
    # where the frames are accessed independently
    # https://gist.github.com/cindeem/7347843

    img = ecat.load(inimg)
    mlist = img.get_mlist()
    nframes = mlist[mlist[:,0] > 0].shape[0]

    to_concat = []
    for i in range(nframes):
        tmp = nib.Nifti1Image(
            dataobj=img.get_frame(i, orientation='neurological'),
            affine=img.get_frame_affine(i)
            )
        to_concat.append(tmp)

    concat = nib.funcs.concat_images(to_concat)
    nib.save(concat, outimg)

def merge_separated_dicom_frames(input_paths, output_path):
    """
    Creates a single image from multiple DICOMS, concatenated as frames.
    This was needed for GS2 data, where some subjects have amyloid
    PET images saved as 4 separate frames.

    Parameters
    ----------
    input_paths : list
        List of paths to folders which contain DICOM files.  The order provided
        dictates the order of frames in the resulting image!
    output_path : str
        Path to the output image.

    Returns
    -------
    None.

    """

    imgs = []

    print('FRAME CONCATENATION')
    print('===================')
    print()
    print(f'> Input images: {len(input_paths)}')
    print(f'> Output path: {output_path}')

    with tempfile.TemporaryDirectory() as WORKINGDIR:
        print(f'> Temp directory: {WORKINGDIR}')

        for i, path in enumerate(input_paths):

            print()
            print(f'- PATH = {path}')

            # convert DCM to NIFTI
            print('  * Converting to NIFTI.')
            destname = f'img{i}'
            destpath = os.path.join(WORKINGDIR, destname + '.nii.gz')
            run_dcm2niix(path, WORKINGDIR, destname, silent=True)

            # load the NIFTI
            print('  * Loading NIFTI data.')
            nii = nib.load(destpath)
            imgs.append(nii)

        print()
        print('> Creating concatenated image.')
        concat = nib.concat_images(images=imgs)
        nib.save(concat, output_path)
        print(f'> Done[{output_path}].')

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

