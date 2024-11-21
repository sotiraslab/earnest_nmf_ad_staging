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
import nibabel as nib
import numpy as np

from atstaging.config import get
from atstaging.preprocessing.execute import execute
from atstaging.preprocessing.conversion import ecat_to_nifti, run_dcm2niix
from atstaging.preprocessing.reorient import reorient_image
from atstaging.preprocessing.segmentation import compute_regional_statistics_MUSE
from atstaging.preprocessing.smoothing import iterative_smoothing

def _ants_registration_outputs(prefix):
    outputs = {
        'affine': prefix + "0GenericAffine.mat",
        'warp': prefix + "1Warp.nii.gz",
        'rigidregistered': prefix + "Warped.nii.gz",
        'origsuvr': prefix + 'OrigSUVR.nii.gz',
        'invwarp': prefix + "1InverseWarp.nii.gz",
        'fullwarp': prefix + '1FullWarp.nii.gz',
        'petbrainmask': prefix + 'BrainMaskPETSpace.nii.gz',
        'petsegmentation': prefix + 'SegementationPETSpace.nii.gz',
        'petbrain': prefix + 'PETBrain.nii.gz',
        'petregistered': prefix + 'PETRegistered.nii.gz',
        }
    return outputs

def _copy_outputs(prefix, out_registered=None, out_rigid_reg=None,
                  out_suvr=None, out_warp=None, out_petbrain=None):

    outputs = _ants_registration_outputs(prefix)
    registered = outputs['petregistered']
    rigid_reg = outputs['rigidregistered']
    suvr = outputs['origsuvr']
    warp = outputs['fullwarp']
    petbrain = outputs['petbrain']

    if os.path.isfile(registered) and out_registered is not None:
        shutil.move(registered, out_registered)

    if os.path.isfile(rigid_reg) and out_rigid_reg is not None:
        shutil.move(rigid_reg, out_rigid_reg)

    if os.path.isfile(suvr) and out_suvr is not None:
        shutil.move(suvr, out_suvr)

    if os.path.isfile(warp) and out_warp is not None:
        shutil.move(warp, out_warp)

    if os.path.isfile(petbrain) and out_petbrain is not None:
        shutil.move(petbrain, out_petbrain)

def _get_img_format(pet):
    if os.path.isdir(pet):
        return 'DICOM'
    elif pet.endswith('.v'):
        return 'ECAT'
    elif pet.endswith('.nii.gz'):
        return 'NIFTI'
    elif pet.endswith('.nii'):
        return 'NIFTI_UNCOMPRESSED'
    else:
        raise ValueError(f'Unrecognized type for {os.path.basename(pet)}')
    
def _get_shape_dict(img):
    nii = nib.load(img)
    shape = nii.shape
    output = {f'Dim{i}': s for i, s in enumerate(shape) if i <= 3}
    if len(shape) == 3:
        output['Dim3'] = None
    return output

def _is_dynamic(pet):
    nii = nib.load(pet)
    shape = nii.shape
    if len(shape) == 3:
        return False
    elif len(shape) == 4:
        return True
    else:
        raise ValueError(f'Unrecognized shape for determining dynamic image: {shape}')

