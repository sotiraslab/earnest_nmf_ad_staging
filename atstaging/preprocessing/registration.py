#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  6 15:48:46 2024

@author: earnestt1234
"""

import os
import shutil
import warnings

from colorama import Fore, Style

from atstaging.config import get
from atstaging.preprocessing.execute import execute

def _ants_registration_outputs(prefix):
    outputs = {
        'affine': prefix + "0GenericAffine.mat",
        'warp': prefix + "1Warp.nii.gz",
        'registered': prefix + "Warped.nii.gz",
        'invwarp': prefix + "1InverseWarp.nii.gz",
        'invwarped': prefix + "InverseWarped.nii.gz",
        'fullwarp': prefix + '1FullWarp.nii.gz'
        }
    return outputs

def _cleanup(OUTNAMES):
     # cleanup
    # this is removing all the temporary images created in the PREFIX directory
    # the user-specified outputs should already be moved
    print()
    print('>>> Removing temporary files.')
    print('- - -')
    for key, value in OUTNAMES.items():
        msg = 'NOT FOUND'
        if os.path.exists(value):
            msg = 'REMOVED'
            os.remove(value)
        print(f'  - "{key}": {value} [{msg}]')
    print('- - -')

def _copy_outputs(prefix, out_registered=None, out_affine=None,
                  out_warp=None):
    
    prefixdir = os.path.dirname(prefix)

    print()
    print('Files in temporary directory:')
    for file in os.listdir(prefixdir):
        print(f'  - {file}')

    outputs = _ants_registration_outputs(prefix)
    affine  = outputs['affine']
    warp = outputs['warp']
    registered = outputs['registered']

    def _verbose_copy(src, dest):
        print()
        print('COPYFILE')
        print('Source: ', src)
        print('Destination: ', dest)
        if not os.path.exists(src):
            print('!! FAILURE: Source not found.')
        else:
            shutil.copy(src, dest)
            print('!! SUCCESS.')

    if out_affine is not None:
        _verbose_copy(affine, out_affine)

    if out_warp is not None:
        _verbose_copy(warp, out_warp)

    if out_registered is not None:
        _verbose_copy(registered, out_registered)

def apply_transform(moving, fixed, warp, output):

    command = [
        'antsApplyTransforms',
        '-d', '3',
        '-i', moving,
        '-r', fixed,
        '-t', warp,
        '-o', output,
        '-v', '1']

    execute(command)

def create_jacobian_determinant_image(fullwarp, out_jacobian):

    command = [
        'CreateJacobianDeterminantImage',
        '3',
        fullwarp,
        out_jacobian
        ]
    execute(command)

def create_fullwarp_image(moving, reference, affine, warp, out_fullwarp):

    command = [
        'antsApplyTransforms',
        '-d', '3',
        '-i', moving,
        '-r', reference,
        '-t', warp, affine,
        '-o', f'[{out_fullwarp},1]',
        '-v', '1']

    execute(command)

def registration_mni_pipeline(brain, mni_brain=None, quick=True, transformation='s',
                              out_registered=None, out_affine=None, out_warp=None,
                              out_fullwarp=None, out_jacobian=None):

    # determine transformation type
    if transformation in ['t', 'r', 'a']:
        is_linear_transformation = True
    elif transformation in ['s', 'sr', 'so']:
        is_linear_transformation = False
    else:
        raise ValueError(f'Transformation type {transformation} not recognized by this pipeline.')
    
    make_full_warp = (out_fullwarp or out_jacobian) and not is_linear_transformation

    # determine if anything needs to be done
    outputs = [out_registered, out_affine, out_warp, out_fullwarp]
    if all(x is None for x in outputs):
        warnings.warn(RuntimeWarning('MRI registration: no outputs selected, exiting!'))
        return

    # set paths
    ANTSPATH = get('ants')
    REFERENCE = mni_brain if mni_brain is not None else get('mni152_brain')

    # files are created in the directory of the input brain,
    # and then moved to their destination
    WORKINGDIR = os.path.dirname(os.path.abspath(brain))
    PREFIX = os.path.join(WORKINGDIR, '_temp_output')
    OUTNAMES = _ants_registration_outputs(PREFIX)

    # MAIN
    # # # # # #

    # REGISTRATION

    basecommand = 'antsRegistrationSyNQuick.sh' if quick else 'antsRegistrationSyN.sh'
    fullcommand = os.path.join(ANTSPATH, basecommand)
    command = [
        fullcommand,
        '-d', '3',
        '-m', brain,
        '-f', REFERENCE,
        '-o', PREFIX,
        '-t', transformation,
        '-j', '0',
        '-n', '1'
        ]

    print()
    print(Fore.BLUE + Style.BRIGHT + 'MRI Registration')
    print('~~~~~'  + Style.RESET_ALL)

    # run
    print()
    print('>>> Initiating registration with following command:')
    print('    ' + Fore.YELLOW + ' '.join(command) + Style.RESET_ALL)
    print('- - -')
    execute(command)
    print('- - -')

    print()
    print('>>> Copying outputs to selected destinations. ')
    _copy_outputs(PREFIX, out_registered=out_registered,
                  out_warp=out_warp, out_affine=out_affine)
    
    # NONLINEAR WARP EXTRA STEPS

    # we can exit if the fullwarp/jacobian images are not being created
    if not make_full_warp:
        _cleanup(OUTNAMES=OUTNAMES)
        print('Completed!')
        return

    # create concatenated warp image
    # if this is not being saved, then `out_fullwarp` is set to None
    # so we create a temporary file that will be deleted on completion
    if out_fullwarp is None:
        out_fullwarp = OUTNAMES['fullwarp']

    if out_fullwarp is not None:
        print()
        print('>>> Creating concatenated transform file.')
        print('- - -')
        create_fullwarp_image(brain, REFERENCE, affine=OUTNAMES['affine'],
                            warp=OUTNAMES['warp'], out_fullwarp=out_fullwarp)
        print('- - -')

    if out_jacobian is not None:
        # create jacobian determinant image
        print()
        print('>>> Creating Jacobian determinant image.')
        print('- - -')
        create_jacobian_determinant_image(fullwarp=out_fullwarp,
                                          out_jacobian=out_jacobian)
        print('- - -')

    # remove temporary files
    _cleanup(OUTNAMES=OUTNAMES)

    print('Completed!')

