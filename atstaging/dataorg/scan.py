#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 24 10:55:05 2024

@author: earnestt1234
"""

import numpy as np
import pandas as pd

from atstaging.dataorg.utils import (
    assign_training_validation,
    link_modalities,
    report_download_coverage,
    report_feature_distribution,
    report_missingness)

def create_subject_table(pet_search, mri_search):

    # NOTE: these are the CSVs generated from a search record on LONI
    # not the collection CSV

    # SEARCH_PET
    # ----------

    # Run the following search:
    #     - Tick Study Date to show in results
    #     - Tick Image ID to show in results
    #     - Tick Original and Pre-processed
    #     - Tick PET for modality
    #     - Tick Radiopharmaceutical to show in results

    # SEARCH_MRI
    # ----------

    # Run the following search:
    #     - Tick Study Date to show in results
    #     - Tick Image ID to show in results
    #     - Tick Original and Pre-processed
    #     - Tick MRI for modality
    #     - Tick Weighting to show in results

    # rough collection of names
    FBP_NAMES = [
        'Florbetapir F^18^',
        'Florbetapir',
        'florbetapir'
        ]
    FBB_NAMES = [
        'Florbetaben',
        'Florbetaben F^18^',
        'FBB',
        'FLORBETABEN',
        '18F-Florbetaben'
        ]
    PIB_NAMES = [
        'Pittsburgh compound B C^11^',
        'PIB',
        '[11C]PIB',
        'Pittsburgh compound B',
        'PiB C-11'
        ]
    NAV_NAMES = [
        '[18F]NAV-4694',
        '[18F] NAV-4694'
        'NAV-4694'
        ]
    FTP_NAMES = [
        'AV1451',
        'T807 F^18^',
        'AV 1451',
        'FLORTAUCIPIR',
        'T80',
        '[18F]Flortaucipir'
        ]
    M62_NAMES = [
        'MK-6240',
        '[18-F] MK-6240',
        '[18F] MK-6240',
        'M62',
        'MK-6240 F-18',
        'MK6240'
        ]
    P26_NAMES = [
        'PI-2620',
        'P26',
        'PI2620'
        ]

    # load data
    pet = pd.read_csv(pet_search)
    mri = pd.read_csv(mri_search)

    # data wrangling for pet
    pet['Study Date'] = pd.to_datetime(pet['Study Date'])
    pet = pet.sort_values(['Subject ID', 'Study Date', 'Type'])
    pet['Imaging Protocol'] = pet.groupby(['Subject ID', 'Study Date'])['Imaging Protocol'].ffill()
    pet = pet[pet['Type'].eq('Original')].copy()

    # get the tracer
    proto = pet['Imaging Protocol'].str.removeprefix('Radiopharmaceutical=').str.strip().copy()
    pet['Tracer'] = pd.Series(dtype='str')
    pet.loc[proto.isin(FBP_NAMES), 'Tracer'] = 'FBP'
    pet.loc[proto.isin(FBB_NAMES), 'Tracer'] = 'FBB'
    pet.loc[proto.isin(PIB_NAMES), 'Tracer'] = 'PIB'
    pet.loc[proto.isin(NAV_NAMES), 'Tracer'] = 'NAV'

    pet.loc[proto.isin(FTP_NAMES), 'Tracer'] = 'FTP'
    pet.loc[proto.isin(M62_NAMES), 'Tracer'] = 'M62'
    pet.loc[proto.isin(P26_NAMES), 'Tracer'] = 'P26'

    pet = pet[~pet['Tracer'].isna()].copy()

    # separate into amyloid and tau
    amy = pet.loc[pet['Tracer'].isin(['FBP', 'FBB', 'PIB', 'NAV'])].copy()
    tau = pet.loc[pet['Tracer'].isin(['FTP', 'M62', 'P26'])].copy()

    # data wrangling for mri
    mri['Study Date'] = pd.to_datetime(mri['Study Date'])
    mri = mri[
        mri['Imaging Protocol'].eq('Weighting=T1') |
        mri['Description'].str.lower().str.contains('mprage')
        ].copy()
    mri = mri.loc[~ mri['Description'].str.contains('rsfmri', case=False), :].copy()
    mri = mri.loc[~ mri['Description'].str.contains('mapping', case=False), :].copy()


    # select columns
    def select(df):
        cols = ['Image ID', 'Subject ID', 'Description',
                'Study Date']
        if 'Tracer' in df.columns:
            cols += ['Tracer']
        tmp = df[cols]
        tmp = tmp.rename(columns={'Image ID': 'ImageID', 'Study Date': 'ScanDate', 'Subject ID': 'Subject'})
        return tmp

    amy = select(amy)
    tau = select(tau)
    t1 = select(mri)

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

    grouped.loc[grouped['GapToVisitAbs'].gt(pd.Timedelta(gap_imaging_visit)), ['AmyloidPositive', 'CDR', 'CDRSumBoxes', 'CDRBinned']] = np.nan

    # filter columns
    keep_columns = list(preproc_table.columns) + ['Age', 'SexMale', 'HasE4', 'AmyloidPositive', 'CDR', 'CDRSumBoxes', 'CDRBinned']
    grouped_small = grouped[keep_columns].copy()

    report_missingness(grouped_small)

    # add dataset assignment
    feature_table = assign_training_validation(grouped_small)

    if verbose:
        report_feature_distribution(feature_table)

    return feature_table
