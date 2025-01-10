
import os
import shutil

from colorama import Fore, Style
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from atstaging.config import get, set_config
from atstaging.outputs import setup_outputs_folder
from atstaging.preprocessing.execute import execute
from atstaging.preprocessing.pipeline import paths_folder_to_dataframe

# variables
INPUT_AMYLOID_IMAGE = 'amyloid_preregistration'
RUN_NAME = 'APNresults'

# only use this for debugging
_DEBUG_LIMIT = None

# config stuff
set_config('main')
output_directory = get('output_directory')
setup_outputs_folder(output_directory)
AMYLOIDPETNET_DIRECTORY = get('amyloidpetnet_directory')
AMYLOIDPETNET_ENV = get('amyloidpetnet_env')

# load paths to amyloid images
preproc_outputs = os.path.join(output_directory, 'preprocessing', 'images')
print()
print('> Loading paths to results of preprocessing outputs in ')
print(f'  - Preprocessing outputs in {preproc_outputs}')
tables = []
for dataset in os.listdir(preproc_outputs):
    dataset_dir = os.path.join(preproc_outputs, dataset)
    if not os.path.isdir(dataset_dir):
        continue
    print(f'  - DataSet={dataset}')
    paths_folder = os.path.join(dataset_dir, 'paths')
    paths_table = paths_folder_to_dataframe(paths_folder)
    tables.append(paths_table)

big_paths_table = pd.concat(tables)
print('> Finished.')

# create AmyloidPETNet compatible dataframe
print()
print('> Creating input CSV compatible with AmyloidPETNet.')
images = big_paths_table[INPUT_AMYLOID_IMAGE ]
images = [img for img in images if os.path.isfile(img)] # so we don't call on non-existent images
apn_input = pd.DataFrame({'img_path': images})
APN_CSV_NAME = f'{RUN_NAME}_input.csv'
APN_CSV_INPUT_PATH = os.path.join(output_directory, 'amyloidpetnet', APN_CSV_NAME)

if _DEBUG_LIMIT is not None:
    print(f'!! WARNING: Debug limit of {_DEBUG_LIMIT} being applied. !!')
    apn_input = apn_input.iloc[:_DEBUG_LIMIT, :].copy()
apn_input.to_csv(APN_CSV_INPUT_PATH, index=False)

print(f'> Saved to {APN_CSV_INPUT_PATH}.')
print(f'> Found {len(apn_input)} input image(s).')

#command to run APN
TMPDIR = os.path.join(AMYLOIDPETNET_DIRECTORY, 'modeltmp')
PREDICT_SCRIPT = os.path.join(AMYLOIDPETNET_DIRECTORY, 'predict.py')
MODEL_DIRECTORY = os.path.join(AMYLOIDPETNET_DIRECTORY, 'model')
command = [
    'conda',
    'run',
    '--name', AMYLOIDPETNET_ENV,
    '--live-stream',
    'python', '-u', PREDICT_SCRIPT,
    '--odir', MODEL_DIRECTORY,
    '--dataset', APN_CSV_INPUT_PATH,
    '--cdir', TMPDIR
]

# run
print()
print('Initiating AmyloidPETNet')
print('    ' + Fore.YELLOW + ' '.join(command) + Style.RESET_ALL)
print('- - -')
execute(command)
print('- - -')

# copy output
print()
print('> Saving raw output.')
APN_CSV_RAWOUTPUT_PATH = os.path.join(output_directory, 'amyloidpetnet', f'{RUN_NAME}_rawoutput.csv')
expected_output = os.path.join(MODEL_DIRECTORY, APN_CSV_NAME)
shutil.copy(expected_output, APN_CSV_RAWOUTPUT_PATH)
print(f'> Finished [{APN_CSV_RAWOUTPUT_PATH}].')

# create nice of table version
print()
print('> Creating version of table with Subject/Session info.')
apn_result = pd.read_csv(APN_CSV_RAWOUTPUT_PATH)
apn_result.columns = [INPUT_AMYLOID_IMAGE, 'APNLogit']
apn_result['APNAmyloidPositive'] = apn_result['APNLogit'].gt(0.0).astype(float)

