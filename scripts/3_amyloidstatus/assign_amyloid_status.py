import os

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import accuracy_score, roc_curve

from atstaging.amyloidstatus import calculate_cortical_summary_suvr, diagnostic_plot_amyloid_positivity, report_positivity_metrics
from atstaging.outputs import load_master, load_musestats
from atstaging.config import set_config, get

set_config('main')

# setup plots folder
output_folder = get('output_directory')
plot_folder = os.path.join(output_folder, 'plots', 'amyloid_status')
os.makedirs(plot_folder, exist_ok=True)

# load datasets
master = load_master(filters=False, features=False)
muse = load_musestats('amyloid')

# add cortical summary info
cortical_summary_suvr = calculate_cortical_summary_suvr(muse=muse)
merger = muse[['Subject', 'Session']].copy()
merger['CorticalSummarySUVR'] = cortical_summary_suvr
merger = merger[merger['CorticalSummarySUVR'].ne(0) & (~merger['CorticalSummarySUVR'].isna())]

master = master.merge(merger, on=['Subject', 'Session'], how='left')
master = master.dropna(subset=['CorticalSummarySUVR'])

# PLOT 1: amyloid SUVR by dataset
sns.boxplot(data=master, x='DataSet', y='CorticalSummarySUVR', hue='AmyloidPositive')
plt.title('Summary SUVR by ground truth amyloid status')
plt.savefig(os.path.join(plot_folder, 'suvr_by_gt_amyloid.png'), dpi=300)

# Apply ROC method to find the cutoffs for tracer
for i, (tracer, df) in enumerate(master.groupby('TracerAmyloid')):

    print()
    print(f'Tracer={tracer}')
    sub = df[~df['AmyloidPositive'].isna()].copy()
    y_true = sub['AmyloidPositive']
    y_score = sub['CorticalSummarySUVR']
    fpr, tpr, thresholds = roc_curve(y_true, y_score)

    accuracies = []
    for t in thresholds:
        y_pred = np.where(y_score >= t, 1., 0.)
        acc = accuracy_score(y_true, y_pred)
        accuracies.append(acc)

    best_index = np.argmax(accuracies)
    cutoff = thresholds[best_index]

    print(f'Cutoff: {cutoff}')
    result = df['CorticalSummarySUVR'].gt(cutoff).astype(float)
    master.loc[df.index, 'ROCAmyloidStatus'] = result

# Show classifcation accuracy, based on GT amyloid positivity
print()
print(report_positivity_metrics(master, 'ROCAmyloidStatus'))

# PLOT 2: Compare amyloid SUVR with ROC method for cutoff
diagnostic_plot_amyloid_positivity(master, test_score='CorticalSummarySUVR', test_label='ROCAmyloidStatus')
plt.savefig(os.path.join(plot_folder, 'diagnostic_plot_roc.png'), dpi=300)

# Create final amyloid status
master['FinalAmyloidStatus'] = master['AmyloidPositive']
master.loc[master['FinalAmyloidStatus'].isna(), 'FinalAmyloidStatus'] = master['ROCAmyloidStatus']
print()
print('Any NAs in final amyloid status?', master['FinalAmyloidStatus'].isna().any())

# PLOT 3: Compare amyloid SUVR with final amyloid status
diagnostic_plot_amyloid_positivity(master, test_score='CorticalSummarySUVR', test_label='FinalAmyloidStatus')
plt.savefig(os.path.join(plot_folder, 'diagnostic_plot_final.png'), dpi=300)

# Save as a features table to add to master
tosave = master[['Subject', 'Session', 'CorticalSummarySUVR', 'ROCAmyloidStatus', 'FinalAmyloidStatus']]
savepath = os.path.join(output_folder, 'masterTables', 'FEATURE_AMYLOIDSTATUS.csv')
tosave.to_csv(savepath, index=False)

# Determine training/validation sets
df = master.sort_values(['Subject', 'TauAmyloidMeanDate']).reset_index(drop=True)
baseline_index = df.groupby('Subject')['TauAmyloidMeanDate'].idxmin()
baseline = df.loc[baseline_index].copy()

passes_tracer = baseline['TracerAmyloid'].eq('FBP') & baseline['TracerTau'].eq('FTP')
passes_ads = ~(baseline['FinalAmyloidStatus'].eq(0.0) & (baseline['CDR'].isna() | baseline['CDR'].ge(0.5)))
training_subjects = baseline.loc[passes_tracer & passes_ads, 'Subject']


training_text = np.where(df['Subject'].isin(training_subjects), 'Training', 'Validation')
baseline_text = np.where(df.index.isin(baseline.index), 'Baseline', 'Followup')
df['Split'] = training_text + baseline_text

# save
tosave = df[['Subject', 'Session', 'Split']].copy()
savepath = os.path.join(output_folder, 'masterTables', 'FEATURE_SPLIT.csv')
tosave.to_csv(savepath, index=False)

tosave = df[['Subject', 'Session']].copy()
tosave['Keep'] = ~df['Split'].isna() & df['TracerAmyloid'].ne('NAV')
savepath = os.path.join(output_folder, 'masterTables', 'FILTER_SPLIT.csv')
tosave.to_csv(savepath, index=False)