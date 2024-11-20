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
        'invwarp': prefix + "1InverseWarped.nii.gz",
        'fullwarp': prefix + '1FullWarp.nii.gz'
        }
    return outputs

def _copy_outputs(prefix, out_registered=None, out_affine=None,
                  out_warp=None):

    outputs = _ants_registration_outputs(prefix)
    affine  = outputs['affine']
    warp = outputs['warp']
    registered = outputs['registered']

    if os.path.isfile(affine) and out_affine is not None:
        shutil.move(affine, out_affine)

    if os.path.isfile(warp) and out_warp is not None:
        shutil.move(warp, out_warp)

    if os.path.isfile(registered) and out_registered is not None:
        shutil.move(registered, out_registered)

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

    make_full_warp = out_fullwarp or out_jacobian
    outputs = [out_registered, out_affine, out_warp, out_fullwarp]
    if all(x is None for x in outputs):
        warnings.warn(RuntimeWarning('MRI registration: no outputs selected, exiting!'))
        return

    ANTSPATH = get('ants')
    REFERENCE = mni_brain if mni_brain is not None else get('mni152_brain')

    # files are created in the directory of the input brain,
    # and then moved to their destination
    WORKINGDIR = os.path.dirname(os.path.abspath(brain))
    PREFIX = os.path.join(WORKINGDIR, '_temp_output')
    OUTNAMES = _ants_registration_outputs(PREFIX)

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

    # we can exit if the fullwarp/jacobian images are not being created
    if not make_full_warp:
        print('Completed!')
        return

    # create concatenated warp image
    # if this is not being saved, then `out_fullwarp` is set to None
    # so we create a temporary file that will be deleted on completion
    if out_fullwarp is None:
        out_fullwarp = OUTNAMES['fullwarp']

    print()
    print('>>> Creating concatenated transform file.')
    print('- - -')
    create_fullwarp_image(brain, REFERENCE, affine=OUTNAMES['affine'],
                          warp=OUTNAMES['warp'], out_fullwarp=out_fullwarp)
    print('- - -')

    # create jacobian determinant image
    print()
    print('>>> Creating Jacobian determinant image.')
    print('- - -')
    create_jacobian_determinant_image(fullwarp=out_fullwarp,
                                      out_jacobian=out_jacobian)
    print('- - -')

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

