#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 25 09:38:46 2024

@author: earnestt1234
"""

import datetime as dt
import os
import pandas as pd

def list_loni_images(directory, show_count=True, count_every=100):
    '''
    Search a folder of images downloaded from LONI and return a DataFrame
    of the contents.

    Parameters
    ----------
    directory : path
        System path to folder of images downloaded from LONI.
    show_count : bool, optional
        Show a running count of images. The default is True.
    count_every : int, optional
        How often (how many images) to update the count when using `show_count`.

    Returns
    -------
    pandas.DataFrame
        Image table.

    '''
    # set date format for date folder
    date_fmt = "%Y-%m-%d_%H_%M_%S.%f"

    # init a container to hold dictionaries corresponding to rows
    rows = []

    # move through LONI folder structure to get to images
    print(f'Beginning search for dowloaded LONI images at "{directory}" ...\n')
    c = 0
    for subject in os.listdir(directory):
        subjectfolder = os.path.join(directory, subject)
        if not os.path.isdir(subjectfolder):
            continue

        for description in os.listdir(subjectfolder):
            descriptionfolder = os.path.join(subjectfolder, description)
            if not os.path.isdir(descriptionfolder):
                continue

            for date in os.listdir(descriptionfolder):
                datefolder = os.path.join(descriptionfolder, date)
                if not os.path.isdir(datefolder):
                    continue

                for imageid in os.listdir(datefolder):
                    imageidfolder = os.path.join(datefolder, imageid)
                    if not os.path.isdir(imageidfolder):
                        continue

                    # can finally look at the images now
                    # remove non-image files just in case
                    imagefiles = [i for i in os.listdir(imageidfolder)
                                  if i.endswith(('.dcm', '.nii', '.nii.gz'))]
                    if not imagefiles:
                        continue

                    img = imagefiles[0] # example image
                    is_dicom = img.lower().endswith('dcm')
                    is_nifti = img.lower().endswith(('.nii', '.nii.gz'))

                    if is_dicom:
                        filetype = 'DICOM'
                    elif is_nifti:
                        filetype = 'NIFTI'
                    else:
                        filetype = 'Unknown'

                    # populate the table
                    row = {}
                    row['Subject'] = subject
                    row['Sequence'] = description
                    row['Date'] = pd.to_datetime(date, format=date_fmt)
                    row['FileType'] = filetype
                    row['ImageID'] = imageid
                    if is_nifti:
                        row['Path'] = os.path.join(imageidfolder, img)
                    else:
                        row['Path'] = imageidfolder
                    rows.append(row)

                    c += 1
                    if show_count:
                        if c % count_every == 0:
                            print(f'Catalogued {c} images...')

    print(f'\nFinished; found {c} images.\n')
    return pd.DataFrame(rows)

def _nstring(df, subject_col='Subject'):
    return f'{len(df[subject_col].unique())} subject(s), {len(df)} scan(s)'

def link_loni_modalities(tau, amyloid, t1, subject_col='Subject',
                         date_col='ScanDate', tracer_col='Tracer',
                         id_col='ImageID', tau_amyloid_threshold='180D',
                         verbose=True):

    vprint = print if verbose else lambda *args, **kwargs: None

    tau = tau[[subject_col, date_col, tracer_col, id_col]]
    amyloid = amyloid[[subject_col, date_col, tracer_col, id_col]]

    vprint()
    vprint(f'Starting T1: {_nstring(t1, subject_col)}')
    vprint(f'Starging amyloid: {_nstring(amyloid, subject_col)}')
    vprint(f'Starting tau: {_nstring(tau, subject_col)}')

    # link amyloid & tau
    t_suffix = "Tau"
    a_suffix = "Amyloid"
    t1_suffix = "T1"
    a_date = f'{date_col}{a_suffix}'
    t_date = f'{date_col}{t_suffix}'
    t1_date = f'{date_col}{t1_suffix}'
    merged = tau.merge(amyloid,
                       how='left', on=subject_col,
                       suffixes = (t_suffix, a_suffix))
    merged = merged.loc[~ merged[a_date].isna(), :].copy()
    vprint()
    vprint(f'Subjects with amyloid/tau: {_nstring(merged, subject_col=subject_col)}')

    merged[t_date] = pd.to_datetime(merged[t_date])
    merged[a_date] = pd.to_datetime(merged[a_date])
    merged['TauAmyloidDiff'] = merged[t_date] - merged[a_date]
    merged['TauAmyloidDiffAbs'] = merged['TauAmyloidDiff'].abs()
    by_tau_scan = merged.groupby([subject_col, t_date])['TauAmyloidDiffAbs'].idxmin()
    grouped = merged.loc[by_tau_scan.values, :]
    grouped = grouped.loc[grouped['TauAmyloidDiffAbs'].le(pd.Timedelta(tau_amyloid_threshold)), :]
    if tau_amyloid_threshold:
        grouped['TauAmyloidMeanDate'] = grouped[t_date] - (grouped['TauAmyloidDiff'] / 2)

    vprint()
    vprint(f'Subjects with amyloid/tau within {tau_amyloid_threshold}: {_nstring(grouped, subject_col=subject_col)}')

    # link t1
    t1 = t1[[subject_col, date_col, id_col]]
    tmp = t1.drop('Subject', axis=1).copy()
    tmp.columns = tmp.columns + 'T1'
    tmp['Subject'] = t1['Subject']

    addt1 = grouped.merge(tmp, on=subject_col,
                          how='left', suffixes=(None, t1_suffix))
    addt1 = addt1.loc[~ addt1[t1_date].isna(), :].copy()

    vprint()
    vprint(f'Subjects with amyloid/tau/T1: {_nstring(addt1, subject_col=subject_col)}')

    addt1[t1_date] = pd.to_datetime(addt1[t1_date])
    addt1['PETT1Diff'] = addt1['TauAmyloidMeanDate'] - addt1[t1_date]
    addt1['PETT1DiffAbs'] = addt1['PETT1Diff'].abs()
    by_tau_scan = addt1.groupby([subject_col, 'TauAmyloidMeanDate'])['PETT1DiffAbs'].idxmin()
    grouped = addt1.loc[by_tau_scan.values, :]

    vprint()
    vprint('Tracer Table:')
    vprint('-----')
    vprint()

    tracer_tabs = pd.crosstab(grouped[f'{tracer_col}{t_suffix}'], grouped[f'{tracer_col}{a_suffix}'])
    vprint(tracer_tabs)

    return grouped

def load_loni_downloads_with_caching(dataset_key, cachedir, download_folder, use_cached=True):
    downloads = None
    if use_cached and os.path.isdir(cachedir):
        cache_files = os.listdir(cachedir)
        for file in cache_files:
            if file.startswith(dataset_key) and file.endswith('.csv'):
                fullfile = os.path.join(cachedir, file)
                print()
                print(f'Using cached file at {fullfile}.')
                downloads = pd.read_csv(fullfile)

    elif downloads is None:
        downloads = list_loni_images(download_folder)
        if not os.path.isdir(cachedir):
            os.mkdir(cachedir)
        ts = dt.datetime.now().strftime('%Y_%m_%d')
        cache_path = os.path.join(cachedir, f'{dataset_key}_{ts}.csv')
        downloads.to_csv(cache_path, index=False)

    return downloads