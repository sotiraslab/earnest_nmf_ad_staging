#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 25 09:38:46 2024

@author: earnestt1234
"""

import datetime as dt
import os
import re
import warnings

import nibabel as nib
import numpy as np
import pandas as pd

def add_features_by_date(a, b, fields, a_subject='Subject', a_date='Date', b_subject='Subject', b_date='Date', b_name='Visit',
                         gap_allowed='365D', drop_missing=False, include_gap_cols=True):
    # b_subject column gets renamed to a_subject, which is confusing
    # pulling this out as a variable to indicate the destination name for subject
    subject = a_subject

    # ensure numeric datetime
    a[a_date] = pd.to_datetime(a[a_date])
    b[b_date] = pd.to_datetime(b[b_date])

    # filter columns in b
    bcols_date = f'{b_name}Date'
    bcols_gap = f'GapTo{b_name}'
    bcols_abs = f'AbsGapTo{b_name}'
    b = b.rename(columns={b_subject: subject, b_date: bcols_date})
    b = b[[subject, bcols_date] + fields]

    # left merge
    merged = a.merge(b, how='left', on=subject)
    if drop_missing:
        merged = merged.loc[~merged[bcols_date].isna(), :].copy()

    # add gap information and filer
    merged[bcols_gap] = merged[a_date] - merged[bcols_date]
    merged[bcols_abs] = merged[bcols_gap].abs()
    grouped = merged.sort_values([a_subject, a_date, bcols_abs]).groupby([a_subject, a_date]).head(n=1)
    if gap_allowed is not None:
        grouped.loc[grouped[bcols_abs].gt(pd.Timedelta(gap_allowed)), fields + [bcols_gap, bcols_abs]] = None

    if not include_gap_cols:
        merged = merged.drop([bcols_gap, bcols_abs], axis=1)

    return grouped

def add_features_by_subject(a, b, fields, a_subject='Subject', b_subject='Subject',
                            drop_missing=False):
    if b[b_subject].duplicated().any():
        warnings.warn(RuntimeWarning('Merged dataframe has duplicate subjects - more than '
                                     'one row is being added for some subjects.'))
    subject = a_subject
    b = b.rename(columns={b_subject: subject})
    b = b[[subject] + fields]

    # left merge
    merged = a.merge(b, how='left', on=subject)
    if drop_missing:
        merged = merged.dropna(axis=0, subset=fields)

    return merged

def add_features_by_viscode(a, b, fields, a_subject='Subject', a_viscode='VISCODE',
                            b_subject='Subject', b_viscode='VISCODE', drop_missing=False):
    b = b[[b_subject, b_viscode] + fields]
    b = b.rename(columns={b_subject: a_subject, b_viscode: a_viscode})
    merged = a.merge(b, how='left', on=[a_subject, a_viscode])
    if drop_missing:
        merged = merged.loc[~merged[b_viscode].isna(), :].copy()

    return merged

def apply_amyloid_pos_filter(df, subject_col='Subject', positivity_col='AmyloidPositive'):
    def amyfilter(group):
        if (group[positivity_col].eq(0) | group[positivity_col].isna()).all():
            return group
        first_index = group[group[positivity_col].eq(1)].index[0]
        return group.loc[first_index:, :]
    
    return df.groupby(subject_col, as_index=False, group_keys=False)[df.columns].apply(amyfilter)

def assign_training_validation(df, omit_non_ad_training=True, subject='Subject',
                               date='TauAmyloidMeanDate'):
    df = df.sort_values([subject, date])
    baseline = df.groupby(subject)[date].idxmin()

    training_type = np.where(df['TracerAmyloid'].eq('FBP') & df['TracerTau'].eq('FTP'), 'Training', 'Validation')
    visit_type = np.where(df.index.isin(baseline.values), 'Baseline', 'Followup')
    df['Division'] = visit_type + training_type

    if omit_non_ad_training:
        df = df.loc[~(df['Division'].eq('BaselineTraining') & (df['CDR'].ge(0.5) | df['CDR'].isna()) & df['AmyloidPositive'].eq(0.0)), :].copy()

    return df

def bin_cdr(cdr):
    cdr = pd.Series(cdr)
    cdr[cdr.ge(1)] = 1
    cdr = cdr.map({0: '0.0', 0.5: '0.5', 1.0: '1.0+'})
    return cdr

def check_missing_loni_images(downloads, collections, show_count=True, count_every=100,
                              out_table=None, out_text=None):

    # read collections
    if os.path.isfile(collections):
        collection_df = read_loni_collection(collections)
    elif os.path.isdir(collections):
        collection_df = read_loni_collection_folder(collections)
    else:
        raise FileNotFoundError(f'Cannot find input file/folder "{collections}"')

    # read downloads
    if isinstance(downloads, pd.DataFrame):
        # downloads already read;just compare to collections
        download_df = downloads
    elif os.path.isdir(downloads):
        # input is download folder; search and read
        download_df = list_loni_images(downloads, show_count=show_count, count_every=count_every)
    elif os.path.isfile(downloads):
        # input is a download file; read
        download_df = pd.read_csv(downloads)
    else:
        raise ValueError(f'Input `downloads` must be a string path or a DataFrame, not {type(downloads)}')

    DOWNLOAD_IMAGE_COL = 'ImageID'
    COLLECTION_IMAGE_COL = 'Image Data ID'
    collection_ids = collection_df[COLLECTION_IMAGE_COL].str.extract('(\d+)', expand=False).astype(int)
    download_ids = download_df[DOWNLOAD_IMAGE_COL].str.extract('(\d+)', expand=False).astype(int)
    present = collection_ids.isin(download_ids)
    missing = collection_df[~present]

    # report
    if missing.empty:
        print()
        print("No missing images!")
        return
    else:
        print()
        print(f"Missing images: {len(missing)}")

    # create output
    if out_text:
        print(f"Writing text file of image IDs to {out_text}.")
        text = ','.join(missing[COLLECTION_IMAGE_COL].str.lstrip('ID'))
        with open(out_text, 'w') as f:
            f.write(text)
        print("Done.")

    if out_table:
        print(f"Writing table of missing images to {out_table}.")
        missing.to_csv(out_table, index=False)
        print("Done.")

    return missing

def get_bids_entities(file, final_entity='modality', remove_ext_pattern='(.nii.gz)|(.nii)$'):
    stem = os.path.basename(file)
    stem = re.sub(remove_ext_pattern, '', stem)
    pairs = stem.split('_')
    entities = {}
    for p in pairs:
        if '-' in p:
            i = p.index('-')
            entities[p[:i]] = p[i+1:]
        else:
            entities[final_entity] = p

    return entities

def get_shape(imgpath):
    try:
        nii = nib.load(imgpath)
        shape = nii.shape
        return shape
    except Exception:
        return None

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

def link_modalities(tau, amyloid, t1, subject_col='Subject',
                    date_col='ScanDate', tracer_col='Tracer',
                    tau_amyloid_threshold='365D', verbose=True,
                    extra_tau_columns=None, extra_amyloid_columns=None,
                    extra_t1_columns=None):
    vprint = print if verbose else lambda *args, **kwargs: None

    extra_tau_columns = [] if extra_tau_columns is None else extra_tau_columns
    extra_amyloid_columns = [] if extra_amyloid_columns is None else extra_amyloid_columns
    extra_t1_columns = [] if extra_t1_columns is None else extra_t1_columns

    tau = tau[[subject_col, date_col, tracer_col] + extra_tau_columns]
    amyloid = amyloid[[subject_col, date_col, tracer_col] + extra_amyloid_columns]

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
    t1 = t1[[subject_col, date_col] + extra_t1_columns]
    tmp = t1.drop(subject_col, axis=1).copy()
    tmp.columns = tmp.columns + 'T1'
    tmp[subject_col] = t1[subject_col]

    addt1 = grouped.merge(tmp, on=subject_col,
                          how='left', suffixes=(None, t1_suffix))
    addt1 = addt1.loc[~ addt1[t1_date].isna(), :].copy()

    addt1[t1_date] = pd.to_datetime(addt1[t1_date])
    addt1['PETT1Diff'] = addt1['TauAmyloidMeanDate'] - addt1[t1_date]
    addt1['PETT1DiffAbs'] = addt1['PETT1Diff'].abs()
    by_tau_scan = addt1.groupby([subject_col, 'TauAmyloidMeanDate'])['PETT1DiffAbs'].idxmin()
    grouped = addt1.loc[by_tau_scan.values, :]

    # remove duplicates
    grouped = grouped.drop_duplicates(subset=[subject_col, a_date])
    grouped = grouped.drop_duplicates(subset=[subject_col, t_date])

    vprint()
    vprint(f'Subjects with amyloid/tau/T1: {_nstring(grouped, subject_col=subject_col)}')

    vprint()
    vprint('Tracer Table:')
    vprint('-----')
    vprint()

    tracer_tabs = pd.crosstab(grouped[f'{tracer_col}{t_suffix}'], grouped[f'{tracer_col}{a_suffix}'])
    vprint(tracer_tabs)

    return grouped

def load_csv_by_match(directory, pattern, *args, **kwargs):

    output = None
    listdir = os.listdir(directory)
    for file in listdir:
        match = re.search(pattern, file)
        if match:
            output = os.path.join(directory, file)
            break

    if output is not None:
        df = pd.read_csv(output, *args, **kwargs)
        return df
    else:
        raise FileNotFoundError(f'Unable to find file matching "{pattern}" in {directory}')

def load_loni_downloads_with_caching(dataset_key, cachedir, download_folder, use_cached=True):

    target_file = os.path.join(cachedir, f'{dataset_key}_downloadcache.csv')

    downloads = None
    if use_cached and os.path.isfile(target_file):
        print()
        print(f'Using cached file at {target_file}.')
        print('Date last modified: ', dt.datetime.utcfromtimestamp(os.path.getmtime(target_file)).strftime('%Y-%m-%d %H:%M:%S'))
        downloads = pd.read_csv(target_file)

    if downloads is None:
        downloads = list_loni_images(download_folder)
        if not os.path.isdir(cachedir):
            os.mkdir(cachedir)
        downloads.to_csv(target_file, index=False)

    return downloads

def print_missing(df, col):
    data = df[col]
    print(f'Count of missing values for "{col}": {data.isna().sum()}')

def read_loni_collection(csv):
    df = pd.read_csv(csv)
    return df

def read_loni_collection_folder(folder):
    dfs = []
    for file in os.listdir(folder):
        if not file.lower().endswith('csv'):
            continue
        fullpath = os.path.join(folder, file)
        dfs.append(read_loni_collection(fullpath))
    concatted = pd.concat(dfs)
    return concatted

def report_download_coverage(preproc_table, amy_paths='PathAmyloid', tau_paths='PathTau', t1_paths='PathT1',
                             assume_from_na=True):
    df = preproc_table

    present_tau = ~df[tau_paths].isna() if assume_from_na else pd.Series([os.path.isfile(x) for x in df[tau_paths]], index=df.index)
    present_amyloid = ~df[amy_paths].isna() if assume_from_na else pd.Series([os.path.isfile(x) for x in df[amy_paths]], index=df.index)
    present_t1 = ~df[t1_paths].isna() if assume_from_na else pd.Series([os.path.isfile(x) for x in df[t1_paths]], index=df.index)

    print()
    print('DOWNLOAD COVERAGE')
    print('-----------------')
    msg = 'NOTE: Assuming non-NA paths exist (assume_from_na).' if assume_from_na else 'NOTE: Ran search to verify paths exists (! assume_from_na)'
    print()
    print(msg)
    print()
    print(f'Scan groups to process: {len(df)}')
    print(f'All modalities available: {sum((present_tau & present_amyloid) & present_t1)}')
    print()
    print(f'Missing amyloid: {sum(~present_amyloid)}')
    print(f'Missing tau: {sum(~present_tau)}')
    print(f'Missing T1: {sum(~present_t1)}')

def report_feature_distribution(features):
    # report
    print()
    print('DATASET COMPOSITION')
    print('===================')

    print()
    print("Dataset sizes")
    print('-----')
    print(features['Division'].value_counts())

    print()
    print(f"TOTAL: {len(features)}")

    print()
    print('Training set (baseline)')
    print('-----')
    tmp = features.loc[features['Division'].eq('BaselineTraining')]
    print(pd.crosstab(tmp['AmyloidPositive'], tmp['CDRBinned'], dropna=False))

    print()
    print('Validation (baseline)')
    print('-----')
    tmp = features.loc[features['Division'].eq('BaselineValidation')]
    print(pd.crosstab(tmp['AmyloidPositive'], tmp['CDRBinned'], dropna=False))

    print()
    print('Validation tracer (baseline)')
    print('-----')
    print(pd.crosstab(tmp['TracerAmyloid'], tmp['TracerTau']))

def report_missingness(features):
    print()
    print('MISSINGNESS')
    print('-----------')
    print_missing(features, 'Age')
    print_missing(features, 'SexMale')
    print_missing(features, 'HasE4')
    print_missing(features, 'AmyloidPositive')
    print_missing(features, 'CDR')
