
import os

from lifelines import KaplanMeierFitter
from lifelines.statistics import pairwise_logrank_test
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from atstaging.config import get, set_config
from atstaging.outputs import load_subtyped_data
from atstaging.plotting import subtype_colors, set_font_properties

set_config('main')

# load longitudinal data
path_cdr_long = os.path.join(get('output_directory'), 'longitudinalTables', 'cdr_long.csv')
cdr_long = pd.read_csv(path_cdr_long, parse_dates=['DateBaseline', 'DateLongitudinal'])
cdr_long['Event'] = cdr_long['CDR'].ge(1)

path_mmse_long = os.path.join(get('output_directory'), 'longitudinalTables', 'mmse_long.csv')
mmse_long = pd.read_csv(path_mmse_long, parse_dates=['DateBaseline', 'DateLongitudinal'])
mmse_long['Event'] = mmse_long['MMSE'].le(24)

# Run the survival analyses

def survival_analysis(variable='cdr', split='training', autosave=True):

    # Load the data with stages
    ads = load_subtyped_data(split, load_controls=False)
    control = load_subtyped_data(split, load_controls=True)
    df = pd.concat([ads, control], axis=0, ignore_index=True)
    df['Subtype'] = np.where(df['ControlForStaging'], 'Control', df['TrainingMLSubtype'])

    # Merge with the longitudinal assessments
    merge_data = {'cdr': cdr_long, 'mmse': mmse_long}[variable]
    survdata = merge_data[merge_data['Subject'].isin(df['Subject'])].copy()
    survdata = survdata[survdata['Subject'].duplicated(keep=False)].copy()
    survdata = survdata.merge(df, on='Subject', how='left')

    # determine who has event at baseline
    bl_event = survdata.groupby('Subject')['Event'].transform('first')
    survdata = survdata[~bl_event].copy()

    # group into lifelines format
    survdata['Duration'] =  (survdata['DateLongitudinal'] - survdata.groupby('Subject')['DateLongitudinal'].transform('first')).dt.total_seconds() / (60*60*24*365.25)
    survgroup = survdata.groupby('Subject').agg({'Subtype': 'first', 'Duration': 'max', 'Event': 'any'})
    survgroup['Event'] = survgroup['Event'].astype(float)

    # Model
    kmf = KaplanMeierFitter()
    fig, ax = plt.subplots(figsize=(9,5))

    groups = sorted(survgroup['Subtype'].unique())
    colors = subtype_colors()
    colors['Control'] = 'gray'

    for group in groups:
        idx = survgroup['Subtype'].eq(group)
        T = survgroup.loc[idx, 'Duration']
        E = survgroup.loc[idx, 'Event']

        kmf.fit(T, E, label=group)
        kmf.plot_survival_function(ax=ax, color=colors[group], label=f'{group} (n={int(idx.sum())})')

    # formatting
    plt.xlabel('Years')
    ylabel = {'cdr': 'P(CDR<1)', 'mmse': 'P(MMSE≥24)'}[variable]
    plt.ylabel(ylabel)
    plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
    plt.grid()

    # Statistics
    stats_result = pairwise_logrank_test(survgroup['Duration'], survgroup['Subtype'], survgroup['Event'])
    stats = stats_result.summary
    stats['annot'] = pd.cut(stats['p'], bins=[-np.inf, 0.001, 0.01, 0.05, np.inf], labels=['***', '**', '*', ''])

    # saving
    if autosave:
        root_output = get('output_directory')
        odir = os.path.join(root_output, 'plots', 'sustain', 'survival_analysis')
        os.makedirs(odir, exist_ok=True)

        bname = f'var-{variable}_split-{split}_survival'
        plt.tight_layout()
        fig.savefig(os.path.join(odir, bname + '.png'), dpi=300)
        stats.to_csv(os.path.join(odir, bname + '.csv'))

    return fig, stats

set_font_properties()

# Training
fig, stats = survival_analysis(variable='mmse', split='training')
fig, stats = survival_analysis(variable='cdr', split='training')

# Validation
fig, stats = survival_analysis(variable='mmse', split='validation')
fig, stats = survival_analysis(variable='cdr', split='validation')
