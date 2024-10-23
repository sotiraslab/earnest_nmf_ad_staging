
import os

import pandas as pd

from atstaging.dataorg.utils import link_modalities

# VARIABLES
PET_SEARCH = '/Users/earnestt1234/Downloads/idaSearch_10_22_2024.csv'
T1_SEARCH = '/Users/earnestt1234/Downloads/idaSearch_10_14_2024.csv'
OUTPUT_DIRECTORY = '/Users/earnestt1234/Desktop'

# load data
pet_search = pd.read_csv(PET_SEARCH)
t1_search = pd.read_csv(T1_SEARCH)

# helper functions
def filter_adni_t1(t1_search, add_columns=False):

    t1 = t1_search.copy()
    orig_columns = t1.columns

    # filter out the unneeded T1 sequences
    unwanted = ['localizer',
                'calibration',
                'loc',
                'field[\s|_]mapping',
                'surv',
                'fgre',
                'scout',
                'smartbrain',
                'T2',
                'fmri',
                'average dc']
    pat = '|'.join(unwanted)
    t1 = t1[~t1['Description'].str.contains(pat, case=False, regex=True)]

    # sort the dataset
    t1['Study Date'] = pd.to_datetime(t1['Study Date'])
    t1 = t1.sort_values(['Subject ID', 'Study Date'])

    # fill the field mapping
    t1['MagStrength'] = t1['Imaging Protocol'].str.extract('(?<=Field Strength=)(.*)')
    t1['MagStrength'] = t1.groupby('Subject ID')['MagStrength'].transform('ffill')
    t1.loc[t1['MagStrength'].eq(2.9), 'MagStrength'] = 3.0

    # add columns for sorting
    t1['ADNI3or4'] = t1['Phase'].eq('ADNI 3') | t1['Phase'].eq('ADNI 4')
    t1['Accelerated'] = t1['Description'].str.contains('grappa|sense|accel', case=False) | t1['ADNI3or4']
    t1['Processed'] = t1['Type'].eq('Processed')
    t1['Scaled2'] = t1['Description'].str.contains('Scaled.*2', regex=True)
    t1['Scaled'] = t1['Description'].str.contains('Scaled', regex=True)
    t1['N3'] = t1['Description'].str.contains('N3')
    t1['B1'] = t1['Description'].str.contains('B1')
    t1['Gradwarp'] = t1['Description'].str.contains('gradwarp', case=False)
    t1['Repeat'] = t1['Description'].str.contains('repeat|mpr-r', case=False, regex=True)

    # filter out original scans (unless ADNI 3 or 4)
    t1 = t1.loc[(t1['ADNI3or4'] & ~t1['Processed']) | t1['Processed'], :]

    # sort T1
    sort_order = [
        'Subject ID',
        'Study Date',
        'Processed',
        'Accelerated',
        'Scaled2',
        'Scaled',
        'N3',
        'B1',
        'Gradwarp',
        'MagStrength',
        'Repeat']
    ascending = [
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        True
        ]
    t1 = t1.sort_values(by=sort_order, ascending=ascending)

    # group
    grouped = t1.groupby(['Subject ID', 'Study Date']).first().reset_index()

    # return
    if not add_columns:
        keep = [c for c in grouped.columns if c in orig_columns]
        grouped = grouped[keep]

    return grouped

# filter tau/amyloid/t1
t1 = filter_adni_t1(t1_search)
tau = pet_search.loc[pet_search['Type'].eq('Original') &
                     (pet_search['Imaging Protocol'].eq('Radiopharmaceutical=18F-AV1451') |
                      pet_search['Imaging Protocol'].eq('Radiopharmaceutical=18F-MK6240') |
                      pet_search['Imaging Protocol'].eq('Radiopharmaceutical=18F-PI2620'))].copy()
amyloid = pet_search.loc[pet_search['Type'].eq('Original') &
                         (pet_search['Imaging Protocol'].eq('Radiopharmaceutical=18F-AV45') |
                          pet_search['Imaging Protocol'].eq('Radiopharmaceutical=18F-FBB'))].copy()

# merge to find overlap
tau['Tracer'] = tau['Imaging Protocol'].map({
    'Radiopharmaceutical=18F-AV1451': 'FTP',
    'Radiopharmaceutical=18F-MK6240': 'M62',
    'Radiopharmaceutical=18F-PI2620': 'P26'})
amyloid['Tracer'] = amyloid['Imaging Protocol'].map({
    'Radiopharmaceutical=18F-AV45': 'FBR',
    'Radiopharmaceutical=18F-FBB': 'FBB'})
merged = link_modalities(tau=tau, amyloid=amyloid, t1=t1,
                         subject_col='Subject ID',
                         date_col = 'Study Date',
                         tracer_col='Tracer',
                         tau_amyloid_threshold='365D',
                         extra_amyloid_columns=['Image ID'],
                         extra_tau_columns=['Image ID'],
                         extra_t1_columns=['Image ID'])

# save image ids to search
def save_loni_search_field(series, outfile):
    text = ','.join(series)
    with open(outfile, 'w') as f:
        f.write(text)

save_loni_search_field(merged['Image IDTau'].astype(str), os.path.join(OUTPUT_DIRECTORY, 'tau_ids.txt'))
save_loni_search_field(merged['Image IDAmyloid'].astype(str), os.path.join(OUTPUT_DIRECTORY, 'amyloid_ids.txt'))
save_loni_search_field(merged['Image IDT1'].astype(str), os.path.join(OUTPUT_DIRECTORY, 't1_ids.txt'))