def prepare_registration_pet(pet, out_nifti=None,
                             out_realign=None, out_average=None,
                             out_smoothed=None, target_fwhm=(10, 10, 10)):
    outputs = [out_nifti, out_realign, out_average, out_smoothed]
    if all([x is None for x in outputs]):
        raise ValueError('At least one output must be specified for PET pre-registration.')
    
    INFO = {
        'Source': pet
    }

    with tempfile.TemporaryDirectory() as WORKINGDIR:

        # variable to track the image as it progresses through different steps
        TEMPIMAGE_NAME = '_temp_image'
        TEMPIMAGE = os.path.join(WORKINGDIR, TEMPIMAGE_NAME + '.nii.gz')

        # covert to NIFTI
        img_fmt = _get_img_format(pet)
        INFO['ImageFormat'] = img_fmt
        print()
        print(f'>>> Detected image format: {img_fmt}')

        if img_fmt == 'DICOM':
            print()
            print('>>> Running DICOM to NIFTI conversion...')
            print('- - -')
            run_dcm2niix(pet, WORKINGDIR, TEMPIMAGE_NAME)
            print('- - -')
        elif img_fmt == 'ECAT':
            print()
            print('>>> Running ECAT to NIFTI conversion...')
            print('- - -')
            ecat_to_nifti(pet, TEMPIMAGE)
            print('- - -')
        elif img_fmt in ['NIFTI_UNCOMPRESSED', 'NIFTI']:
            print()
            print('>>> Creating compressed NIFTI image')
            print('- - -')
            nii = nib.load(pet)
            nib.save(nii, TEMPIMAGE)
            print('- - -')

        # reorient, and then save out_nifti if requested
        print()
        print('>>> Running image reorientation...')
        reorient_image(TEMPIMAGE, 'RPI')

        if out_nifti is not None:
            shutil.copy(TEMPIMAGE, out_nifti)

        # realignment
        INFO['IsDynamic'] = _is_dynamic(TEMPIMAGE)
        INFO.update(_get_shape_dict(TEMPIMAGE))
        if _is_dynamic(TEMPIMAGE):
            print()
            print('>>> Running MCFLIRT for realignment of PET frames...')
            print('- - -')
            run_mcflirt(TEMPIMAGE, TEMPIMAGE)
            print('- - -')
            INFO['MCFLIRTApplied'] = True
        else:
            print('>>> Image is not dynamic; skipping realignment.')
            INFO['MCFLIRTApplied'] = False

        if out_realign:
            shutil.copy(TEMPIMAGE, out_realign)

        # averaging
        if _is_dynamic(TEMPIMAGE):
            print('>>> Averaging image across frames...')
            print('- - -')
            nii = nib.load(TEMPIMAGE)
            data = nii.get_fdata().mean(axis=3)
            newimg = nib.Nifti1Image(dataobj=data, affine=nii.affine, header=nii.header)
            nib.save(newimg, TEMPIMAGE)
            print('- - -')
            INFO['AverageApplied'] = True
        else:
            print('>>> Image is not dynamic; skipping averaging.')
            INFO['AverageApplied'] = False

        if out_average:
            shutil.copy(TEMPIMAGE, out_average)

        # smoothing
        print()
        print(f'>>> Applying iterative smoothing algorithm to target: {target_fwhm} mm FWHM...')
        print('- - -')
        smoothstats = iterative_smoothing(TEMPIMAGE, TEMPIMAGE, target_fwhm=target_fwhm,
                                          start_fwhm=(0, 0, 0), stepsize=0.5,
                                          tolerance=0.5, max_iterations=75,
                                          automask=True, difMAD=True, verbose=True)
        INFO.update(smoothstats)
        print('- - -')

        if out_smoothed:
            shutil.copy(TEMPIMAGE, out_smoothed)

        print()
        print('PET pre-registration steps completed.')

        return INFO

