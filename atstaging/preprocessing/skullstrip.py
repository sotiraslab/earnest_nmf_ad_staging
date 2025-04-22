
import nibabel as nib
import numpy as np

from .execute import execute
from atstaging.config import get

def apply_brainmask(t1, brainmask, outpath):
    t1 = nib.load(t1)
    brainmask = nib.load(brainmask)

    t1data = t1.get_fdata()
    maskdata = brainmask.get_fdata()
    masked = np.where(maskdata == 1, t1data, 0)

    output = nib.Nifti1Image(masked, affine=t1.affine, header=t1.header)
    nib.save(output, outpath)

def get_skullstrip_method(key):
    key = key.lower()
    if key == 'hdbet' or key == 'hd-bet':
        return run_hdbet
    elif key == 'dlicv':
        return run_deepmrseg_dlicv
    else:
        raise ValueError('`key` must be "DLICV" or "HDBET".')

def run_hdbet(inpath, outpath):

    command = [
        'conda',
        'run',
        '--name', get('hdbet_env'),
        '--live-stream',
        'hd-bet',
        '-i', inpath,
        '-o', outpath,
        '-device', 'cpu',
        '--disable_tta'
    ]

    execute(command)

    # hdbet saves brain
    # convert it to mask here to make it consistent with run_deepmrseg_dlicv
    nii = nib.load(outpath)
    data = nii.get_fdata()
    mask = np.where(data != 0, 1., 0.)
    result_nii = nib.Nifti1Image(dataobj=mask, affine=nii.affine)
    nib.save(result_nii, outpath)

def run_deepmrseg_dlicv(inpath, outpath):

    command = [
        'conda',
        'run',
        '--name', get('deepmrseg_env'),
        '--live-stream',
        'deepmrseg_apply',
        '--task', 'dlicv',
        '--inImg', inpath,
        '--outImg', outpath
    ]

    execute(command)
