# IMPORTS

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import root_scalar
import seaborn as sns
from sklearn.metrics import accuracy_score, roc_curve
from sklearn.mixture import GaussianMixture

from atstaging.petstatus import calculate_cortical_summary_suvr, diagnostic_plot_amyloid_positivity, report_positivity_metrics
from atstaging.outputs import load_master, load_musestats
from atstaging.config import set_config, get

set_config('main')
preproc_dir = '/ceph/chpc/shared/aristeidis_sotiras_group/tom_pet_processing/'

# PREP

# setup plots folder
output_folder = get('output_directory')
plot_folder = os.path.join(output_folder, 'plots', 'data_splitting')
os.makedirs(plot_folder, exist_ok=True)

# load datasets
master = load_master(filters=False, features=False)
muse_amyloid = load_musestats('amyloid', output_directory=preproc_dir)
muse_tau = load_musestats('tau', output_directory=preproc_dir)

# calc cortical summary SUVRs
amyloid_summary_suvr = calculate_cortical_summary_suvr(muse=muse_amyloid, pet='amyloid')
merger = muse_amyloid[['Subject', 'Session']].copy()
merger['SummarySUVRAmyloid'] = amyloid_summary_suvr
merger = merger[merger['SummarySUVRAmyloid'].ne(0) & (~merger['SummarySUVRAmyloid'].isna())]

master = master.merge(merger, on=['Subject', 'Session'], how='left')
master = master.dropna(subset=['SummarySUVRAmyloid'])

tau_summary_suvr = calculate_cortical_summary_suvr(muse=muse_tau, pet='tau')
merger = muse_tau[['Subject', 'Session']].copy()
merger['SummarySUVRTau'] = tau_summary_suvr
merger = merger[merger['SummarySUVRTau'].ne(0) & (~merger['SummarySUVRTau'].isna())]

master = master.merge(merger, on=['Subject', 'Session'], how='left')
master = master.dropna(subset=['SummarySUVRTau'])

# AMYLOID
# ROC approach to match the cutoffs provided by datasets

# PLOT 1: amyloid SUVR by dataset
sns.boxplot(data=master, x='DataSet', y='SummarySUVRAmyloid', hue='AmyloidPositive')
plt.title('Summary SUVR by ground truth amyloid status')
plt.savefig(os.path.join(plot_folder, 'suvr_by_gt_amyloid.png'), dpi=300)

# Apply ROC method to find the cutoffs for tracer
for i, (tracer, df) in enumerate(master.groupby('TracerAmyloid')):

    print()
    print(f'Tracer={tracer}')
    sub = df[~df['AmyloidPositive'].isna()].copy()
    y_true = sub['AmyloidPositive']
    y_score = sub['SummarySUVRAmyloid']
    fpr, tpr, thresholds = roc_curve(y_true, y_score)

    accuracies = []
    for t in thresholds:
        y_pred = np.where(y_score >= t, 1., 0.)
        acc = accuracy_score(y_true, y_pred)
        accuracies.append(acc)

    best_index = np.argmax(accuracies)
    cutoff = thresholds[best_index]

    print(f'Cutoff: {cutoff}')
    result = df['SummarySUVRAmyloid'].gt(cutoff).astype(float)
    master.loc[df.index, 'ROCAmyloidStatus'] = result

# Show classifcation accuracy, based on GT amyloid positivity
print()
print(report_positivity_metrics(master, 'ROCAmyloidStatus'))

# PLOT 2: Compare amyloid SUVR with ROC method for cutoff
diagnostic_plot_amyloid_positivity(master, test_score='SummarySUVRAmyloid', test_label='ROCAmyloidStatus')
plt.savefig(os.path.join(plot_folder, 'diagnostic_plot_roc.png'), dpi=300)

# Create final amyloid status
master['FinalAmyloidStatus'] = master['AmyloidPositive']
master.loc[master['FinalAmyloidStatus'].isna(), 'FinalAmyloidStatus'] = master['ROCAmyloidStatus']
print()
print('Any NAs in final amyloid status?', master['FinalAmyloidStatus'].isna().any())

# PLOT 3: Compare amyloid SUVR with final amyloid status
diagnostic_plot_amyloid_positivity(master, test_score='SummarySUVRAmyloid', test_label='FinalAmyloidStatus')
plt.savefig(os.path.join(plot_folder, 'diagnostic_plot_final.png'), dpi=300)

# Save as a features table to add to master
tosave = master[['Subject', 'Session', 'SummarySUVRAmyloid', 'ROCAmyloidStatus', 'FinalAmyloidStatus']]
savepath = os.path.join(output_folder, 'masterTables', 'FEATURE_AMYLOIDSTATUS.csv')
tosave.to_csv(savepath, index=False)

# TAU Status
# Gaussian mixture model

def gmm_intersection_cutoff(data, n_std=2):

    x = np.array(data)

    gmm = GaussianMixture(n_components=2, random_state=42)
    gmm.fit(x[:, np.newaxis])

    means = gmm.means_
    stds = np.sqrt(gmm.covariances_.flatten())
    weights = gmm.weights_

    g1 = lambda x: norm.pdf(x, loc = means[0], scale = stds[0]) * weights[0]
    g2 = lambda x: norm.pdf(x, loc = means[1], scale = stds[1]) * weights[1]
    diff = lambda x: g2(x) - g1(x)
    cutoff = root_scalar(diff, bracket=list(means)).root

    # plot
    xmin = x.min()
    xmax = x.max()
    x = np.linspace(xmin, xmax, 5000)
    y1 = g1(x)
    y2 = g2(x)

    fig = plt.figure(figsize=(6, 4))
    plt.hist(data, density=True, color='gray')
    plt.plot(x, y1, color='blue')
    plt.fill_between(x, y1, color='blue', alpha=0.3)
    plt.plot(x, y2, color='red')
    plt.fill_between(x, y2, color='red', alpha=0.3)
    plt.axvline(cutoff, color='k')

    plt.show()

    return cutoff, fig

