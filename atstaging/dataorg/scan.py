#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 24 10:55:05 2024

@author: earnestt1234
"""

import pandas as pd

from atstaging.dataorg.utils import link_loni_modalities, list_loni_images

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
