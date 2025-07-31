import os

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
import pandas as pd
import seaborn as sns

from atstaging.config import get, set_config
from atstaging.outputs import load_split
from atstaging.plotting import set_font_properties

# Load data, set config, setup output
set_config('main')
master = load_split(None, None)
master['Stage'] = master['StageLabeled'].replace(['A0T+', 'A1T+', 'NS'], 'Atypical')
training = master[master['Split'].eq('TrainingBaseline') & ~master['ControlForStaging']].copy()
validation = master[master['Split'].eq('ValidationBaseline') & ~master['ControlForStaging']].copy()

set_font_properties()

root_output = get('output_directory')
ODIR = os.path.join(root_output, 'plots', 'compare_aa2024', 'clinical')
os.makedirs(ODIR, exist_ok=True)

# Show how PACC changes over clinical stages
plt.figure(figsize=(8, 6))
sns.boxplot(training, x='AA2024Clinical', y='PACCOriginal', order=['Stage 1', 'Stage 2', 'Stage 3', 'Stage 4-6'])
plt.grid()
plt.title('Training; Original PACC', loc='left')
plt.savefig(os.path.join(ODIR, 'training_pacc_original_boxplot.png'), dpi=300)

plt.figure(figsize=(8, 6))
sns.boxplot(training, x='AA2024Clinical', y='PACCADNI', order=['Stage 1', 'Stage 2', 'Stage 3', 'Stage 4-6'])
plt.grid()
plt.title('Training; ADNI PACC', loc='left')
plt.savefig(os.path.join(ODIR, 'training_pacc_adni_boxplot.png'), dpi=300)

plt.figure(figsize=(8, 6))
sns.boxplot(validation, x='AA2024Clinical', y='PACCOriginal', order=['Stage 1', 'Stage 2', 'Stage 3', 'Stage 4-6'])
plt.grid()
plt.title('Validation; Original PACC', loc='left')
plt.savefig(os.path.join(ODIR, 'validation_pacc_original_boxplot.png'), dpi=300)

plt.figure(figsize=(8, 6))
sns.boxplot(validation, x='AA2024Clinical', y='PACCADNI', order=['Stage 1', 'Stage 2', 'Stage 3', 'Stage 4-6'])
plt.grid()
plt.title('Validation; ADNI PACC', loc='left')
plt.savefig(os.path.join(ODIR, 'validation_pacc_adni_boxplot.png'), dpi=300)

# Distribution of clinical stages across my staging
def compare_staging_heatmap(data, title=None):
    hmap = pd.crosstab(data['Stage'], data['AA2024Clinical'])
    hmap_norm = hmap.div(hmap.sum(axis=1), axis=0) * 100
    
    fig = plt.figure(figsize=(6, 7))
    im = plt.imshow(hmap_norm, vmin=0, vmax=100, cmap='Blues')
    plt.yticks(range(len(hmap_norm.index)), hmap_norm.index)
    plt.xticks(range(len(hmap_norm.columns)), hmap_norm.columns, rotation=45, ha='right')
    
    for x in range(len(hmap_norm.columns)):
        for y in range(len(hmap_norm.index)):
            value = hmap.iloc[y, x]
            prop = hmap_norm.iloc[y, x]
            color = 'black' if prop < 50 else 'white'
            plt.text(x, y, value, color=color, ha='center', va='center')
    if title is not None:  
        plt.title(title, loc='left')
    
    ax = plt.gca()
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.2)
    cbar = plt.colorbar(im, cax=cax)
    cbar.set_label('Row-wise percentage', rotation=270)

    return fig

fig = compare_staging_heatmap(training, 'Training')
plt.savefig(os.path.join(ODIR, 'training_compare_staging_heatmap.png'))

fig = compare_staging_heatmap(validation, 'Validation')
plt.savefig(os.path.join(ODIR, 'validation_compare_staging_heatmap.png'))

# Resilience vs vulnerability

def resilient_vulernable_heatmap(master, split='training', autosave=True):
    
    cmap = plt.colormaps['PuOr_r'].resampled(256)
    newcolors = cmap(np.linspace(0, 1, 256))
    gray = np.array((0.5019607843137255, 0.5019607843137255, 0.5019607843137255, 1.0)) # gray
    newcolors[:25, :] = gray
    newcmap = ListedColormap(newcolors)

    split_value = split.capitalize() + 'Baseline'
    
    data = master[master['Split'].eq(split_value) & master['ControlForStaging'].eq(False)].copy()
    hmap = pd.crosstab(data['Stage'], data['AA2024Clinical'])
    
    resilvul = np.array(
        [[0, 1, 1, 1],
         [0, 1, 1, 1],
         [0, 1, 1, 1],
         [-1, 0, 1, 1],
         [-1, -1, 0, 1],
         [-1, -1, 0, 1],
         [-1, -1, -1, 0],
         [-2, -2, -2, -2]])
    
    fig, axes = plt.subplots(ncols=2, figsize=(8, 8), width_ratios=(7, 1))
    plt.subplots_adjust(wspace=0)
    ax1, ax2 = axes
    ax1.imshow(resilvul, cmap=newcmap, vmin=-2, vmax=2)
    
    count_group = {'Resilient': 0, 'Expected': 0, 'Vulnerable': 0, 'Atypical': 0}
    
    for x in range(len(hmap.columns)):
        for y in range(len(hmap.index)):
            value = hmap.iloc[y, x]
            color = 'black'
            pct = round(value/len(data)*100, 2)
            text = f'{value}\n{pct}%'
            ax1.text(x, y, text, color=color, ha='center', va='center')
    
            rv_value = resilvul[y, x]
            group = { -1:'Resilient',  0:'Expected', 1:'Vulnerable', -2: 'Atypical'}[rv_value]
            count_group[group] += value
    ax1.set_yticks(range(len(hmap.index)), hmap.index)
    ax1.set_xticks(range(len(hmap.columns)), hmap.columns, rotation=45, ha='right')
    ax1.set_title(split.capitalize(), loc='left')
    
    bottom = 0
    colors = {'Resilient': cmap(0.25), 'Expected': cmap(0.5), 'Vulnerable': cmap(0.75), 'Atypical': 'gray'}
    for k, v in count_group.items():
        ax2.bar(0, v, bottom=bottom, label=k, color=colors[k])
        ax2.text(0, bottom + (v/2), f'n={v}', ha='center', va='center')
        bottom += v
    ax2.set_xlim(-0.4, 0.4)
    ax2.set_ylim(0, sum(count_group.values()))
    ax2.set_xticks([])
    
    ax2.legend(loc='lower center', bbox_to_anchor=(0.5, 1))
    bounds = ax2.get_position().bounds
    ax2.set_position([bounds[0], bounds[1] +  0.2, bounds[2], bounds[3] - 0.4])

    return fig

fig = resilient_vulernable_heatmap(master, 'training')
plt.savefig(os.path.join(ODIR, 'training_reslience_heatmap.png'))

fig = resilient_vulernable_heatmap(master, 'validation')
plt.savefig(os.path.join(ODIR, 'validation_reslience_heatmap.png'))