
import os

import pandas as pd

from atstaging.dataorg.utils import load_csv_by_match

# VARIABLES
SEARCH_PI2620 = r"C:\Users\tom.earnest\Downloads\habshd_tau_search_10_10_2024.csv"
SEARCH_FBB = r"C:\Users\tom.earnest\Downloads\habshd_amyloid_search_10_10_2024.csv"
SEARCH_MRI = r"C:\Users\tom.earnest\Downloads\habshd_mri_10_10_2024.csv"
HABSHD_TABULAR = r"C:\Users\tom.earnest\Downloads\tabular"
OUTPUT_DIRECTORY = r"C:\Users\tom.earnest\Desktop"

# load data
tau = pd.read_csv(SEARCH_PI2620)
amy = pd.read_csv(SEARCH_FBB)
t1 = pd.read_csv(SEARCH_MRI)

# filter out the unneeded sequences
tau = tau.loc[tau['Description'].str.contains('PI-2620_PET Brain AC Allpass'), :]
amy = amy.loc[amy['Description'].str.contains('PET.*FBB.*Allpass'), :]
t1 = t1.loc[t1['Description'].str.contains('SAG MPRAGE'), :]

# load all subjects
searches = [
    'HD_1_African',
    'HD_1_Mexican',
    'HD_1_Non',
    'HD_2_Mexican',
    'HD_2_Non',
    'HD_3_Mexican',
    'HD_3_Non']
habshd = pd.concat([load_csv_by_match(HABSHD_TABULAR, s) for s in searches])
subjects = habshd['Med_ID'].unique()

# filter tables to only include subjects for
# which we have tabular clinical/cognitive information available
tau_final = tau[tau['Subject ID'].isin(subjects)]
amy_final = amy[amy['Subject ID'].isin(subjects)]
t1_final = t1[t1['Subject ID'].isin(subjects)]

# save image ids to search
def save_loni_search_field(series, outfile):
    text = ','.join(series)
    with open(outfile, 'w') as f:
        f.write(text)
        
save_loni_search_field(tau_final['Image ID'].astype(str), os.path.join(OUTPUT_DIRECTORY, 'tau_ids.txt'))
save_loni_search_field(amy_final['Image ID'].astype(str), os.path.join(OUTPUT_DIRECTORY, 'amyloid_ids.txt'))
save_loni_search_field(t1_final['Image ID'].astype(str), os.path.join(OUTPUT_DIRECTORY, 't1_ids.txt'))

# report
print()
print(f'Tau images: {len(tau_final)}')
print(f'Amyloid images: {len(amy_final)}')
print(f'T1 images: {len(t1_final)}')
