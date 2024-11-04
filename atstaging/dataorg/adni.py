#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 24 10:55:05 2024

@author: earnestt1234
"""

import pandas as pd

from atstaging.dataorg.utils import (
    bin_cdr,
    add_features_by_date,
    add_features_by_subject,
    apply_amyloid_pos_filter,
    assign_training_validation,
    link_modalities,
    load_csv_by_match,
    print_missing,
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

def create_feature_table(preproc_table, tabular_folder):
    
    # load tables
    amyloid = load_csv_by_match(tabular_folder, 'UCBERKELEY_AMY')
    apoe = load_csv_by_match(tabular_folder, 'APOERES')
    cdr = load_csv_by_match(tabular_folder, 'CDR')
    demog = load_csv_by_match(tabular_folder, 'PTDEMOG')
    first_visit = load_csv_by_match(tabular_folder, 'First_Visit')

    # Age
    first_visit['BaselineAge'] = first_visit['subject_age']
    first_visit['BaselineDate'] = pd.to_datetime(first_visit['subject_date'])
    features = add_features_by_subject(preproc_table, first_visit,
                                    fields=['BaselineAge', 'BaselineDate'],
                                    a_subject='Subject', b_subject='subject_id')
    features = features.sort_values(['Subject', 'TauAmyloidMeanDate'])
    features['Age'] = features['BaselineAge'] + ((pd.to_datetime(features['TauAmyloidMeanDate']) - features['BaselineDate']).dt.total_seconds() / (60 * 60 * 24 * 365.25))

    # Sex
    sex = demog.copy()
    sex = sex.drop_duplicates('PTID')
    sex['SexMale'] = (sex['PTGENDER'] == 1).astype(float)
    features = add_features_by_subject(features, sex,
                                    fields=['SexMale'],
                                    a_subject='Subject', b_subject='PTID')
    
    # Genotype
    apoe['HasE4'] = apoe['GENOTYPE'].str.contains('4').astype(float)
    features = add_features_by_subject(features, apoe,
                                    fields=['HasE4'],
                                    a_subject='Subject', b_subject='PTID')

    # Amyloid status
    amyloid['DateAmyloidUCB'] = pd.to_datetime(amyloid['SCANDATE'])
    amyloid['AmyloidPositive'] = amyloid['AMYLOID_STATUS']
    features = add_features_by_date(features, amyloid, fields=['AmyloidPositive'],
                                    a_subject='Subject', a_date='ScanDateAmyloid',
                                    b_subject='PTID', b_date='DateAmyloidUCB', b_name='UCBAMY',
                                    gap_allowed='90D', include_gap_cols=False)

    # CDR
    cdr['CDR'] = cdr['CDGLOBAL']
    cdr['CDRSumBoxes'] = cdr['CDRSB']
    cdr['CDRBinned'] = bin_cdr(cdr['CDGLOBAL'])
    cdr = cdr.loc[cdr['CDR'].ge(0)]
    features = add_features_by_date(features, cdr, fields=['CDR', 'CDRSumBoxes', 'CDRBinned'],
                                    a_subject='Subject', a_date='TauAmyloidMeanDate',
                                    b_subject='PTID', b_date='VISDATE', b_name='CDRVisit',
                                    gap_allowed='180D', include_gap_cols=True)
    

    print()
    print('MISSINGNESS')
    print('-----------')
    print_missing(features, 'Age')
    print_missing(features, 'SexMale')
    print_missing(features, 'HasE4')
    print_missing(features, 'AmyloidPositive')
    print_missing(features, 'CDR')

    # assign training/validation
    final = apply_amyloid_pos_filter(features)
    final = assign_training_validation(final)

    report_feature_distribution(final)

    return final