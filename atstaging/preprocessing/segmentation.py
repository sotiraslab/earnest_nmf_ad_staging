
import glob
import os

import nibabel as nib
import numpy as np
import pandas as pd

from .execute import execute
from atstaging.config import get

def compute_regional_statistics_MUSE(img, segmentaion):
    img = nib.load(img)
    seg = nib.load(segmentaion)
    voxel_dims = (img.header["pixdim"])[1:4]
    voxel_volume = np.prod(voxel_dims)
    img_data = img.get_fdata()
    seg_data = seg.get_fdata()
    labels, sizes = np.unique(seg_data, return_counts=True)
    print(f' ** Found {len(labels)} labels in segmentation:')
    print(f' **     {[float(i) for i in labels]}')
    rows = []
    for label, size in zip(labels, sizes):
        mask = seg_data == label
        region = img_data[mask]
        row = {}
        row['ROI'] = label
        row['MUSEVoxels'] = size
        row['MUSEVolume'] = size * voxel_volume
        row['MUSEMinimum'] = region.min()
        row['MUSEMaximum'] = region.max()
        row['MUSEAverage'] = region.mean()
        rows.append(row)

    muse = load_muse_roi_table_cleaned()
    df = pd.DataFrame(rows)
    output = muse.merge(df, how='left', on='ROI')
    return output

def derive_brainmask_from_MUSE(segmentation, out_brainmask=None, out_brain=None, in_img=None):

    if out_brain is None and out_brainmask is None:
        raise ValueError('At least one output (`out_brain` or `out_brainmask`) must be provided.')

    if out_brain and in_img is None:
        raise ValueError(
            'When requested to save brain (`out_brain`), user must provide an '
            'input T1 or brain image (`in_img`)')

    seg = nib.load(segmentation)
    seg_data = seg.get_fdata()
    isbrain_mask = (seg_data != 0).astype(float)

    if out_brainmask:
        brainmask = nib.Nifti1Image(dataobj=isbrain_mask, affine=seg.affine)
        nib.save(brainmask, out_brainmask)

    if out_brain:
        t1 = nib.load(in_img)
        t1_data = t1.get_fdata()
        t1_data_mask_applied = np.where(isbrain_mask == 1., t1_data, 0.)
        brain = nib.Nifti1Image(dataobj=t1_data_mask_applied, affine=seg.affine)
        nib.save(brain, out_brain)
    
def get_mask_volume(inpath, binarize=True, background_value=0.):
    nii = nib.load(inpath)
    voxel_dims = (nii.header["pixdim"])[1:4]
    voxel_volume = np.prod(voxel_dims)
    data = nii.get_fdata()
    is_binary = np.all((data == 0) | (data == 1))
    if not is_binary and not binarize:
        raise RuntimeError('Cannot compute mask volume for a non-binary image with this function. '
                           'Either set `binarize=True` or supply a different image.')
    if not is_binary and binarize:
        data = np.where(data == background_value, 0., 1.)
    mask_count = data.sum()
    mask_volume = mask_count * voxel_volume
    return mask_volume

def get_muse_volumes(inpath, icv_mask=None):
    muse = load_muse_roi_table_cleaned()
    volumes = get_segementation_volumes(inpath)
    muse['Volume'] = muse['ROI'].map(volumes)
    if icv_mask is not None:
        muse['ICV'] = get_mask_volume(icv_mask)
        muse['NormalizedVolume'] = muse['Volume'] / muse['ICV']
    return muse

def get_segementation_volumes(inpath):
    nii = nib.load(inpath)
    data = nii.get_fdata()
    voxel_dims = (nii.header["pixdim"])[1:4]
    voxel_volume = np.prod(voxel_dims)
    labels, counts = np.unique(data, return_counts=True)
    volumes = counts * voxel_volume
    return dict(zip(labels.astype(int).tolist(), volumes.astype(float).tolist()))

def load_muse_roi_table():
    deepmrseg_directory = os.path.join(os.environ["HOME"], '.deepmrseg')
    find_roi_csv = glob.glob('trained_models/muse/*/LPS/configs/ROI_Indices.csv', root_dir=deepmrseg_directory)
    if not find_roi_csv:
        raise FileNotFoundError(f"Cannot find ROI_Indices.csv file under {deepmrseg_directory}.")
    file = os.path.join(deepmrseg_directory, find_roi_csv[0])
    df = pd.read_csv(file)
    return df

def load_muse_roi_table_cleaned():
    df = load_muse_roi_table()
    df['TissueType'] = df['Tissue_Type']
    df['FullName'] = df['Name']
    df['Name'] = df['FullName'].str.lower().str.replace(' ', '_').str.replace('_+', '_', regex=True)
    df['IsBrain'] = df['Brain?'].eq('Brain')
    df['IsCerebellum'] = df['Lobe_Name'].eq('Cerebellum')
    df['Hemisphere'] = df['Hemisphere'].str.lower()
    out = df[['ROI', 'FullName', 'Name', 'Hemisphere', 'TissueType', 'IsBrain', 'IsCerebellum']].copy()
    return out
    
def run_deepmrseg_muse(inpath, outpath):

    command = [
        'conda',
        'run',
        '--name', get('deepmrseg_env'),
        '--live-stream',
        'deepmrseg_apply',
        '--task', 'muse',
        '--inImg', inpath,
        '--outImg', outpath
    ]

    execute(command)

def segmentation_pipeline(brain, out_segmentation, out_volumes=None, out_petreference=None,
                          rerun_segmentation=False, out_brainmask=None, out_brain=None):

    print('* -------------- *')
    print('|  Segmentation  |')
    print('* -------------- *')
    print()
    print(f'Input image: {brain}')

    print()
    print('>>> Applying DeepMRSeg::MUSE for segmentation')
    
    if os.path.exists(out_segmentation) and not rerun_segmentation:
        print(f'>>> Existing segmentation at {out_segmentation}; not rerunning.')
    else:
        print('--- BEGIN ---')
        run_deepmrseg_muse(brain, outpath=out_segmentation)
        print('---  END  ---')

    if out_volumes:
        print('>>> Getting volumes for segmentation ROIS...')
        df = get_muse_volumes(out_segmentation, icv_mask=brain)
        df.to_csv(out_volumes, index=False)
        print('>>> Done.')

    if out_petreference:
        print('>>> Getting PET cerebellar GM reference mask.')
        nii = nib.load(out_segmentation)
        data = nii.get_fdata()
        maskdata = np.where((data == 38) | (data == 39), 1., 0.)
        mask = nib.Nifti1Image(dataobj=maskdata, affine=nii.affine, dtype=np.int16)
        nib.save(mask, out_petreference)
        print('>>> Done.')

    if out_brain is not None or out_brainmask is not None:
        print('>>> Deriving brain mask image(s) from MUSE segmentation.')
        derive_brainmask_from_MUSE(segmentation=out_segmentation, out_brainmask=out_brainmask, out_brain=out_brain, in_img=brain)
        print('>>> Done.')