add_ids = big_paths_table[['Subject', 'Session', INPUT_AMYLOID_IMAGE]]
nicetable = add_ids.merge(apn_result, on=INPUT_AMYLOID_IMAGE, how='inner')
nice_output_path = os.path.join(output_directory, 'amyloidpetnet', f'{RUN_NAME}_output.csv')
nicetable.to_csv(nice_output_path, index=False)
print(f'> Finished [{nice_output_path}].')

# create version of MASTER with this information added
print()
print('> Creating version of MASTER with this information.')
master_folder = os.path.join(output_directory, 'masterTables')
master = pd.read_csv(os.path.join(master_folder, 'MASTER.csv'), dtype={'Subject':str, 'Session':str})
master = master.merge(nicetable, on=['Subject', 'Session'], how='left')
master_output_path = os.path.join(master_folder, 'MASTER_APN.csv')
master.to_csv(master_output_path, index=False)
print(f'> Finished [{master_output_path}].')

# create the diagnostic plot
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

def diagnostic_plot_AmyloidPETNet(df):

    # apn = AmyloidPETNet
    apn = df
    apn = apn[~apn['APNAmyloidPositive'].isna()].copy()

    # recode the amyloid status
    apn['PlotGroup'] = apn['AmyloidPositive'].map({1.0: 'A+', 0.0: 'A-', np.nan: 'NA'})

    # set up some useful variables for plots
    datasets = apn['DataSet'].unique()
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
        data = apn[apn['DataSet'].eq(dataset) & apn['PlotGroup'].eq('A-')].copy()
        if not data.empty:
            ys = data['APNLogit']
            xs = jitter_ys(ys, xcenter=col1_center, spread=column_halfwidth)
            color = np.where(ys < 0, 'blue', 'red')
            ax.scatter(xs, ys, c=color, edgecolors='blue')
            tn = (ys < 0).sum()
            fp = (ys >= 0).sum()
        else:
            tn = 0
            fp = 0

        # plot GT: A+
        data = apn[apn['DataSet'].eq(dataset) & apn['PlotGroup'].eq('A+')].copy()
        if not data.empty:
            ys = data['APNLogit']
            xs = jitter_ys(ys, xcenter=col2_center, spread=column_halfwidth)
            color = np.where(ys < 0, 'blue', 'red')
            ax.scatter(xs, ys, c=color, edgecolors='red')
            tp = (ys >= 0).sum()
            fn = (ys < 0).sum()
        else:
            tp = 0
            fn = 0

        # plot GT: ???
        data = apn[apn['DataSet'].eq(dataset) & apn['PlotGroup'].eq('NA')].copy()
        if not data.empty:
            ys = data['APNLogit']
            xs = jitter_ys(ys, xcenter=col3_center, spread=column_halfwidth)
            color = np.where(ys < 0, 'blue', 'red')
            ax.scatter(xs, ys, c=color)
    
        label = f'{dataset}\n[{tp}/{tn}/{fp}/{fn}]'
        labels.append(label)

    # formatting
    ax.set_ylabel('AmyloidPETNet Score')
    ax.set_xlabel('Ground Truth Group\n[TP/TN/FP/FN]')
    ax.axhline(0, color='k', linestyle='dashed')
    ax.set_xticks(range(len(datasets)), labels)
    
    gt = apn[~apn['AmyloidPositive'].isna()].copy()
    total = len(gt)
    tp = (apn['AmyloidPositive'].eq(1) & apn['APNAmyloidPositive'].eq(1)).sum()
    tn = (apn['AmyloidPositive'].eq(0) & apn['APNAmyloidPositive'].eq(0)).sum()
    fp = (apn['AmyloidPositive'].eq(0) & apn['APNAmyloidPositive'].eq(1)).sum()
    fn = (apn['AmyloidPositive'].eq(1) & apn['APNAmyloidPositive'].eq(0)).sum()
    correct = tp + tn
    
    title = f'TruePos: {pct(tp, total)}%, TrueNeg: {pct(tn, total)}%, FalsePos: {pct(fp, total)}%, FalseNeg: {pct(fn, total)}%, Accuracy: {pct(correct, total)}%'
    ax.set_title(title)

    return fig

print()
print('> Creating diagnostic plot.')
fig = diagnostic_plot_AmyloidPETNet(master)
outpath = os.path.join(output_directory, 'amyloidpetnet', f'{RUN_NAME}_plot.png')
plt.tight_layout()
fig.savefig(outpath, dpi=300)
print(f'> Finished [{outpath}].')