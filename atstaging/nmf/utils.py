
import os
import pickle

import h5py
import nibabel as nib
from nifti_overlay import NiftiOverlay
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from skimage.measure import block_reduce
from sklearn.metrics import adjusted_rand_score, r2_score

from atstaging.config import get

def assess_solution_similarity(mat1, mat2):

    W1, _ = load_results(mat1)
    W2, _ = load_results(mat2)

    W1_unit = W1 / np.sqrt(np.sum(W1 ** 2, axis=0))
    W2_unit = W2 / np.sqrt(np.sum(W2 ** 2, axis=0))

    dist = cdist(W1_unit.T, W2_unit.T)
    ind1, ind2 = linear_sum_assignment(dist)

    results = {}
    results['match_index_1'] = ind1
    results['match_index_2'] = ind2

    # Mean/median inner product
    inner_products = []

    for i, j in zip(ind1, ind2):
        cmp1 = W1_unit[:, i]
        cmp2 = W2_unit[:, j]
        inner_products.append(np.dot(cmp1, cmp2))

    results['inner_products'] = inner_products
    results['mean_inner_product'] = np.mean(inner_products)
    results['median_inner_product'] = np.median(inner_products)

    # ARI
    zeroW1 = np.all(W1 == 0, axis=1)
    zeroW2 = np.all(W2 == 0, axis=1)
    zeroBoth = zeroW1 & zeroW2
    W1_wta = W1_unit.argmax(axis=1)
    W2_wta = W2_unit.argmax(axis=1)
    ari = adjusted_rand_score(W1_wta, W2_wta)
    ari_nonzero = adjusted_rand_score(W1_wta[~zeroBoth], W2_wta[~zeroBoth])

    results['adjusted_rand_index'] = ari
    results['adjusted_rand_index_nonzero'] = ari_nonzero

    # Correlation
    correlations = []

    for i, j in zip(ind1, ind2):
        cmp1 = W1_unit[~zeroBoth, i]
        cmp2 = W2_unit[~zeroBoth, j]
        correlations.append(r2_score(cmp1, cmp2))

    results['pearson_correlations'] = correlations
    results['mean_person_correlation'] = np.mean(correlations) 
    results['median_pearson_correlation'] = np.median(correlations)

    return results

def load_image_with_downsample(path, downsample_factor, order='F'):
        
    nii = nib.load(path)
    data3d = nii.get_fdata()
    
    if downsample_factor == 1:
        return data3d.flatten(order=order)
    else:
        reduce = block_reduce(data3d, block_size=downsample_factor, func=np.mean)
        return reduce.flatten(order=order)
        
def load_results_with_downsample(path_mat, voxel_dim, downsample_factor=1, order='F', dtype='single', transpose=True):
    
    dtype = np.dtype(dtype)
    
    W, H = load_results(path_mat, transpose=True)
        
    # no downsampling
    if downsample_factor == 1:
        return W, H
    
    # downsampling
    m_orig, k = W.shape
    
    example1d = W[:, 0]
    example3d = np.reshape(example1d, shape=voxel_dim, order=order)
    reduce = block_reduce(example3d, block_size=downsample_factor, func=np.mean)
    flatten = reduce.flatten(order=order)
    m_final = len(flatten)
    
    W_final = np.zeros((m_final, k), dtype=dtype)
    for i in range(k):
        compoment1d = W[:, i]
        component3d = np.reshape(compoment1d, shape=voxel_dim, order=order)
        reduce = block_reduce(component3d, block_size=downsample_factor, func=np.mean)
        flatten = reduce.flatten(order=order)
        W_final[:, i] = flatten

    # result is already transposed;
    # if transpose not requested, transpose back
    if not transpose:
            W_final = W_final.T
            H = H.T

    return W_final, H

def load_nmf_runner(path):

    # if a folder is passed, assume it is the run output directory
    if os.path.isdir(path):
        path = os.path.join(path, 'NMFRunner.pickle')

    with open(path, 'rb') as file:
        runner = pickle.load(file)

    return runner

def load_results(mat, transpose=True):
    with h5py.File(mat, 'r') as f:
        W = np.array(f['B'])
        H = np.array(f['C'])

    if transpose:
        W = W.T
        H = H.T

    return W, H

def plot_component(mat, i):

    mni_path = get('mni152_brain')
    mni = nib.load(mni_path)
    mni_affine = mni.affine
    mni_shape = mni.shape

    W, _ = load_results(mat, transpose=True)
    data1d = W[:, i]
    data3d = np.reshape(data1d, mni_shape, order='F')
    datanii = nib.Nifti1Image(data3d, affine=mni_affine)
    overlay = NiftiOverlay(dpi=150, nslices=5, min_all=0.3, max_all=0.7)
    overlay.add_anat(mni_path)
    overlay.add_anat(datanii, color='magma', alpha=.7)
    overlay.plot()

    return overlay.fig

def plot_component_over_pet_average(mat, i, path_pet, show_plot=True, vmin_pet=None, vmax_pet=None):
    mni_path = get('mni152_brain')
    mni = nib.load(mni_path)
    mni_affine = mni.affine
    mni_shape = mni.shape

    W, _ = load_results(mat, transpose=True)
    data1d = W[:, i]
    data3d = np.reshape(data1d, mni_shape, order='F')
    datanii = nib.Nifti1Image(data3d, affine=mni_affine)

    overlay = NiftiOverlay()
    overlay.add_anat(path_pet, color='gray', vmin=vmin_pet, vmax=vmax_pet)
    overlay.add_anat(datanii, color='magma', alpha=.5, drop_zero=True)

    if show_plot:
        overlay.plot()

    return overlay

