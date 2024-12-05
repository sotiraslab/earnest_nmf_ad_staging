#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 24 10:55:05 2024

@author: earnestt1234
"""

import numpy as np
import pandas as pd

from atstaging.dataorg.utils import (
    add_features_by_viscode,
    assign_training_validation,
    bin_cdr,
    link_modalities,
    load_csv_by_match,
    report_download_coverage,
    report_feature_distribution
    )

def create_subject_table(amy_search, tau_search, t1_search, tabular_folder):

    amy = pd.read_csv(amy_search)
    tau = pd.read_csv(tau_search)
    t1 = pd.read_csv(t1_search)

    # select columns
    # For HABS-HD, there are more images available than subjects in the clinical tables
    # we explicitly filter those out here
    # load all subjects
    searches = [
        'HD 1 African',
        'HD 1 Mexican',
        'HD 1 Non',
        'HD 2 Mexican',
        'HD 2 Non',
        'HD 3 Mexican',
        'HD 3 Non']
    habshd = pd.concat([load_csv_by_match(tabular_folder, s) for s in searches])
    subjects = habshd['Med_ID'].unique()

    def select(df):
        cols = ['Image Data ID', 'Subject', 'Description',
                'Acq Date', 'Visit']
        tmp = df[cols]
        tmp = tmp.rename(columns={'Image Data ID': 'ImageID', 'Acq Date': 'ScanDate'})
        tmp = tmp[tmp['Subject'].isin(subjects)]
        return tmp

    amy = select(amy)
    tau = select(tau)
    t1 = select(t1)

    # label tracers
    amy['Tracer'] = 'FBB'
    tau['Tracer'] = 'P26'

    result = link_modalities(tau, amy, t1,
                             extra_tau_columns=['ImageID'],
                             extra_amyloid_columns=['ImageID'],
                             extra_t1_columns=['ImageID', 'Visit'])
    return result

def create_preproc_table(subject_table, download_table):

    df = subject_table
    df['ImageIDTau'] = df['ImageIDTau'].str.replace('D', 'I')
    df['ImageIDAmyloid'] = df['ImageIDAmyloid'].str.replace('D', 'I')
    df['ImageIDT1'] = df['ImageIDT1'].str.replace('D', 'I')

    mapper = download_table['Path']
    mapper.index = download_table['ImageID']

    df['PathTau'] = df['ImageIDTau'].map(mapper)
    df['PathAmyloid'] = df['ImageIDAmyloid'].map(mapper)
    df['PathT1'] = df['ImageIDT1'].map(mapper)

    report_download_coverage(preproc_table=df)

    return df

def create_feature_table(preproc_table, habshd_uds, verbose=True):
    
    # Confirmed that the LONI labels of visits for MRI should match with the
    # clinical Visits (Visit_ID) defined in HABS-HD
    # just need to recode
    # NOTE: only applies for T1!  Amyloid/tau visit IDs in LONI will not map
    #       to the clinical visits in a straightforward way
    preproc_table = preproc_table.sort_values(['Subject', 'ScanDateTau'])
    preproc_table['VisitID'] = preproc_table['VisitT1'].map(
        {'BL': 1,
         'M24': 2,
         'M48': 3,
         'M72': 4}
    )

    # add the variables of interest
    features = add_features_by_viscode(preproc_table, habshd_uds, fields=['Age', 'ID_Gender','APOE4_Positivity', '01_AB_FBB_AB_pos', 'CDR_Global', 'CDR_Sum'],
                                       a_subject='Subject', b_subject='Med_ID',
                                       a_viscode='VisitID', b_viscode='Visit_ID')
    features = features.drop_duplicates(subset=['Subject', 'VisitID'], keep='first')

    # recoding features
    # Many visit twos with missing age, so imputing two years from the baseline age
    features['ImputedAge'] = features.groupby('Subject')['Age'].transform('first') + (2 * (features['VisitID'] - 1))
    features.loc[features['Age'].isna(), 'Age'] = features['ImputedAge']

    # ID_Gender is male=0, female=1
    features['SexMale'] = 1 - features['ID_Gender']
    features['SexMale'] = features.groupby('Subject')['SexMale'].transform('ffill')

    # Ffill Amyloid positivity
    features['AmyloidPositive'] = features['01_AB_FBB_AB_pos']
    features['APosImputed'] = features.groupby('Subject')['AmyloidPositive'].transform('ffill')
    features['AmyloidPositive'] = np.where(features['AmyloidPositive'].isna() & features['APosImputed'].eq(1), features['APosImputed'], features['AmyloidPositive'])

    # APOE
    features['HasE4'] = features['01_AB_FBB_AB_pos']
    features['HasE4'] = features.groupby('Subject')['HasE4'].transform('ffill')

    # CDR
    features['CDR'] = features['CDR_Global']
    features['CDRSumBoxes'] = features['CDR_Sum']
    features['CDRBinned'] = bin_cdr(features['CDR'])

    # filter columns
    keep_columns = list(preproc_table.columns) + ['Age', 'SexMale', 'HasE4', 'AmyloidPositive', 'CDR', 'CDRSumBoxes', 'CDRBinned']
    features = features[keep_columns].copy()

    # assign training/validation 
    final = assign_training_validation(features)

    if verbose:
        report_feature_distribution(final)

    return final