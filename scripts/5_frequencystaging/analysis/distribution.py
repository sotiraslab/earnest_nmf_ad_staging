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

from atstaging.config import get, set_config
from atstaging.outputs import load_split
from atstaging.plotting import staging_colors, set_font_properties

# preparations
set_config('main')

set_font_properties(8)

output_directory = get('output_directory')
plot_dest = os.path.join(output_directory, 'plots', 'stage_distribution')
os.makedirs(plot_dest, exist_ok=True)

# load data
baseline = load_split(None, 'baseline', omit_control=False, verbose=False)
baseline['Group'] = (
    np.where(baseline['Split'].eq('TrainingBaseline'), 'Training', 'Validation') +
    '-' +
    np.where(baseline['ControlForStaging'].eq(True), 'NC', 'ADS')
    )
baseline['Stage'] = baseline['Stage'].replace({'Atypical': 'NS'})

scolors = staging_colors()

# Plot stage percentage by group
groups = ['Training-NC', 'Training-ADS', 'Validation-NC', 'Validation-ADS']
stages = ['A0T0', 'A1T0', 'A2T0', 'A2T1', 'A2T2', 'A2T3', 'A2T4', 'NS']

plt.figure(figsize=(1.8, 2.333))

for i, group in enumerate(groups):
    x = i
    bottom = 0
    sub = baseline[baseline['Group'].eq(group)].copy()
    for j, stage in enumerate(stages):
        n = (sub['Stage'].eq(stage)).sum()
        pct = n / len(sub) * 100
        color = scolors[stage]
        label = '_' * i + stage
        plt.bar(
            x=x, height=pct, bottom=bottom,
            color=color, edgecolor='black', label=label,
            linewidth=0.5)
        bottom += pct

    plt.text(i, 105, len(sub), ha='center', va='center', fontsize=6)

plt.xticks(range(len(groups)), groups, rotation=30, ha='right')
plt.ylabel('Frequency (%)')
plt.ylim(0, 100)
# plt.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=6)

plt.tight_layout()
plt.savefig(os.path.join(plot_dest, 'stage_distribution_by_group.svg'))

# Stage percentage by dataset
datasets = ['A4', 'ADNI', 'GS1', 'GS2', 'HABS', 'HABSHD', 'OASIS', 'SCAN']

plt.figure(figsize=(2.333, 2.333))

for i, dataset in enumerate(datasets):
    x = i
    bottom = 0
    sub = baseline[baseline['DataSet'].eq(dataset)].copy()
    for j, stage in enumerate(stages):
        n = (sub['Stage'].eq(stage)).sum()
        pct = n / len(sub) * 100
        color = scolors[stage]
        label = '_' * i + stage
        plt.bar(
            x=x, height=pct, bottom=bottom,
            color=color, edgecolor='black', label=label,
            linewidth=.5)
        bottom += pct

    plt.text(i, 105, len(sub), ha='center', va='center', fontsize=6)

plt.xticks(range(len(datasets)), datasets, rotation=30, ha='right')
plt.ylabel('Frequency (%)')
plt.ylim(0, 100)
# plt.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=6)

plt.tight_layout()
plt.savefig(os.path.join(plot_dest, 'stage_distribution_by_dataset.svg'))

# Create a separate figure for legend

plt.figure(figsize=(3.5, .5))

for i, stage in enumerate(stages):
    plt.barh(
        0, 1, left=i, color=scolors[stage], label=stage,
        edgecolor='black', linewidth=1)
plt.axis('off')
plt.legend(
    loc='upper center',
    bbox_to_anchor=(0.5, 0),
    ncols=len(stages),
    fontsize=6,
    frameon=False
    )

plt.tight_layout()
plt.savefig(os.path.join(plot_dest, 'legend.svg'), bbox_inches='tight')

# Plot NS types by group
baseline['StageLabelNS'] = baseline['StageLabelNS'].replace({'Other': 'Atypical Tau'})
groups = ['Training-NC', 'Training-ADS', 'Validation-NC', 'Validation-ADS']
stages = ['A0T+', 'A1T+', 'MTL-', 'Atypical Tau']
scolors['Atypical Tau'] = scolors['Other']

plt.figure(figsize=(3.5, 3))

for i, group in enumerate(groups):
    x = i
    bottom = 0
    sub = baseline[baseline['Group'].eq(group) & baseline['Stage'].eq('NS')].copy()
    print()
    print(group)
    print(sub['StageLabelNS'].value_counts()/len(sub)*100)
    for j, stage in enumerate(stages):
        n = (sub['StageLabelNS'].eq(stage)).sum()
        pct = n / len(sub) * 100
        color = scolors[stage]
        label = '_' * i + stage
        plt.bar(x=x, height=pct, bottom=bottom, color=color, edgecolor='black', label=label)
        bottom += pct

    plt.text(i, 102, str(len(sub)), ha='center', va='center')

plt.xticks(range(len(groups)), groups, rotation=30, ha='right')
plt.ylabel('Frequency (%)')
plt.ylim(0, 100)
plt.legend(loc='upper left', bbox_to_anchor=(1, 1))


plt.tight_layout()
plt.savefig(os.path.join(plot_dest, 'distribution_of_NS.svg'), bbox_inches='tight')