def register_pet_image(pet, t1, brainmask, warp, suvr_reference_mask=None, muse_segmentation=None,
                       mni_brain=None, out_registered=None, out_suvr=None, out_rigid_reg=None, out_warp=None,
                       out_petbrain=None, out_regional_suvrs=None):
    outputs = [out_registered, out_rigid_reg, out_warp, out_petbrain, out_suvr, out_regional_suvrs]
    if all(x is None for x in outputs):
        warnings.warn(RuntimeWarning('MRI registration: no outputs selected, exiting!'))
        return
    
    INFO = {}

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

        # compute SUVR
        rigidregisted = OUTNAMES['rigidregistered']
        working_pet_image = pet
        suvr = OUTNAMES['origsuvr']
        if suvr_reference_mask is not None:
            print()
            print(f'>>> Using {suvr_reference_mask} to compuete an SUVR.')
            img = nib.load(rigidregisted)
            mask = nib.load(suvr_reference_mask)
            img_data = img.get_fdata()
            mask_data = np.isclose(mask.get_fdata(), 1.0).astype(float)
            mask_applied = np.where(mask_data == 1, img_data, 0.)
            sum_img_data = mask_applied.sum()
            n_voxels_in_mask = mask_data.sum()
            ref_uptake = float(sum_img_data / n_voxels_in_mask)
            INFO['ReferenceUptake'] = ref_uptake

            print(f'>>> Reference uptake value: {ref_uptake}')
            nii = nib.load(pet)
            data = nii.get_fdata()
            print(f'>>> Range before SUVR normalization: {float(data.min()), float(data.max())}')
            INFO['PreSUVRMin'] = float(data.min())
            INFO['PreSUVRMax'] = float(data.max())

            data /= ref_uptake
            print(f'>>> Range after SUVR normalization: {float(data.min()), float(data.max())}')
            INFO['PostSUVRMin'] = float(data.min())
            INFO['PostSUVRMax'] = float(data.max())
            
            data = np.where(data < 0, 0, data)
            print(f'>>> Range after negative removal: {float(data.min()), float(data.max())}')
            INFO['ZeroNegMin'] = float(data.min())
            INFO['ZeroNegMax'] = float(data.max())

            newimg = nib.Nifti1Image(dataobj=data, affine=nii.affine)
            nib.save(newimg, suvr)
            working_pet_image = suvr

        # skullstrip the PET image
        affine = OUTNAMES['affine']
        petbrain = OUTNAMES['petbrain']
        petbrainmask = OUTNAMES['petbrainmask']
        command = [
            ants_applytransforms,
            '-d', '3',
            '-i', brainmask,
            '-r', working_pet_image,
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

        command = [ants_imagemath, '3', petbrain, 'm', petbrainmask, working_pet_image]

        print()
        print('>>> Skullstripping the PET image:')
        print('    ' + Fore.YELLOW + ' '.join(command) + Style.RESET_ALL)
        print('- - -')
        execute(command)
        print('- - -')

        # get regional SUVRs for PET image
        petsegmentation = OUTNAMES['petsegmentation']
        if muse_segmentation is not None:
            command = [
                ants_applytransforms,
                '-d', '3',
                '-i', muse_segmentation,
                '-r', working_pet_image,
                '-o', petsegmentation,
                '-t', f"[{affine},1]",
                '-n', 'NearestNeighbor',
                '-v'
                ]
            
            print()
            print('>>> Moving T1 MUSE segmentation to PET space:')
            print('    ' + Fore.YELLOW + ' '.join(command) + Style.RESET_ALL)
            print('- - -')
            execute(command)
            print('- - -')

            print()
            print('>>> Computing regional statistics from segmentation in PET space:')
            print('- - -')
            regional_suvrs = compute_regional_statistics_MUSE(img=working_pet_image, segmentaion=petsegmentation)
            if out_regional_suvrs is not None:
                regional_suvrs.to_csv(out_regional_suvrs, index=False)
            print('- - -')

        # combined transform
        fullwarp = OUTNAMES['fullwarp']
        command = [
            ants_applytransforms,
            '-d', '3',
            '-i', working_pet_image,
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
        _copy_outputs(PREFIX, out_registered=out_registered, out_suvr=out_suvr,
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

        return INFO

def run_mcflirt(inimg, outimg):

    FSLDIR = get('fsl')
    mcflirt = os.path.join(FSLDIR, 'bin', 'mcflirt')
    command = [mcflirt,
               '-in', inimg,
               '-out', outimg,
               '-report',
               '-stages', '4']
    execute(command, env={'FSLOUTPUTTYPE': 'NIFTI_GZ'})
