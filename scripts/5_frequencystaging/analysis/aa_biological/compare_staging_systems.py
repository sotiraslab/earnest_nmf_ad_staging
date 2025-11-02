import os

import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

import numpy as np
import pandas as pd

from atstaging.config import get, set_config
from atstaging.outputs import load_split
from atstaging.plotting import set_font_properties
from atstaging.staging import assign_frequency_stage

set_config('main')

# Helper functions

def compare_staging_heatmap(data):

    # prep data for plot
    data['AA2024BiologicalStage'] = pd.Categorical(data['AA2024BiologicalStage'], categories=['0','$A+/T_{2}-$','$A+/T_{2MTL}+$','$A+/T_{2MOD}+$','$A+/T_{2HIGH+}$','NS'])
    data['Stage'] = data['Stage'].replace({'Atypical':'NS'})
    hmap = pd.crosstab(data['Stage'], data['AA2024BiologicalStage'])
    hmap_norm = hmap.div(hmap.sum(axis=1), axis=0) * 100

    # formatting for plot
    set_font_properties(7)
    params = {'mathtext.default': 'regular'}
    plt.rcParams.update(params)

    # plot
    fig = plt.figure(figsize=(2.5, 2.5))
    im = plt.imshow(hmap_norm, vmin=0, vmax=100, cmap='Blues')
    plt.yticks(range(len(hmap_norm.index)), hmap_norm.index)
    plt.xticks(range(len(hmap_norm.columns)), hmap_norm.columns, rotation=45, ha='right')

    for x in range(len(hmap_norm.columns)):
        for y in range(len(hmap_norm.index)):
            value = hmap.iloc[y, x]
            prop = hmap_norm.iloc[y, x]
            color = 'black' if prop < 50 else 'white'
            plt.text(x, y, value, color=color, ha='center', va='center', size=6)

    ax = plt.gca()
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="10%", pad=0.1)
    cbar = plt.colorbar(im, cax=cax)
    cbar.set_label('Row-wise percentage', rotation=270)

    return fig

def determine_aa2024_biological_stages():

    df = load_split(None, None, verbose=False)

    root_output = get('output_directory')
    path_braak_w = os.path.join(root_output, 'filesForR', 'braak_wscores.csv')
    braak = pd.read_csv(path_braak_w, dtype={'Subject': str, 'Session': str})
    df = df.merge(braak, on=['Subject', 'Session'], how='left')

    training = df[df['Split'].eq('TrainingBaseline') & ~df['ControlForStaging']]
    braak_neo_pos_values = training.loc[training['BraakNeoWScore'].gt(2.5), 'BraakNeoWScore']
    high_cutoff = np.median(braak_neo_pos_values)

    stage_data = df[['Subject', 'Session']].copy()
    stage_data['A'] = df['FinalAmyloidStatus']
    stage_data['B'] = df['BraakMTLWScore'].gt(2.5).astype(float)
    stage_data['C'] = df['BraakNeoWScore'].gt(2.5).astype(float)
    stage_data['D'] = df['BraakNeoWScore'].gt(high_cutoff).astype(float)



    stages = assign_frequency_stage(stage_data[['A', 'B', 'C', 'D']].to_numpy(), groupings=[0,1,2,3], atypical='NS')
    stages = stages.rename_categories({'0': '0', '1': '$A+/T_{2}-$', '2':'$A+/T_{2MTL}+$', '3':'$A+/T_{2MOD}+$', '4':'$A+/T_{2HIGH+}$', 'NS': 'NS'})

    output = df[['Subject', 'Session']].copy()
    output['AA2024BiologicalStage'] = stages

    outpath = os.path.join(root_output, 'masterTables', 'FEATURE_AA2024Biological.csv')
    output.to_csv(outpath, index=False)

    print(f'Saved stages for {len(output)} subjects at "{outpath}".')

# MAIN

determine_aa2024_biological_stages()

# load data
df = load_split(None, None, verbose=False)
training = df[df['Split'].eq('TrainingBaseline') & ~df['ControlForStaging']].copy()
validation = df[df['Split'].eq('ValidationBaseline') & ~df['ControlForStaging']].copy()

# setup output
root_output = get('output_directory')
odir = os.path.join(root_output, 'plots', 'compare_aa2024', 'biological')
os.makedirs(odir, exist_ok=True)

# training
fig = compare_staging_heatmap(training)
plt.tight_layout()
fig.savefig(os.path.join(odir, 'compare_biological_stages_training.svg'), dpi=300)

# validation
fig = compare_staging_heatmap(validation)
plt.tight_layout()
fig.savefig(os.path.join(odir, 'compare_biological_stages_validation.svg'), dpi=300)
