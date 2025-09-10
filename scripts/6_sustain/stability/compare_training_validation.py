import os

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

from atstaging.config import get, set_config
from atstaging.plotting import set_font_properties, staging_colors
from atstaging.outputs import load_subtyped_data
from atstaging.sustain import SustainManager

# setup
set_config('main')
root_output = get('output_directory')
set_font_properties()

odir = os.path.join(root_output, 'plots', 'sustain', 'stability')
os.makedirs(odir, exist_ok=True)

# Ordering Similarity
# ==================

# load models
t_sustain = SustainManager(os.path.join(root_output, 'sustain', 'training'))
v_sustain = SustainManager(os.path.join(root_output, 'sustain', 'validation'))

t_sequence, t_freq = t_sustain.sustain.combine_cross_validated_sequences(N_folds=10, N_subtypes=3, plot=False)
v_sequence, v_freq = v_sustain.sustain.combine_cross_validated_sequences(N_folds=10, N_subtypes=3, plot=False)

# get the order for plotting subtypes
# basically trying to establish which sutypes in training match to the validation ones
_, t_subtype_order = t_sustain.map_subtype_indexing(n_subtypes=3, verbose=False)

# this is basically reimplementing map_subtype_indexing()
# but using the validation sequence instead of the training
v_sequence_avg = v_sequence.mean(axis=2)
dist = cdist(t_sustain.frequency_based_biomarker_ordering(n_subtypes=3), v_sequence_avg)
_, v_subtype_order = linear_sum_assignment(dist)

# helper func
def cosine_similarity(x, y):
    num = np.dot(x, y)
    den = np.linalg.norm(x) * np.linalg.norm(y)
    return (num/den)

# calculate observed mean (cosine) similarity of the positional biomarker orderings between training & validation
biomarker_indices = list(range(t_sustain.n_biomarkers))

observed_similarity = np.zeros((3, 3, t_sustain.n_biomarkers))

for i in biomarker_indices:
    t_prob_position = (t_sequence == i).mean(axis=2)
    v_prob_position = (v_sequence == i).mean(axis=2)
    for row, j in enumerate(t_subtype_order):
        for col, k in enumerate(v_subtype_order):
            observed_similarity [row, col, i] = cosine_similarity(t_prob_position[j, :], v_prob_position[k, :])

observed_similarity_average = observed_similarity.mean(axis=2)
print('Observed similarity:')
print(observed_similarity_average)

# permutations to estimate null distribution
np.random.seed(42)

biomarker_indices = list(range(t_sustain.n_biomarkers))
repeats = 500
    
null_similarity = np.zeros((3, 3, t_sustain.n_biomarkers, repeats))

for i in biomarker_indices:
    t_prob_position = (t_sequence == i).mean(axis=2)
    v_prob_position = (v_sequence == i).mean(axis=2)
    for r in range(repeats):
        for row, j in enumerate(t_subtype_order):
            for col, k in enumerate(v_subtype_order):
                null_similarity[row, col, i, r] = cosine_similarity(t_prob_position[j, :], np.random.permutation(v_prob_position[k, :]))

null_similarity_average = null_similarity.mean(axis=2)
p_values = (null_similarity_average >= observed_similarity_average.reshape((3, 3, 1))).mean(axis=2)
print('\np-values:')
print(p_values)

# plot
fig = plt.figure()
plt.imshow(observed_similarity_average, cmap='Blues', vmin=0, vmax=1)
plt.xticks([0, 1, 2], ['S1', 'S2', 'S3'])
plt.yticks([0, 1, 2], ['S1', 'S2', 'S3'])
plt.ylabel('Training subtypes')
plt.xlabel('Validation subtypes')

for i in t_subtype_order:
    for j in v_subtype_order:
        sim = round(observed_similarity_average[i, j], 2)
        pval = round(p_values[i, j], 3)
        stars = pd.cut([pval], [-np.inf, 0.001, 0.01, 0.05, np.inf], right=False, labels=['***', '**', '*', ''])[0]
        color = 'white' if sim > 0.5 else 'black'
        weight = 'bold' if pval<0.05 else 'normal'

        text = f'{sim}{stars}'
        plt.text(j, i, text, ha='center', va='center', color=color, fontweight=weight)

        ptext = f'p={pval}' if pval>= 0.001 else 'p<0.001'
        plt.text(j, i+0.2, ptext, ha='center', va='center', color=color, fontsize=10)

cbar = plt.colorbar()
cbar.ax.set_ylabel('Cosine similarity', rotation=270)
cbar.ax.get_yaxis().labelpad = 15

plt.savefig(os.path.join(odir, 'ordering_similarity_heatmap.svg'))

# SUVR Similarity
# ===============

training = load_subtyped_data('training')
validation = load_subtyped_data('validation')

wcols = list(training.columns[training.columns.str.endswith('WScore')])
wcols_amy = list(training.columns[training.columns.str.contains('PAC.*WScore')])
wcols_tau = list(training.columns[training.columns.str.contains('PTC.*WScore')])

scolors = staging_colors()
amycmap = LinearSegmentedColormap.from_list('amyloid', [(0., 'white'), (1., scolors['A2T0'])])
taucmap = LinearSegmentedColormap.from_list('tau', [(0., 'white'), (1., scolors['A2T4'])])

def avg_pathology_similarity(training, validation, cols, cmap='viridis', hicolor='black', locolor='white'):
        
    tdata = training.loc[:, ['TrainingMLSubtype'] + list(cols)]
    vdata = validation.loc[:, ['ValidationMLSubtype'] + list(cols)]

    tmeans = tdata.groupby('TrainingMLSubtype').mean()
    vmeans = vdata.groupby('ValidationMLSubtype').mean()

    corrmat = np.zeros((3, 3))
    
    for i in range(3):
        for j in range(3):
            corr = pearsonr(tmeans.iloc[i, :], vmeans.iloc[j, :])
            corrmat[i, j] = corr.statistic

    fig = plt.figure()
    plt.imshow(corrmat, vmin=0, vmax=1, cmap=cmap)
    plt.xticks([0, 1, 2], ['S1', 'S2', 'S3'])
    plt.yticks([0, 1, 2], ['S1', 'S2', 'S3'])
    plt.ylabel('Training subtypes')
    plt.xlabel('Validation subtypes')

    for i in range(3):
        for j in range(3):
            r = corrmat[i, j]
            color = hicolor if r > 0.5 else locolor
            plt.text(j, i, round(r, 2), ha='center', va='center', color=color)

    cbar = plt.colorbar()
    cbar.ax.set_ylabel('Pearson correlation', rotation=270)
    cbar.ax.get_yaxis().labelpad = 15
    
    return fig

_ = avg_pathology_similarity(training, validation, wcols, cmap='viridis')
plt.savefig(os.path.join(odir, 'suvr_similarity_all.svg'))

_ = avg_pathology_similarity(training, validation, wcols_amy, cmap=amycmap, hicolor='white', locolor='black')
plt.savefig(os.path.join(odir, 'suvr_similarity_amyloid.svg'))

_ = avg_pathology_similarity(training, validation, wcols_tau, cmap=taucmap, hicolor='white', locolor='black')
plt.savefig(os.path.join(odir, 'suvr_similarity_tau.svg'))