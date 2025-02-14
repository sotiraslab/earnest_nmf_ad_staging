import os

import pandas as pd

from atstaging.config import get, set_config

set_config('main')

# get a list of all dataset outputs
output_directory = get('output_directory')
preproc_directory = os.path.join(output_directory, 'preprocessing', 'images')
dataset_folders = [os.path.join(preproc_directory, folder)
                   for folder in os.listdir(preproc_directory)]

# helper for printing percentages
def pct(top, bottom):
    return round(top/bottom * 100, 2)

# main
output = []

for folder in dataset_folders:

    datasetname = os.path.basename(folder).removesuffix('.csv')
    print()
    print(datasetname)
    print('------')

    if not os.path.isdir(folder):
        continue
    
    qccsv = os.path.join(folder, 'qc', 'screenshotQC.csv')
    if not os.path.isfile(qccsv):
        print()
        print(f'! Warning: No QC file for dataset folder {folder}.  Skipping.')
        continue

    qc = pd.read_csv(qccsv, dtype={'Subject': str, 'Session': str})
    score_cols = [col for col in qc.columns if col.endswith('_PASS')]
    score = qc.loc[:, score_cols].copy()
    score = score.apply(lambda col: pd.to_numeric(col, errors='coerce'))
    passing = score.eq(1).all(axis=1)

    df = qc[['Subject', 'Session']].copy()
    df['Keep'] = passing
    output.append(df)

    passes = passing.sum().astype(int)
    fails = (~passing).sum().astype(int)
    total = len(passing)
    print(f'  - Passing: {passes} ({pct(passes, total)}%)')
    print(f'  - Failures: {fails} ({pct(fails, total)}%)')
    print(f'  - Total: {total}')

output = pd.concat(output)

total = len(output)
passes = output['Keep'].sum().astype(int)
fails = total - passes

print()
print(f'Overall passing: {passes} ({pct(passes, total)}%)')
print(f'Overall faliures: {fails} ({pct(fails, total)}%)')
print(f'Overall total: {total}')

print()
print('Saving compiled results as a filter for the master CSV.')
dest = os.path.join(output_directory, 'masterTables', 'FILTER_QC.csv')
output.to_csv(dest, index=False)
print(f'Done. [{dest}]')