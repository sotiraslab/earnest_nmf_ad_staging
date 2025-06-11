# IMPORTS
import os

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from atstaging.config import get, set_config
from atstaging.outputs import load_split

# PARAMETERS
N = 5000
seed = 42

np.random.seed(seed)

# HELPERS
def longitudinal_permutation_test(flow, N):
    flow = flow.copy()

    flow['label_from'] = flow['label_from'].replace({'NS':np.nan}).astype(float)
    flow['label_to'] = flow['label_to'].replace({'NS':np.nan}).astype(float)
    label_from = flow['label_from'].to_numpy()
    label_to = flow['label_to'].to_numpy()

    observed = stagestat(label_from, label_to)

    null = []

    for n in range(N):
        swap = np.random.rand(len(flow)) < 0.5
        before = np.where(swap, label_to, label_from)
        after = np.where(swap, label_from, label_to)
        null.append(stagestat(before, after))

    null = np.array(null)
    p = (null >= observed).mean()

    plt.rcParams.update({'font.family':'arial',
                         'font.size':20})

    fig, ax = plt.subplots(figsize=(8, 6))

    ax.hist(null, edgecolor='k', facecolor='dodgerblue', label='null',
            linewidth=3)
    ax.axvline(observed, color='red', label='observed', lw=3)
    ax.set_ylabel('Frequency')
    ax.set_xlabel('Statistic')
    ax.set_title(f'p={p}')

    ax.legend()

    return {'observed': observed, 'null': null, 'p': p, 'figure': fig}

def longitudinal_transitions_heatmap(flow, ax=None, ticklabels=None):

    # create heatmap data
    labels = sorted(flow['label_to'].unique(), key = lambda x: (not x.isnumeric(), x))
    transitions = flow.groupby(['label_from', 'label_to'])['subject'].count()
    new_index = pd.MultiIndex.from_product([labels, labels])
    transitions = transitions.reindex(new_index).reset_index()
    transitions.columns = ['label_from', 'label_to', 'n']
    transitions['n'] = transitions['n'].fillna(0)
    transitions['perc'] = transitions.groupby('label_from')['n'].transform(lambda x: (x / x.sum()) * 100).fillna(0)

    tbl = transitions.pivot(index='label_from', columns='label_to', values='perc')

    gs = plt.GridSpec(nrows=1, ncols=2, width_ratios=[20, 1], wspace=.2)

    fig = plt.figure(figsize=(12, 11))
    ax = fig.add_subplot(gs[0])
    c1 = fig.add_subplot(gs[1])

    ax.set_aspect('equal')
    sns.heatmap(tbl, ax=ax, cmap='inferno', vmin=0, vmax=100, cbar_ax=c1)

    ax.tick_params(axis='both', which='both',length=0)
    ticklabels = labels if ticklabels is None else ticklabels
    ax.set_xticklabels(ticklabels)
    ax.set_yticklabels(ticklabels)
    ax.set_ylabel('Stage (current)')
    ax.set_xlabel('Stage (follow-up)')
    ax.set_title(f'N={len(flow)}')

    # draw boxes on diagonal & text
    for i in range(len(labels)):
        for j in range(len(labels)):
            if i == j:
                rec = patches.Rectangle((i, j), width=1, height=1, color='darkgray', fill=False, lw=5, zorder=5)
                ax.add_patch(rec)

            s = str(round(tbl.iloc[i, j], 1))
            color = 'white' if tbl.iloc[i, j] < 90 else 'black'
            ax.text(x=j+.5, y=i+.5, s=s, ha='center', va='center', color=color)

    # draw NS box
    r1 = patches.Rectangle((0, len(labels) - 1), width=len(labels), height=1, color='white', fill=False, lw=5, zorder=1)
    r2 = patches.Rectangle((len(labels) - 1, 0), width=1, height=len(labels), color='white', fill=False, lw=5, zorder=1)
    ax.add_patch(r1)
    ax.add_patch(r2)

    # label colorbar
    c1.yaxis.set_label_position('left')
    c1.set_ylabel('Observed transitions (%)')

    return fig

def pipeline(df, stage_labels=None, out_histogram=None, out_heatmap=None):
    flow = stageflow(df)
    permresults = longitudinal_permutation_test(flow, N=N)
    if out_histogram is not None:
        permresults['figure'].savefig(out_histogram, dpi=300)

    hmap = longitudinal_transitions_heatmap(flow, ticklabels=stage_labels)
    if out_heatmap is not None:
        hmap.savefig(out_heatmap, dpi=300)

def stageflow(df, subject_col='Subject', label_col='StageMain'):

    position_col = 'VisitNumber'

    df[position_col] = df.groupby('Subject').cumcount() + 1
    subjects_vc = df[subject_col].value_counts()
    subjects_long = subjects_vc.index[subjects_vc > 1]
    df = df.loc[df[subject_col].isin(subjects_long)]

    g = df.groupby(subject_col)
    flow = pd.DataFrame({'subject': df[subject_col],
                         'pos_from': df[position_col],
                         'pos_to': g[position_col].shift(-1),
                         'label_from': df[label_col],
                         'label_to': g[label_col].shift(-1)}).dropna()

    return flow

def stagestat(label_from, label_to):
    return np.mean(label_to >= label_from)

# MAIN

set_config('main')
stage_labels = ['A0T0', 'A1T0', 'A2T0', 'A2T1', 'A2T2', 'A2T3', 'A2T4', 'NS']

# outputs
output_directory = get('output_directory')
plots_dest = os.path.join(output_directory, 'plots', 'longitudinal_staging_stability')
os.makedirs(plots_dest, exist_ok=True)

# training
df = load_split('training', None, verbose=False)
df = df[~df['ControlForStaging']].copy()
pipeline(df, out_histogram=os.path.join(plots_dest, 'training_permutation_test.png'),
         out_heatmap=os.path.join(plots_dest, 'training_transition_heatmap.png'),
         stage_labels=stage_labels)

# # Validation - All
df = load_split('validation', None, verbose=False)
df = df[~df['ControlForStaging']].copy()
pipeline(df, out_histogram=os.path.join(plots_dest, 'validationAll_permutation_test.png'),
         out_heatmap=os.path.join(plots_dest, 'validationAll_transition_heatmap.png'))

# Validation - subsets
for x in ['A', 'B', 'C']:
    df = load_split('validation', None, verbose=False, validation_sub=x)
    df = df[~df['ControlForStaging']].copy()
    pipeline(df, out_histogram=os.path.join(plots_dest, f'validation{x}_permutation_test.png'),
             out_heatmap=os.path.join(plots_dest, f'validation{x}_transition_heatmap.png'))
