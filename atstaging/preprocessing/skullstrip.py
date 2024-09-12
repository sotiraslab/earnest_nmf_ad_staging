
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
