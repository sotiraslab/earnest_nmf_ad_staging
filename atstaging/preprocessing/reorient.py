# -*- coding: utf-8 -*-
"""
Created on Wed Sep  4 14:10:11 2024

@author: earne
"""

import nibabel as nib

def _invert_orientation(code):

    '''Get the inverted version of an orientation code.'''

    # It seems that nibabel and AFNI call the same orientation
    # by different names - one refers to the ascending direction
    # and one to the descending direction of each dimension.
    # E.g. a file with "RPI" orientation reported by AFNI will
    # have "LAS" orientation on nibabel.  This function assumes
    # that you want what AFNI reports from `3dinfo`, and thus
    # does this conversion step to get expected output.

    convert = {'L':'R',
               'R':'L',
               'A':'P',
               'P':'A',
               'S':'I',
               'I':'S'}
    trans = {ord(k):v for k, v in convert.items()}
    code = code.translate(trans)
    return code

def reorient_image(inpath, orientation, outpath=None):
    '''
    Reorient a 3D NIFTI image.  Note the orientations
    follow AFNI convention, so the specified target
    orientation should match what is returned by checking
    the orientation with `3dinfo`.

    Parameters
    ----------
    inpath : str
        Path to input image.
    orientation : str
        3-letter orientation code (capitalized), e.g. 'RPI'.
    outpath : str
        Path to output image.  If not passed, original image is
        overwritten in place.

    Returns
    -------
    None.

    '''

    outpath = inpath if outpath is None else outpath
    orientation = _invert_orientation(orientation)
    nii = nib.load(inpath)

    # https://github.com/nipy/nibabel/issues/1010
    orig_orient = nib.io_orientation(nii.affine)
    targ_orient = nib.orientations.axcodes2ornt(orientation)
    transform = nib.orientations.ornt_transform(orig_orient, targ_orient)

    newnii = nii.as_reoriented(transform)
    nib.save(newnii, outpath)