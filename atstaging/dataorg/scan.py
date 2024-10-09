#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 24 10:55:05 2024

@author: earnestt1234
"""

import pandas as pd

from atstaging.dataorg.utils import assign_training_validation, link_loni_modalities

def create_preproc_table(subject_table, download_table):

    df = subject_table
    df['ImageIDTau'] = df['ImageIDTau'].str.replace('D', 'I')
    df['ImageIDAmyloid'] = df['ImageIDAmyloid'].str.replace('D', 'I')
    df['ImageIDT1'] = df['ImageIDT1'].str.replace('D', 'I')

    mapper = download_table['Path']
    mapper.index = download_table['ImageID']

    df['TauPath'] = df['ImageIDTau'].map(mapper)
    df['AmyloidPath'] = df['ImageIDAmyloid'].map(mapper)
    df['T1Path'] = df['ImageIDT1'].map(mapper)

    return df

def create_subject_table(amy_search, tau_search, t1_search):

    amy = pd.read_csv(amy_search)
    tau = pd.read_csv(tau_search)
    t1 = pd.read_csv(t1_search)

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
        {'AV Coreg, Avg, Rigid Reg to Std Img/Vox Size, 50-70, 6mm Res': 'FBR',
         'FBB Coreg, Avg, Rigid Reg to Std Img/Vox Size, 90-110, 6mm Res': 'FBB',
         'PIB Coreg, Avg, Rigid Reg to Std Img/Vox Size, 40-60, 6mm Res': 'PIB',
         'NAV Coreg, Avg, Rigid Reg to Std Img/Vox Size, 50-70, 6mm Res': 'NAV'}
        )
    tau['Tracer'] = tau['Description'].map(
        {'T80 Coreg, Avg, Rigid Reg to Std Img/Vox Size, 80-100, 6mm Res': 'FTP',
         'M62 Coreg, Avg, Rigid Reg to Std Img/Vox Size, 90-110, 6mm Res': 'M62',
         'P26 Coreg, Avg, Rigid Reg to Std Img/Vox Size, 45-75, 6mm Res': 'P26'})

    result = link_loni_modalities(tau, amy, t1)
    return result

def create_feature_table(preproc_table, nacc_uds, gap_imaging_visit='120D', verbose=True):

    vprint = print if verbose else lambda *args, **kwargs: None
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

    # report
    vprint()
    vprint('DATASET COMPOSITION')
    vprint('===================')

    vprint()
    vprint("Dataset sizes")
    vprint('-----')
    vprint(feature_table['Division'].value_counts())

    vprint()
    vprint('Training set (baseline)')
    vprint('-----')
    tmp = feature_table.loc[feature_table['Division'].eq('BaselineTraining')]
    vprint(pd.crosstab(tmp['AmyloidPositive'], tmp['CDRBinned'], dropna=False))

    vprint()
    vprint('Validation (baseline)')
    vprint('-----')
    tmp = feature_table.loc[feature_table['Division'].eq('BaselineValidation')]
    vprint(pd.crosstab(tmp['AmyloidPositive'], tmp['CDRBinned'], dropna=False))
    vprint()
    vprint(pd.crosstab(tmp['TracerAmyloid'], tmp['TracerTau']))

    return feature_table
