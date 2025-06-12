#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 11 15:48:11 2025

@author: earnestt1234
"""

# IMPORTS

import os

import matplotlib.pyplot as plt

from atstaging.config import get, set_config
from atstaging.outputs import load_split
from atstaging.plotting import staging_colors

# PARAMETERS

def pie_chart_atypical_staging(data):

    pieorder = ['A0T+', 'A1T+', 'NS']
    colors_dict = staging_colors()

    # Pie chart of stages in the training set
    vc = data['StageLabeled'].value_counts().reindex(pieorder).dropna()
    labels = vc.index
    counts = vc.values

    colors = [colors_dict[s] for s in labels]
    plt.figure(figsize=(5, 5))
    plt.pie(counts, labels=labels, colors=colors,
            wedgeprops = {"edgecolor" : "black", 'linewidth': 1, 'antialiased': True},
            startangle=90)

def pie_chart_typical_staging(data):

    pieorder = ['A0T0', 'A1T0', 'A2T0', 'A2T1', 'A2T2', 'A2T3', 'A2T4', 'Atypical']
    colors_dict = staging_colors()

    # Pie chart of stages in the training set
    edited = data['StageLabeled'].copy()
    edited[edited.isin(['A1T+', 'A0T+', 'NS'])] = 'Atypical'
    vc = edited.value_counts().reindex(pieorder).dropna()
    labels = vc.index
    counts = vc.values

    colors = [colors_dict[s] for s in labels]
    plt.figure(figsize=(5, 5))
    plt.pie(counts, labels=labels, colors=colors,
            wedgeprops = {"edgecolor" : "black", 'linewidth': 1, 'antialiased': True},
            startangle=90)

# MAIN

set_config('main')

plt.rcParams.update({'font.family': 'arial'})

output_directory = get('output_directory')
plot_dest = os.path.join(output_directory, 'plots', 'stage_distribution')
os.makedirs(plot_dest, exist_ok=True)

# training set
training = load_split('training', 'baseline', omit_control=True, verbose=False)

pie_chart_typical_staging(training)
plt.title(f'Training set (N={len(training)})', loc='left')
plt.savefig(os.path.join(plot_dest, 'training_pie.png'), dpi=300)

pie_chart_atypical_staging(training)
n_ns = sum(training['StageLabeled'].isin(['A0T+', 'A1T+', 'NS']))
plt.title(f'N={n_ns}', loc='left')
plt.savefig(os.path.join(plot_dest, 'training_atypical_pie.png'), dpi=300)

# validation set
validation = load_split('validation', 'baseline', omit_control=True, verbose=False)

pie_chart_typical_staging(validation)
plt.title(f'Validation set (N={len(validation)})', loc='left')
plt.savefig(os.path.join(plot_dest, 'validation_pie.png'), dpi=300)

pie_chart_atypical_staging(validation)
n_ns = sum(validation['StageLabeled'].isin(['A0T+', 'A1T+', 'NS']))
plt.title(f'N={n_ns}', loc='left')
plt.savefig(os.path.join(plot_dest, 'validation_atypical_pie.png'), dpi=300)
