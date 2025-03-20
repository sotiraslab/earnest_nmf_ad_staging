
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def jitter_ys(ys, xcenter, spread):
    '''Create jitter in x for raw data being plotted in a bar chart.'''

    xs = np.random.uniform(0, spread/2, size=len(ys))
    half = int(len(ys)/2)
    xs[np.arange(len(xs)) < half] *= -1
    np.random.shuffle(xs)
    xs += xcenter
    return xs

def pct(top, bottom):
    return round(top/bottom * 100, 2)

def calculate_cortical_summary_suvr(muse):
    suvr_cols, vol_cols = get_muse_cortical_summary_columns()
    regional_suvr = muse[suvr_cols]
    regional_vol = muse[vol_cols]
    regional_weights = regional_vol.div(regional_vol.sum(axis=1), axis=0)
    regional_weights.columns = suvr_cols
    cortical_summary_suvr = (regional_suvr * regional_weights).sum(axis=1)
    return cortical_summary_suvr

def diagnostic_plot_amyloid_positivity(df, test_score, test_label, gt_label='AmyloidPositive'):

    pdata = df

    # recode the amyloid status
    pdata['PlotGroup'] = pdata[gt_label].map({1.0: 'A+', 0.0: 'A-', np.nan: 'NA'})

    # set up some useful variables for plots
    datasets = pdata['DataSet'].unique()
    group_width = .75
    column_width = group_width / 3
    column_halfwidth = column_width / 2

    # create figure
    fig, ax = plt.subplots(figsize=(12, 5))

    # main loop
    labels = []
    for i, dataset in enumerate(datasets):
    
        col1_center = i - column_width
        col2_center = i
        col3_center = i + column_width
    
        # draw shading bars showing GT
        ax.axvspan(col1_center - column_halfwidth, col1_center + column_halfwidth, color='blue', alpha=0.1, zorder=1)
        ax.axvspan(col2_center - column_halfwidth, col2_center + column_halfwidth, color='red', alpha=0.1, zorder=1)
        ax.axvspan(col3_center - column_halfwidth, col3_center + column_halfwidth, color='gray', alpha=0.1, zorder=1)
    
        # plot GT: A-
        data = pdata[pdata['DataSet'].eq(dataset) & pdata['PlotGroup'].eq('A-')].copy()
        if not data.empty:
            ys = data[test_score]
            xs = jitter_ys(ys, xcenter=col1_center, spread=column_halfwidth)
            color = np.where(data[test_label].eq(0), 'blue', 'red')
            ax.scatter(xs, ys, c=color, edgecolors='blue', alpha=0.4)
            tn = (ys < 0).sum()
            fp = (ys >= 0).sum()
        else:
            tn = 0
            fp = 0

        # plot GT: A+
        data = pdata[pdata['DataSet'].eq(dataset) & pdata['PlotGroup'].eq('A+')].copy()
        if not data.empty:
            ys = data[test_score]
            xs = jitter_ys(ys, xcenter=col2_center, spread=column_halfwidth)
            color = np.where(data[test_label].eq(0), 'blue', 'red')
            ax.scatter(xs, ys, c=color, edgecolors='red', alpha=0.4)
            tp = (ys >= 0).sum()
            fn = (ys < 0).sum()
        else:
            tp = 0
            fn = 0

        # plot GT: ???
        data = pdata[pdata['DataSet'].eq(dataset) & pdata['PlotGroup'].eq('NA')].copy()
        if not data.empty:
            ys = data[test_score]
            xs = jitter_ys(ys, xcenter=col3_center, spread=column_halfwidth)
            color = np.where(data[test_label].eq(0), 'blue', 'red')
            ax.scatter(xs, ys, c=color,  alpha=0.4)
    
        label = f'{dataset}\n[{tp}/{tn}/{fp}/{fn}]'
        labels.append(label)

    # formatting
    ax.set_ylabel('Score')
    ax.set_xlabel('Ground Truth Group\n[TP/TN/FP/FN]')
    ax.set_xticks(range(len(datasets)), labels)
    
    gt = pdata[~pdata[gt_label].isna()].copy()
    total = len(gt)
    tp = (pdata[gt_label].eq(1) & pdata[test_label].eq(1)).sum()
    tn = (pdata[gt_label].eq(0) & pdata[test_label].eq(0)).sum()
    fp = (pdata[gt_label].eq(0) & pdata[test_label].eq(1)).sum()
    fn = (pdata[gt_label].eq(1) & pdata[test_label].eq(0)).sum()
    correct = tp + tn
    
    title = f'TruePos: {pct(tp, total)}%, TrueNeg: {pct(tn, total)}%, FalsePos: {pct(fp, total)}%, FalseNeg: {pct(fn, total)}%, Accuracy: {pct(correct, total)}%'
    ax.set_title(title)

    return fig

