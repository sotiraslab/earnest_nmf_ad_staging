#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 11 15:48:11 2025

@author: earnestt1234
"""

# IMPORTS

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from atstaging.config import get, set_config
from atstaging.outputs import load_subtyped_data
from atstaging.plotting import subtype_colors, set_font_properties

# preparations
set_config('main')

set_font_properties()

output_directory = get('output_directory')
plot_dest = os.path.join(output_directory, 'plots', 'sustain', 'subtype_distribution')
os.makedirs(plot_dest, exist_ok=True)
colors = subtype_colors()

# load data
training = load_subtyped_data('training')
validation = load_subtyped_data('validation')
baseline = pd.concat([training, validation], axis=0, ignore_index=True)
baseline['Group'] = (
    np.where(baseline['Split'].eq('TrainingBaseline'), 'Training', 'Validation')
    )

# mark subtypes and stages
baseline['Subtype'] = baseline['TrainingMLSubtype']
baseline.loc[baseline['TrainingMLStage'].eq(0) | baseline['TrainingSubtypeValid'].eq(0), 'Subtype'] = 'NA'
baseline['Stage'] = baseline['TrainingMLStage']

# Subtype percentage by group
groups = ['Training', 'Validation']
subtypes = ['S1', 'S2', 'S3']

plt.figure(figsize=(5, 6))

for i, group in enumerate(groups):
    x = i
    bottom = 0
    sub = baseline[baseline['Group'].eq(group)].copy()
    for j, subtype in enumerate(subtypes):
        n = (sub['Subtype'].eq(subtype)).sum()
        pct = n / len(sub) * 100
        color = colors[subtype]
        label = '_' * i + subtype
        plt.bar(x=x, height=pct, bottom=bottom, color=color, edgecolor='black', label=label)
        bottom += pct

    plt.text(i, 102, len(sub), ha='center', va='center')

plt.xticks(range(len(groups)), groups)
plt.ylabel('Frequency (%)')
plt.ylim(0, 100)
plt.legend(loc='upper left', bbox_to_anchor=(1, 1))

plt.tight_layout()
plt.savefig(os.path.join(plot_dest, 'subtype_distribution_by_group.svg'), dpi=300)

# Subtype percentage by dataset
datasets = ['A4', 'ADNI', 'GS1', 'GS2', 'HABS', 'HABSHD', 'OASIS', 'SCAN']

plt.figure(figsize=(8, 6))

for i, dataset in enumerate(datasets):
    x = i
    bottom = 0
    sub = baseline[baseline['DataSet'].eq(dataset)].copy()
    for j, subtype in enumerate(subtypes):
        n = (sub['Subtype'].eq(subtype)).sum()
        pct = n / len(sub) * 100
        color = colors[subtype]
        label = '_' * i + subtype
        plt.bar(x=x, height=pct, bottom=bottom, color=color, edgecolor='black', label=label)
        bottom += pct

    plt.text(i, 102, len(sub), ha='center', va='center')

plt.xticks(range(len(datasets)), datasets, rotation=45, ha='right')
plt.ylabel('Frequency (%)')
plt.ylim(0, 100)
plt.legend(loc='upper left', bbox_to_anchor=(1, 1))

plt.tight_layout()
plt.savefig(os.path.join(plot_dest, 'subtype_distribution_by_dataset.svg'), dpi=300)

#%% Stage distribution by group
plt.figure(figsize=(6, 4))
sns.boxplot(data=baseline, x='Group', y='Stage', hue='Subtype', palette=colors)

plt.legend(loc='upper left', bbox_to_anchor=(1, 1))

plt.tight_layout()
plt.savefig(os.path.join(plot_dest, 'stage_distribution_by_group.svg'), dpi=300)

#%% Stage distribution by dataset

plt.figure(figsize=(10, 4))
sns.boxplot(data=baseline, x='DataSet', y='Stage', hue='Subtype', palette=colors, order=datasets)

plt.legend(loc='upper left', bbox_to_anchor=(1, 1))

plt.tight_layout()
plt.savefig(os.path.join(plot_dest, 'stage_distribution_by_dataset.svg'), dpi=300)

