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
    report_download_coverage,
    report_feature_distribution
    )

def create_subject_table_from_combined_search(image_search):
    df = pd.read_csv(image_search)

    amy = df.loc[df['Description'].eq('AV45 Co-registered, Averaged') |
                 df['Description'].eq('FBB Co-registered, Averaged'), :].copy()
    
    tau = df.loc[df['Description'].eq('AV1451 Co-registered, Averaged') |
                 df['Description'].eq('MK6240 Co-registered, Averaged') |
                 df['Description'].eq('PI2620 Co-registered, Averaged'), :].copy()
    
    t1 = df.loc[~ (df['Description'].isin(amy['Description']) | df['Description'].isin(tau['Description'])), :].copy()

    # select columns
    def select(df):
        cols = ['Image Data ID', 'Subject', 'Description',
                'Acq Date']
        tmp = df[cols]
        tmp = tmp.rename(columns={'Image Data ID': 'ImageID', 'Acq Date': 'ScanDate'})
        return tmp

    amy = select(amy)
    tau = select(tau)
    t1 = select(t1)

    # label tracers
    amy['Tracer'] = None
    amy.loc[amy['Description'].str.contains('AV45'), 'Tracer'] = 'FBR'
    amy.loc[amy['Description'].str.contains('FBB'), 'Tracer'] = 'FBB'
    if amy['Tracer'].isna().any():
        raise ValueError('Unable to detect tracer for some rows; recheck logic for assigning ADNI tracers.')

    tau['Tracer'] = None
    tau.loc[tau['Description'].str.contains('AV1451'), 'Tracer'] = 'FTP'
    tau.loc[tau['Description'].str.contains('MK6240'), 'Tracer'] = 'M62'
    tau.loc[tau['Description'].str.contains('PI2620'), 'Tracer'] = 'P26'
    if amy['Tracer'].isna().any():
        raise ValueError('Unable to detect tracer for some rows; recheck logic for assigning ADNI tracers.')

    result = link_modalities(tau, amy, t1, extra_tau_columns=['ImageID'], extra_amyloid_columns=['ImageID'], extra_t1_columns=['ImageID'])
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

    report_download_coverage(df)

    return df

def create_feature_table(preproc_table, habshd_uds, verbose=True):
    
    # add a visit code for the images
    # this assumes that most images are taken at the first visit
    # which seems to be true based on IDA
    # not the best approach, but seems to be needed since dates are given in the subject datatable
    preproc_table = preproc_table.sort_values(['Subject', 'ScanDateTau'])
    preproc_table['VisitID'] = preproc_table.groupby('Subject').cumcount() + 1

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