for i, (tracer, df) in enumerate(master.groupby('TracerTau')):    
    print()
    print(f'Tracer={tracer}')
    model_suvrs = df.groupby('Subject').first()['SummarySUVRTau']
    cutoff, fig = gmm_intersection_cutoff(model_suvrs)
    print(f'Cutoff: {cutoff}, Sample size for fit: {len(model_suvrs)}')
    result = df['SummarySUVRTau'].gt(cutoff).astype(float)
    master.loc[df.index, 'GMMTauStatus'] = result
    fig.savefig(os.path.join(plot_folder, f'tau_gmm_{tracer}.png'), dpi=300)

for dataset, df in master.groupby('DataSet'):
    temp = 'A=' + df['FinalAmyloidStatus'].astype(str) + '/CDR=' + df['CDRBinned']
    temp.name = 'DiseaseStatus'
    print()
    print(f'DATASET={dataset}')
    print(pd.crosstab(temp, df['GMMTauStatus']))

# Save as a features table to add to master
tosave = master[['Subject', 'Session', 'SummarySUVRTau', 'GMMTauStatus']]
savepath = os.path.join(output_folder, 'masterTables', 'FEATURE_TAUSTATUS.csv')
tosave.to_csv(savepath, index=False)

# DETERMINE DATA SPLITTING

# reload master with new features
master = load_master()
df = master.sort_values(['Subject', 'TauAmyloidMeanDate']).reset_index(drop=True)
baseline_index = df.groupby('Subject')['TauAmyloidMeanDate'].idxmin()
# baseline = df.loc[baseline_index].copy()

# useful masks
has_demographics = (~df['Age'].isna()) & (~df['SexMale'].isna())
is_baseline = df.index.isin(baseline_index)
is_ads = df['FinalAmyloidStatus'].eq(1.0)
is_cn = df['FinalAmyloidStatus'].eq(0.0) & df['GMMTauStatus'].eq(0.0) & (df['CDR'].eq(0.0) & ~df['CDR'].isna())
has_acceptable_diseasestatus = (is_ads | is_cn) & has_demographics
has_training_tracers = df['TracerAmyloid'].eq('FBP') & df['TracerTau'].eq('FTP')
training_subjects = df.loc[has_training_tracers & has_acceptable_diseasestatus & is_baseline, 'Subject'].unique()
is_training = df['Subject'].isin(training_subjects)

# look for changes to tracer
baseline_tracers = df.loc[is_baseline, ['Subject', 'TracerAmyloid', 'TracerTau']]
baseline_tracers.columns = ['Subject', 'BaselineTracerAmyloid', 'BaselineTracerTau']
tracer_tracker = df[['Subject', 'Session', 'TracerAmyloid', 'TracerTau']]
tracer_tracker = tracer_tracker.merge(baseline_tracers, how='left', on='Subject')
followup_tracer_changes = tracer_tracker['BaselineTracerAmyloid'].ne(tracer_tracker['TracerAmyloid']) | tracer_tracker['BaselineTracerTau'].ne(tracer_tracker['TracerTau'])

#  apply splits
df['Split'] = ''
df.loc[is_training & is_baseline, 'Split'] = 'TrainingBaseline'
df.loc[is_training & ~is_baseline, 'Split'] = 'TrainingFollowup'
df.loc[~is_training & is_baseline, 'Split'] = 'ValidationBaseline'
df.loc[~is_training & ~is_baseline, 'Split'] = 'ValidationFollowup'

# apply exclusion criteria
omit_subjects = df.loc[is_baseline & ~ has_acceptable_diseasestatus, 'Subject']
omit_mask = df['Subject'].isin(omit_subjects) | (~ has_demographics) | followup_tracer_changes
omitted = df[omit_mask].copy()
df = df[~omit_mask].copy()
omitted.to_csv(os.path.join(plot_folder, 'omitted_scans.csv'), index=False)

# Identify same tracer splits
df['SameTracerValidationA'] = df['TracerAmyloid'].eq('PIB') & df['TracerTau'].eq('FTP')
df['SameTracerValidationB'] = df['TracerAmyloid'].eq('FBB') & df['TracerTau'].eq('P26')
df['SameTracerValidationC'] = df['TracerAmyloid'].eq('FBB') & df['TracerTau'].eq('FTP')

# save
tosave = df[['Subject', 'Session', 'Split', 'SameTracerValidationA', 'SameTracerValidationB', 'SameTracerValidationC']].copy()
savepath = os.path.join(output_folder, 'masterTables', 'FEATURE_SPLIT.csv')
tosave.to_csv(savepath, index=False)

tosave = df[['Subject', 'Session']].copy()
tosave['Keep'] = ~df['Split'].isna() & df['TracerAmyloid'].ne('NAV')
savepath = os.path.join(output_folder, 'masterTables', 'FILTER_SPLIT.csv')
tosave.to_csv(savepath, index=False)