def get_muse_cortical_summary_columns():

    # MAP FS TO MUSE
    # taken from Srinivasan et al. (2020)
    # https://doi.org/10.1016/j.neuroimage.2020.117248
    leftside = {
        'ctx-lh-caudalmiddlefrontal': 'Left MFG   middle frontal gyrus',
        'ctx-lh-lateralorbitofrontal': 'Left POrG  posterior orbital gyrus',
        'ctx-lh-medialorbitofrontal': 'Left SCA   subcallosal area',
        'ctx-lh-parsopercularis': 'Left OpIFG opercular part of the inferior frontal gyrus',
        'ctx-lh-parsorbitalis': 'Left OrIFG orbital part of the inferior frontal gyrus',
        'ctx-lh-parstriangularis':  'Left TrIFG triangular part of the inferior frontal gyrus',
        'ctx-lh-rostralmiddlefrontal': [
            'Left AOrG  anterior orbital gyrus',
            'Left MFG   middle frontal gyrus',
        ],
        'ctx-lh-superiorfrontal': [
            'Left MSFG  superior frontal gyrus medial segment',
            'Left SFG   superior frontal gyrus',
            'Left SMC   supplementary motor cortex',
        ],
        'ctx-lh-frontalpole': [
            'Left FRP   frontal pole',
        ],
        'ctx-lh-caudalanteriorcingulate': 'Left MCgG  middle cingulate gyrus',
        'ctx-lh-isthmuscingulate': 'Left PCgG  posterior cingulate gyrus',
        'ctx-lh-posteriorcingulate': 'Left MCgG  middle cingulate gyrus',
        'ctx-lh-rostralanteriorcingulate': 'Left ACgG  anterior cingulate gyrus',
        'ctx-lh-inferiorparietal': 'Left AnG   angular gyrus',
        'ctx-lh-precuneus': 'Left PCu   precuneus',
        'ctx-lh-superiorparietal': 'Left SPL   superior parietal lobule',
        'ctx-lh-supramarginal': [
            'Left PO    parietal operculum',
            'Left SMC   supplementary motor cortex',
        ],
        'ctx-lh-inferiortemporal': 'Left ITG   inferior temporal gyrus',
        'ctx-lh-middletemporal': 'Left MTG   middle temporal gyrus',
        'ctx-lh-superiortemporal': [
            'Left PP    planum polare',
            'Left PT    planum temporale',
            'Left STG   superior temporal gyrus',
        ],
    }

    # Add the right side
    cortical_summary_fs_to_muse = leftside.copy()

    for k, v in leftside.items():
    
        new_key = k.replace('ctx-lh', 'ctx-rh')
        
        if isinstance(v, str):
            cortical_summary_fs_to_muse[new_key] = v.replace('Left', 'Right')
        else:
            cortical_summary_fs_to_muse[new_key] = [x.replace('Left', 'Right') for x in v]

    # Make a flattened version
    muse_summary_regions_flat = []
    
    for k, v in cortical_summary_fs_to_muse.items():
    
        if isinstance(v, str):
            muse_summary_regions_flat.append(v)
        else:
            _ = [muse_summary_regions_flat.append(x) for x in v]

    # Edits to match columns in saved datasets
    muse_summary_regions_flat = list(set(muse_summary_regions_flat))
    muse_summary_regions = pd.Series(muse_summary_regions_flat)
    muse_summary_regions_nice = muse_summary_regions.str.lower().str.replace(' ', '_').str.replace('_+', '_', regex=True)
    suvr_columns = muse_summary_regions_nice + '_SUVR'
    volume_columns = muse_summary_regions_nice + '_VOLUME'
    
    return suvr_columns, volume_columns

def report_positivity_metrics(master, test_col, gt_col='AmyloidPositive'):

    rows = []

    for i, ((dataset, tracer), df) in enumerate(master.groupby(['DataSet', 'TracerAmyloid'])):
    
        # confusion matrix
        confmat = pd.crosstab(df[gt_col], df[test_col], dropna=False).reindex(index=[0.0, 1.0, np.nan], columns = [0.0, 1.0])
        tp = confmat.iloc[1, 1]
        tn = confmat.iloc[0, 0]
        fp = confmat.iloc[0, 1]
        fn = confmat.iloc[1, 0]
        accuracy = round((tp + tn) / (tp + tn + fp + fn) * 100, 2)

        row = {
            'DataSet': dataset,
            'Tracer': tracer,
            'TP': tp,
            'TN': tn,
            'FP': fp,
            'FN': fn,
            'Accuracy': accuracy,
            # 'AssignedNegative': confmat.iloc[2, 0],
            # 'AssignedPositive': confmat.iloc[2, 1]
        }
        rows.append(row)
    
    confmat_table = pd.DataFrame(rows)
    confmat_table = confmat_table.round(2)
    return confmat_table
