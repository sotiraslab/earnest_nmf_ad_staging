
import os

import pandas as pd

from atstaging.dataorg.utils import load_csv_by_match

# VARIABLES
SEARCH_PI2620 = "/Users/earnestt1234/Desktop/habshd_download/habshd_search_pi2620_12_05_2024.csv"
SEARCH_FBB = "/Users/earnestt1234/Desktop/habshd_download/habshd_search_fbb_12_05_2024.csv"
SEARCH_MRI = "/Users/earnestt1234/Desktop/habshd_download/habshd_t1_10102024_12_05_2024.csv"
HABSHD_TABULAR = "/Users/earnestt1234/Desktop/habshd_download/request-449"
OUTPUT_DIRECTORY = "/Users/earnestt1234/Desktop/habshd_download"

# load data
tau = pd.read_csv(SEARCH_PI2620)
amy = pd.read_csv(SEARCH_FBB)
t1 = pd.read_csv(SEARCH_MRI)

# filter out the unneeded sequences
t1 = t1.loc[t1['Description'].str.contains('SAG MPRAGE'), :]

# load all subjects
searches = [
    'HD 1 African',
    'HD 1 Mexican',
    'HD 1 Non',
    'HD 2 Mexican',
    'HD 2 Non',
    'HD 3 Mexican',
    'HD 3 Non']
habshd = pd.concat([load_csv_by_match(HABSHD_TABULAR, s) for s in searches])
subjects = habshd['Med_ID'].unique()

# filter tables to only include subjects for
# which we have tabular clinical/cognitive information available
tau_final = tau[tau['Subject'].isin(subjects)]
amy_final = amy[amy['Subject'].isin(subjects)]
t1_final = t1[t1['Subject'].isin(subjects)]

# save image ids to search
def save_loni_search_field(series, outfile):
    text = ','.join(series)
    with open(outfile, 'w') as f:
        f.write(text)
        
save_loni_search_field(tau_final['Image Data ID'].astype(str).str.replace('D', 'I'), os.path.join(OUTPUT_DIRECTORY, 'tau_ids.txt'))
save_loni_search_field(amy_final['Image Data ID'].astype(str).str.replace('D', 'I'), os.path.join(OUTPUT_DIRECTORY, 'amyloid_ids.txt'))
save_loni_search_field(t1_final['Image Data ID'].astype(str).str.replace('D', 'I'), os.path.join(OUTPUT_DIRECTORY, 't1_ids.txt'))

# report
print()
print(f'Tau images: {len(tau_final)}')
print(f'Amyloid images: {len(amy_final)}')
print(f'T1 images: {len(t1_final)}')
