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

set_font_properties()

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
baseline['Stage'] = baseline['StageLabeled'].replace(['A0T+', 'A1T+', 'NS'], 'Atypical')

scolors = staging_colors()

# Plot stage percentage by group
groups = ['Training-NC', 'Training-ADS', 'Validation-NC', 'Validation-ADS']
stages = ['A0T0', 'A1T0', 'A2T0', 'A2T1', 'A2T2', 'A2T3', 'A2T4', 'Atypical']

plt.figure(figsize=(6, 6))

for i, group in enumerate(groups):
    x = i
    bottom = 0
    sub = baseline[baseline['Group'].eq(group)].copy()
    for j, stage in enumerate(stages):
        n = (sub['Stage'].eq(stage)).sum()
        pct = n / len(sub) * 100
        color = scolors[stage]
        label = '_' * i + stage
        plt.bar(x=x, height=pct, bottom=bottom, color=color, edgecolor='black', label=label)
        bottom += pct

plt.xticks(range(len(groups)), groups, rotation=45, ha='right')
plt.ylabel('Frequency (%)')
plt.ylim(0, 100)
plt.legend(loc='upper left', bbox_to_anchor=(1, 1))

plt.tight_layout()
plt.savefig(os.path.join(plot_dest, 'stage_distribution_by_group.svg'), dpi=300)

# Stage percentage by dataset
datasets = ['A4', 'ADNI', 'GS1', 'GS2', 'HABS', 'HABSHD', 'OASIS', 'SCAN']

plt.figure(figsize=(6, 6))

for i, dataset in enumerate(datasets):
    x = i
    bottom = 0
    sub = baseline[baseline['DataSet'].eq(dataset)].copy()
    for j, stage in enumerate(stages):
        n = (sub['Stage'].eq(stage)).sum()
        pct = n / len(sub) * 100
        color = scolors[stage]
        label = '_' * i + stage
        plt.bar(x=x, height=pct, bottom=bottom, color=color, edgecolor='black', label=label)
        bottom += pct

plt.xticks(range(len(datasets)), datasets, rotation=45, ha='right')
plt.ylabel('Frequency (%)')
plt.ylim(0, 100)
plt.legend(loc='upper left', bbox_to_anchor=(1, 1))

plt.tight_layout()
plt.savefig(os.path.join(plot_dest, 'stage_distribution_by_dataset.svg'), dpi=300)


# # PARAMETERS

# def pie_chart_atypical_staging(data):

# # MAIN

# set_config('main')

# plt.rcParams.update({'font.family': 'arial'})

# output_directory = get('output_directory')
# plot_dest = os.path.join(output_directory, 'plots', 'stage_distribution')
# os.makedirs(plot_dest, exist_ok=True)

# # training set
# training = load_split('training', 'baseline', omit_control=True, verbose=False)

# pie_chart_typical_staging(training)
# plt.title(f'Training set (N={len(training)})', loc='left')
# plt.savefig(os.path.join(plot_dest, 'training_pie.png'), dpi=300)

# pie_chart_atypical_staging(training)
# n_ns = sum(training['StageLabeled'].isin(['A0T+', 'A1T+', 'NS']))
# plt.title(f'N={n_ns}', loc='left')
# plt.savefig(os.path.join(plot_dest, 'training_atypical_pie.png'), dpi=300)

# # validation set
# validation = load_split('validation', 'baseline', omit_control=True, verbose=False)

# pie_chart_typical_staging(validation)
# plt.title(f'Validation set (N={len(validation)})', loc='left')
# plt.savefig(os.path.join(plot_dest, 'validation_pie.png'), dpi=300)

# pie_chart_atypical_staging(validation)
# n_ns = sum(validation['StageLabeled'].isin(['A0T+', 'A1T+', 'NS']))
# plt.title(f'N={n_ns}', loc='left')
# plt.savefig(os.path.join(plot_dest, 'validation_atypical_pie.png'), dpi=300)
