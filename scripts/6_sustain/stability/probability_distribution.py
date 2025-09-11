import os

import matplotlib.pyplot as plt
import mpltern
import pandas as pd
import seaborn as sns

from atstaging.config import get, set_config
from atstaging.outputs import load_subtyped_data
from atstaging.plotting import subtype_colors, set_font_properties

set_config('main')
root_output = get('output_directory')
colors = subtype_colors()
set_font_properties()

training = load_subtyped_data('training', sustain_model='Training')
validation = load_subtyped_data('validation', sustain_model='Training')
both = pd.concat([training, validation], axis=0, ignore_index=True)

def ternary_plot(data):
    subtypes = ['S1', 'S2', 'S3']

    fig = plt.figure()
    ax = fig.add_subplot(projection='ternary')
    pct_certain = round(data['TrainingProbMLSubtype'].gt(.5).mean() * 100, 2)

    for subtype in subtypes:
        sub = data[data['TrainingMLSubtype'].eq(subtype)]
        p1 = sub['TrainingProbSubtypeS1']
        p2 = sub['TrainingProbSubtypeS2']
        p3 = sub['TrainingProbSubtypeS3']
        color = colors[subtype]
        ax.scatter(p1, p2, p3, color=color, edgecolor='black', label=subtype, zorder=2)

    ax.axtline(0.5, color='black', linestyle='dashed')
    ax.axlline(0.5, color='black', linestyle='dashed')
    ax.axrline(0.5, color='black', linestyle='dashed')
    ax.fill([0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5], color='gray', alpha=0.5, zorder=1)
    ax.set_tlabel('S1')
    ax.set_llabel('S2')
    ax.set_rlabel('S3')
    ax.taxis.set_ticks([])
    ax.laxis.set_ticks([])
    ax.raxis.set_ticks([])
    ax.legend()
    ax.text(-0.05, 0.5, 0.5, f'individuals outside gray area: {pct_certain}%', va='center', ha='center', size=10)

# def probability_boxplot()

ternary_plot(training)
ternary_plot(validation)

data = both

plt.figure()
sns.boxplot(data=data, x='Split', y='TrainingProbMLSubtype', hue='TrainingMLSubtype', palette=colors)
