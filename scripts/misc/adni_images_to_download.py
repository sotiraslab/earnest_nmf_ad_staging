
import os

import pandas as pd

from atstaging.dataorg.utils import link_modalities

# VARIABLES
PET_SEARCH = '/scratch/tom.earnest/atstaging/searches/adni_pet_search.csv'
T1_SEARCH = '/scratch/tom.earnest/atstaging/searches/adni_mri_search.csv'
OUTPUT_DIRECTORY = '/scratch/tom.earnest/atstaging/searches/'

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
                'average dc',
                'cal ',
                'Cal Head 24',
                'ASSET Cal',
                '8hrbrain',
                't1_fl2d_sag',
                'Take off auto send',
                'AXIAL RFORMAT 1',
               ]
    pat = '|'.join(unwanted)
    t1 = t1[~t1['Description'].str.contains(pat, case=False, regex=True)]
    t1 = t1[~t1['Description'].eq('CORONAL')]

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

def filter_pet(pet_search):
    pet_search['Study Date'] = pd.to_datetime(pet_search['Study Date'])
    pet_search = pet_search.sort_values(['Subject ID', 'Study Date'])
    pet_search['Imaging Protocol'] = pet_search.groupby(['Subject ID', 'Study Date'])['Imaging Protocol'].ffill()
    pet_search = pet_search.loc[pet_search['Description'].str.contains('Co-registered, Averaged'), :].copy()

    amyloid = pet_search.loc[(pet_search['Imaging Protocol'].eq('Radiopharmaceutical=18F-AV45') |
                              pet_search['Imaging Protocol'].eq('Radiopharmaceutical=18F-FBB'))].copy()

    tau = pet_search.loc[(pet_search['Imaging Protocol'].eq('Radiopharmaceutical=18F-AV1451') |
                          pet_search['Imaging Protocol'].eq('Radiopharmaceutical=18F-MK6240') |
                          pet_search['Imaging Protocol'].eq('Radiopharmaceutical=18F-PI2620'))].copy()

    return amyloid, tau

# filter tau/amyloid/t1
t1 = filter_adni_t1(t1_search)
amyloid, tau = filter_pet(pet_search)

# merge to find overlap
tau['Tracer'] = tau['Imaging Protocol'].map({
    'Radiopharmaceutical=18F-AV1451': 'FTP',
    'Radiopharmaceutical=18F-MK6240': 'M62',
    'Radiopharmaceutical=18F-PI2620': 'P26'})
amyloid['Tracer'] = amyloid['Imaging Protocol'].map({
    'Radiopharmaceutical=18F-AV45': 'FBP',
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
        f.write('\n')

a = merged['Image IDTau'].astype(int).astype(str)
t = merged['Image IDAmyloid'].astype(int).astype(str)
n = merged['Image IDT1'].astype(int).astype(str)

save_loni_search_field(a, os.path.join(OUTPUT_DIRECTORY, 'adni_tau_ids.txt'))
save_loni_search_field(t, os.path.join(OUTPUT_DIRECTORY, 'adni_amyloid_ids.txt'))
save_loni_search_field(n, os.path.join(OUTPUT_DIRECTORY, 'adni_t1_ids.txt'))

save_loni_search_field(pd.concat([a, t, n]), os.path.join(OUTPUT_DIRECTORY, 'all_ids.txt'))