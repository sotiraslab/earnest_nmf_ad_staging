import os

import matplotlib.pyplot as plt
import mpltern
import numpy as np
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

subtypes = ['S1', 'S2', 'S3']

def ternary_plot(data):

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

    return fig

def probability_boxplot():
    data = both.copy()

    data['Subtype'] = data['TrainingMLSubtype']
    data['Group'] = data['Split'].str.replace('Baseline', '')
    fig = plt.figure(figsize=(3, 4))
    sns.boxplot(data=data, x='Group', y='TrainingProbMLSubtype', hue='Subtype', palette=colors, hue_order=subtypes)
    plt.ylim(0, 1.05)
    plt.ylabel('P(subtype)')

    return fig

def probability_cutoff_plot():
    thresholds = np.linspace(0., 1., 21)
    pdata = pd.DataFrame({'Cutoff': thresholds})
    for subtype in subtypes:
        tcol = f'Training{subtype}'
        vcol =  f'Validation{subtype}'
        pdata[tcol] = np.nan
        pdata[vcol] = np.nan
        for i, thr in enumerate(thresholds):
            index = pdata.index[i]
            tsub = training[training['TrainingMLSubtype'].eq(subtype)]
            pdata.loc[index, tcol] = tsub['TrainingProbMLSubtype'].gt(thr).mean()

            vsub = validation[validation['TrainingMLSubtype'].eq(subtype)]
            pdata.loc[index, vcol] = vsub['TrainingProbMLSubtype'].gt(thr).mean()

    fig = plt.figure(figsize=(6,4))
    long = pdata.melt(id_vars='Cutoff', var_name='tmp', value_name='P(subtype) > cutoff')
    long['Split'] = np.where(long['tmp'].str.contains('Training'), 'Training', 'Validation')
    long['Subtype'] = long['tmp'].str.extract('(S\d)')
    sns.lineplot(data=long, x='Cutoff', y='P(subtype) > cutoff', hue='Subtype', style='Split', palette=colors)

    return fig

def probability_subtype_by_stage(data, name=None):

    data['Stage'] = data['TrainingMLStage'].astype(int)
    data['P(subtype)'] = data['TrainingProbMLSubtype']
    data['Subtype'] = data['TrainingMLSubtype']

    fig = plt.figure(figsize=(6, 4))
    sns.boxplot(data=data, x='Stage', y='P(subtype)', hue='Subtype',
                palette=colors, hue_order=subtypes)
    plt.axhline(0.5, color='k', linestyle='dashed')
    plt.ylim(0, 1.05)
    plt.legend(loc='lower left', bbox_to_anchor=(0, 0))

    if name is not None:
        plt.title(f'{name} (n={len(data)})', loc='left')

    return fig

odir = os.path.join(root_output, 'plots', 'sustain', 'subtype_probability')
os.makedirs(odir, exist_ok=True)

fig =  ternary_plot(training)
plt.tight_layout()
plt.savefig(os.path.join(odir, 'training_ternary.svg'), dpi=300)

fig =  ternary_plot(validation)
plt.tight_layout()
plt.savefig(os.path.join(odir, 'validation_ternary.svg'), dpi=300)

fig = probability_boxplot()
plt.tight_layout()
plt.savefig(os.path.join(odir, 'probability_subtype_boxplot.svg'), dpi=300)

fig = probability_cutoff_plot()
plt.tight_layout()
plt.savefig(os.path.join(odir, 'probability_cutoff_plot.svg'), dpi=300)

fig = probability_subtype_by_stage(training, 'Training')
plt.tight_layout()
plt.savefig(os.path.join(odir, 'psubtype_by_stage_training.svg'), dpi=300)

fig = probability_subtype_by_stage(validation, 'Validation')
plt.tight_layout()
plt.savefig(os.path.join(odir, 'psubtype_by_stage_validation.svg'), dpi=300)

