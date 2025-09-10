#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  5 14:09:01 2025

@author: earnestt1234
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from atstaging.config import get, set_config
from atstaging.outputs import load_split
from atstaging.plotting import staging_colors, set_font_properties

# Preparation
set_config('main')
set_font_properties()

baseline = load_split(None, 'baseline')
baseline['Group'] = (
    np.where(baseline['Split'].eq('TrainingBaseline'), 'Training', 'Validation') +
    '-' +
    np.where(baseline['ControlForStaging'].eq(True), 'NC', 'ADS')
    )
scolors = staging_colors()

root_output = get('output_directory')
odir = os.path.join(root_output, 'plots', 'status_staging_concordance')
os.makedirs(odir, exist_ok=True)

# Amyloid
colors = {
    '0': 'gray',
    '1': scolors['A1T0'],
    '2': scolors['A2T0'],
    'NS': scolors['Atypical']
    }

plt.figure(figsize=(5, 7))
baseline['Amyloid stage'] = baseline['StageAmyloid']

sns.stripplot(data=baseline, x="Group", y='SummarySUVRAmyloid', hue='Amyloid stage',
              alpha=0.5, jitter=.333,
              order=['Training-NC', 'Training-ADS', 'Validation-NC', 'Validation-ADS'],
              hue_order=colors.keys(),
              palette=colors)
plt.xticks(rotation=45, ha='right')
plt.ylabel('Cortical amyloid (SUVR)')
plt.legend(loc='upper left', bbox_to_anchor=(1,1))

plt.tight_layout()
plt.savefig(os.path.join(odir, 'amyloid_status_concordance.svg'), dpi=300)

# Tau
colors = {
    '0': 'gray',
    '1': scolors['A2T1'],
    '2': scolors['A2T2'],
    '3': scolors['A2T3'],
    '4': scolors['A2T4'],
    'NS': scolors['Atypical']
    }

plt.figure(figsize=(5, 7))
baseline['Tau stage'] = baseline['StageTau']
sns.stripplot(data=baseline, x="Group", y='SummarySUVRTau', hue='Tau stage',
              alpha=0.5, jitter=.333,
              order=['Training-NC', 'Training-ADS', 'Validation-NC', 'Validation-ADS'],
              hue_order=colors.keys(),
              palette=colors)
plt.xticks(rotation=45, ha='right')
plt.ylabel('Cortical tau (SUVR)')
plt.legend(loc='upper left', bbox_to_anchor=(1,1))

plt.tight_layout()
plt.savefig(os.path.join(odir, 'tau_status_concordance.svg'), dpi=300)
