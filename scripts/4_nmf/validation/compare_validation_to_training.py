
# IMPORTS
import os

import matplotlib.pyplot as plt
import numpy as np

from atstaging.config import get, set_config
from atstaging.nmf.utils import load_results
from atstaging.plotting import set_font_properties

set_config('main')

# HELPER FUNCTION
def nmf_similarity_heatmap(pathA, indicesA, pathB, indicesB, ax=None, savepath=None):

    # load the components
    WA, _ = load_results(pathA)
    WB, _ = load_results(pathB)

    WA = WA[:, indicesA]
    WB = WB[:, indicesB]

    WA_unit = WA / np.sqrt(np.sum(WA ** 2, axis=0))
    WB_unit = WB / np.sqrt(np.sum(WB ** 2, axis=0))

    # compare the similarity
    nA = len(indicesA)
    nB = len(indicesB)
    sim = np.zeros(shape=[nA, nB])

    for i in range(nA):
        for j in range(nB):
            cmpA = WA_unit[:, i]
            cmpB = WB_unit[:, j]
            sim[i, j] = np.dot(cmpA, cmpB)

    if ax is None:
        ax = plt.gca()

    ax.imshow(sim, vmin=0, vmax=1, cmap='viridis')
    ax.set_yticks(range(nA))
    ax.set_yticklabels([i+1 for i in indicesA])
    ax.set_xticks(range(nB))
    ax.set_xticklabels([i+1 for i in indicesB])
    ax.tick_params(axis='both', which='both',length=0)

    for i in range(nA):
        for j in range(nB):
            t = round(sim[i, j], 2)
            ax.text(j, i, t, ha='center', va='center')

    if savepath is not None:
        plt.savefig(savepath, dpi=300)

# PARAMETERS
# The indices pretty much need to be manually defined by inspection of components
# to pull out the gray matter ones

output_directory = get('output_directory')
idir = os.path.join(output_directory, 'images')

# Training
training_amy_path = os.path.join(idir, 'amyloid_components', 'rank11', 'ResultsExtractBases.mat')
training_amy_indices = [1, 2, 5, 6]
training_tau_path = os.path.join(idir, 'tau_components', 'rank12', 'ResultsExtractBases.mat')
training_tau_indices = [1, 3, 4, 6, 9, 10, 11]

# Validation A
valA_amy_path = os.path.join(idir, 'validationA_amyloid_components', 'rank11', 'ResultsExtractBases.mat')
valA_amy_indices = [1, 2, 3, 6, 7]
valA_tau_path = os.path.join(idir, 'validationA_tau_components', 'rank12', 'ResultsExtractBases.mat')
valA_tau_indices = [1, 2, 4, 5, 6, 7, 9, 10]

# Validation B
valB_amy_path = os.path.join(idir, 'validationB_amyloid_components', 'rank11', 'ResultsExtractBases.mat')
valB_amy_indices = [1,5,6]
valB_tau_path = os.path.join(idir, 'validationB_tau_components', 'rank12', 'ResultsExtractBases.mat')
valB_tau_indices = [1,2,7,9,10]

# Validation C
valC_amy_path = os.path.join(idir, 'validationC_amyloid_components', 'rank11', 'ResultsExtractBases.mat')
valC_amy_indices = [1,3,5,8]
valC_tau_path = os.path.join(idir, 'validationC_tau_components', 'rank12', 'ResultsExtractBases.mat')
valC_tau_indices = [0,1,3,5,8,9]

# Validation All
valAll_amy_path = os.path.join(idir, 'validationAll_amyloid_components', 'rank11', 'ResultsExtractBases.mat')
valAll_amy_indices = [1, 4, 5]
valAll_tau_path = os.path.join(idir, 'validationAll_tau_components', 'rank12', 'ResultsExtractBases.mat')
valAll_tau_indices = [0, 4, 5, 6, 8, 10]

# Collect into iterables
array_training_paths = [training_amy_path, training_tau_path]
array_training_indices = [training_amy_indices, training_tau_indices]

array_val_path_AMY = [valA_amy_path, valB_amy_path, valC_amy_path, valAll_amy_path]
array_val_path_TAU = [valA_tau_path, valB_tau_path, valC_tau_path, valAll_tau_path]
array_val_indices_AMY = [valA_amy_indices, valB_amy_indices, valC_amy_indices, valAll_amy_indices]
array_val_indices_TAU = [valA_tau_indices, valB_tau_indices, valC_tau_indices, valAll_tau_indices]

# MAIN

savedir = os.path.join(output_directory, 'plots', 'validation_nmf_similarity')
os.makedirs(savedir, exist_ok=True)

# Valdation - amyloid
set_font_properties(8)
plt.figure(figsize=(2, 3), dpi=300)
nmf_similarity_heatmap(
    training_amy_path, training_amy_indices,
    valAll_amy_path, valAll_amy_indices,
    )
plt.tight_layout()
plt.savefig(os.path.join(savedir, 'amyloid_all.svg'))

# Validation - tau
set_font_properties(7)
plt.figure(figsize=(2, 3), dpi=300)
nmf_similarity_heatmap(
    training_tau_path, training_tau_indices,
    valAll_tau_path, valAll_tau_indices,
    )
plt.tight_layout()
plt.savefig(os.path.join(savedir, 'tau_all.svg'))

# Colorbar


# # Amyloid
# fig, axes = plt.subplots(nrows=1, ncols=4, figsize=(12, 4), dpi=300, sharey=True,
#                          width_ratios=[len(x) for x in array_val_indices_AMY])

# for i in range(4):
#     ax = axes[i]

#     pathA = training_amy_path
#     indicesA = training_amy_indices

#     pathB = array_val_path_AMY[i]
#     indicesB = array_val_indices_AMY[i]

#     print(f'panel {i}...')
#     nmf_similarity_heatmap(pathA, indicesA, pathB, indicesB, ax=ax)

# plt.tight_layout()
# plt.savefig(os.path.join(savedir, 'amyloid_compare.png'))

# # Tau
# fig, axes = plt.subplots(nrows=1, ncols=4, figsize=(20, 20/3), dpi=300, sharey=True,
#                          width_ratios=[len(x) for x in array_val_indices_TAU])

# for i in range(4):
#     ax = axes[i]

#     pathA = training_tau_path
#     indicesA = training_tau_indices

#     pathB = array_val_path_TAU[i]
#     indicesB = array_val_indices_TAU[i]

#     print(f'panel {i}...')
#     nmf_similarity_heatmap(pathA, indicesA, pathB, indicesB, ax=ax)

# plt.tight_layout()
# plt.savefig(os.path.join(savedir, 'tau_compare.png'))
