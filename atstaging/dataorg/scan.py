#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 24 10:55:05 2024

@author: earnestt1234
"""

import pandas as pd

from atstaging.dataorg.utils import (
    assign_training_validation,
    link_modalities,
    report_download_coverage,
    report_feature_distribution)

def create_subject_table(amy_search, tau_search, t1_search):

    amy = pd.read_csv(amy_search)
    tau = pd.read_csv(tau_search)
    t1 = pd.read_csv(t1_search)

    # explicilty omit rsFMRI scans - error that these were added
    t1 = t1.loc[~ t1['Description'].str.contains('rsfmri', case=False), :].copy()

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
    amy['Tracer'] = amy['Description'].map(
        {'AV Co-registered, Averaged, 50-70': 'FBR',
         'FBB Co-registered, Averaged, 90-110': 'FBB',
         'PIB Co-registered, Averaged, 40-60': 'PIB',
         'NAV Coreg, Avg, Rigid Reg to Std Img/Vox Size, 50-70': 'NAV'}
        )
    tau['Tracer'] = tau['Description'].map(
        {'T80 Co-registered, Averaged, 80-100': 'FTP',
         'M62 Co-registered, Averaged, 90-110': 'M62',
         'P26 Co-registered, Averaged, 45-75': 'P26'})

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

def create_feature_table(preproc_table, nacc_uds, gap_imaging_visit='120D', verbose=True):
    nacc = nacc_uds

    # make dataset more manageable in terms of columns
    desired_columns = [
        'NACCID',
        'NACCADC', # ADRC
        'VISITMO',
        'VISITDAY',
        'VISITYR',
        'NACCFDYS', # Days since baseline visit
        'NACCAGE',
        'BIRTHYR',
        'BIRTHMO',
        'SEX',
        'AMYLPET',
        'CDRSUM',
        'CDRGLOB',
        'NACCAPOE',
        'NACCNE4S',
    ]
    naccsub = nacc[desired_columns].copy()

    # link the imaging data to the clinical/cog data
    preproc_table['TauAmyloidMeanDate'] = pd.to_datetime(preproc_table['TauAmyloidMeanDate'])
    naccsub['VisitDate'] = pd.to_datetime(
        {'year': naccsub['VISITYR'],
        'month': naccsub['VISITMO'],
        'day': naccsub['VISITDAY']}
    )
    merged = preproc_table.merge(naccsub, how='left', left_on='Subject', right_on='NACCID')
    merged = merged.loc[~merged['VisitDate'].isna(), :]
    merged['GapToVisit'] = merged['TauAmyloidMeanDate'] - merged['VisitDate']
    merged['GapToVisitAbs'] = merged['GapToVisit'].abs()
    by_imaging = merged.groupby(['Subject', 'TauAmyloidMeanDate'])['GapToVisitAbs'].idxmin()
    grouped = merged.loc[by_imaging, :]
    grouped = grouped.loc[grouped['GapToVisitAbs'].le(pd.Timedelta(gap_imaging_visit)), :]

    # Recoding 

    # >>> Age
    birthage = pd.to_datetime(
        {'year': grouped['BIRTHYR'],
        'month': grouped['BIRTHMO'],
        'day': 15}
    )

    grouped['Age'] = (grouped['TauAmyloidMeanDate'] - birthage).dt.total_seconds() / (60 * 60 * 24 * 365.25)
    grouped[['Age', 'NACCAGE']]

    # >>> Sex
    grouped['SexMale'] = (grouped['SEX'] == 1).astype(float)

    # >>> APOE
    grouped['HasE4'] = grouped['NACCNE4S'].ge(1).astype(float)
    grouped.loc[grouped['NACCNE4S'].eq(9), 'HasE4'] = pd.NA

    # >>> amyloid
    grouped['AmyloidPositive'] = grouped['AMYLPET'].map({
        0: 0.0,
        1: 1.0,
        8: None,
        -4: None,
    })

    # >>> CDR
    grouped['CDR'] = grouped['CDRGLOB']
    grouped['CDRSumBoxes'] = grouped['CDRSUM']
    grouped['CDRBinned'] = grouped['CDR']
    grouped.loc[grouped['CDRBinned'].ge(1), 'CDRBinned'] = 1
    grouped['CDRBinned'] = grouped['CDRBinned'].map({0: '0.0', 0.5: '0.5', 1.0: '1.0+'})

    # filter columns
    keep_columns = list(preproc_table.columns) + ['Age', 'SexMale', 'HasE4', 'AmyloidPositive', 'CDR', 'CDRSumBoxes', 'CDRBinned']
    grouped_small = grouped[keep_columns].copy()

    # add dataset assignment
    feature_table = assign_training_validation(grouped_small)

    if verbose:
        report_feature_distribution(feature_table)

    return feature_table
