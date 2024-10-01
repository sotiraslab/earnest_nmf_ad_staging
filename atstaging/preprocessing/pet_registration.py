#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  1 11:24:34 2024

@author: earnestt1234
"""

import os
import shutil
import tempfile
import warnings

from colorama import Fore, Style

from atstaging.config import get
from atstaging.preprocessing.execute import execute
from atstaging.preprocessing.dicom_to_nifiti import run_dcm2niix
from atstaging.preprocessing.reorient import reorient_image

def _ants_registration_outputs(prefix):
    outputs = {
        'affine': prefix + "0GenericAffine.mat",
        'warp': prefix + "1Warp.nii.gz",
        'rigidregistered': prefix + "Warped.nii.gz",
        'invwarp': prefix + "1InverseWarp.nii.gz",
        'fullwarp': prefix + '1FullWarp.nii.gz',
        'petbrainmask': prefix + 'BrainMaskPETSpace.nii.gz',
        'petbrain': prefix + 'PETBrain.nii.gz',
        'petregistered': prefix + 'PETRegistered.nii.gz',
        }
    return outputs

def _copy_outputs(prefix, out_registered=None, out_rigid_reg=None,
                  out_warp=None, out_petbrain=None):

    outputs = _ants_registration_outputs(prefix)
    registered = outputs['petregistered']
    rigid_reg = outputs['rigidregistered']
    warp = outputs['fullwarp']
    petbrain = outputs['petbrain']

    if os.path.isfile(registered) and out_registered is not None:
        shutil.move(registered, out_registered)

    if os.path.isfile(rigid_reg) and out_rigid_reg is not None:
        shutil.move(rigid_reg, out_rigid_reg)

    if os.path.isfile(warp) and out_warp is not None:
        shutil.move(warp, out_warp)

    if os.path.isfile(petbrain) and out_petbrain is not None:
        shutil.move(petbrain, out_petbrain)

def preregistration_pet(pet, output):

    is_dicom = os.path.isdir(pet)
    outdir = os.path.dirname(os.path.abspath(output))
    name = os.path.basename(output).removesuffix('.nii.gz')
    if is_dicom:
        print()
        print('>>> Running DICOM to NIFTI conversion...')
        print('- - -')
        run_dcm2niix(pet, outdir, name)
        pet = output
        print('- - -')

    print()
    print('>>> Running image reorientation...')
    reorient_image(pet, 'RPI', outpath=output)

def register_pet_image(pet, t1, brainmask, brain, warp, mni_brain=None,
                       out_registered=None, out_rigid_reg=None, out_warp=None,
                       out_petbrain=None):
    outputs = [out_registered, out_rigid_reg, out_warp, out_petbrain]
    if all(x is None for x in outputs):
        warnings.warn(RuntimeWarning('MRI registration: no outputs selected, exiting!'))
        return

    with tempfile.TemporaryDirectory() as WORKINGDIR:

        print()
        print(f'>>> Created temporary working directory: {WORKINGDIR}')

        # variables
        ANTSPATH = get('ants')
        PREFIX = os.path.join(WORKINGDIR, '_temp_output')
        OUTNAMES = _ants_registration_outputs(PREFIX)
        REFERENCE = mni_brain if mni_brain is not None else get('mni152_brain')

        # software
        ants_registration = os.path.join(ANTSPATH, 'antsRegistrationSyNQuick.sh')
        ants_applytransforms = os.path.join(ANTSPATH, 'antsApplyTransforms')
        ants_imagemath = os.path.join(ANTSPATH, 'ImageMath')

        print()
        print(Fore.BLUE + Style.BRIGHT + 'PET Registration')
        print('~~~~~'  + Style.RESET_ALL)

        # rigid registration
        command = [
            ants_registration,
            '-d', '3',
            '-m', pet,
            '-f', t1,
            '-o', PREFIX,
            '-t', 'r'
            ]

        print()
        print('>>> Running rigid registration of PET to MRI:')
        print('    ' + Fore.YELLOW + ' '.join(command) + Style.RESET_ALL)
        print('- - -')
        execute(command)
        print('- - -')

        # skullstrip the PET image
        affine = OUTNAMES['affine']
        petbrain = OUTNAMES['petbrain']
        petbrainmask = OUTNAMES['petbrainmask']
        command = [
            ants_applytransforms,
            '-d', '3',
            '-i', brainmask,
            '-r', pet,
            '-o', petbrainmask,
            '-t', f"[{affine},1]",
            '-n', 'NearestNeighbor',
            '-v'
            ]

        print()
        print('>>> Moving MRI brain mask to PET space:')
        print('    ' + Fore.YELLOW + ' '.join(command) + Style.RESET_ALL)
        print('- - -')
        execute(command)
        print('- - -')

        command = [ants_imagemath, '3', petbrain, 'm', petbrainmask, pet]

        print()
        print('>>> Skullstripping the PET image:')
        print('    ' + Fore.YELLOW + ' '.join(command) + Style.RESET_ALL)
        print('- - -')
        execute(command)
        print('- - -')

        # combined transform
        fullwarp = OUTNAMES['fullwarp']
        command = [
            ants_applytransforms,
            '-d', '3',
            '-i', pet,
            '-r', REFERENCE,
            '-t', warp, affine,
            '-o', f'[{fullwarp},1]',
            '-v', '1']

        print()
        print('>>> Combining the transformation (PET -> T1 + T1 -> MNI):')
        print('    ' + Fore.YELLOW + ' '.join(command) + Style.RESET_ALL)
        print('- - -')
        execute(command)
        print('- - -')

        # apply combined transform
        final = OUTNAMES['petregistered']
        command = [
            ants_applytransforms,
            '-d', '3',
            '-i', petbrain,
            '-r', REFERENCE,
            '-t', fullwarp,
            '-o', final,
            '-v', '1']

        print()
        print('>>> Warping PET brain image to MNI space:')
        print('    ' + Fore.YELLOW + ' '.join(command) + Style.RESET_ALL)
        print('- - -')
        execute(command)
        print('- - -')

        # move output files
        print()
        print('>>> Copying outputs to selected destinations. ')
        _copy_outputs(PREFIX, out_registered=out_registered,
                      out_warp=out_warp, out_rigid_reg=out_rigid_reg,
                      out_petbrain=out_petbrain)

        # cleanup
        # this is removing all the temporary images created in the PREFIX directory
        # the user-specified outputs should already be moved
        print()
        print('>>> Removing temporary files.')
        print('- - -')
        for key, value in OUTNAMES.items():
            print(f'  - "{key}": {value}')
            if os.path.exists(value):
                os.remove(value)
        print('- - -')

        print('Completed!')

