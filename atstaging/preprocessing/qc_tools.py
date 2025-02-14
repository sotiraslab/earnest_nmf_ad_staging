#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 19 10:48:35 2024

@author: earnestt1234
"""

import datetime as dt
import os
import re
import warnings

import nibabel as nib
import numpy as np
import pandas as pd

from atstaging.preprocessing.pipeline import paths_folder_to_dataframe

def create_filecounts(preproc_dir, paths_table):
    
    rows = []
    
    for sub in os.listdir(preproc_dir):
        sub_dir = os.path.join(preproc_dir, sub)
        if not os.path.isdir(sub_dir) or not sub.startswith('sub-'):
            continue
        sub = sub.removeprefix('sub-')
    
        for ses in os.listdir(sub_dir):
            ses_dir = os.path.join(sub_dir, ses)
            if not os.path.isdir(ses_dir) or not ses.startswith('ses-'):
                continue
            ses = ses.removeprefix('ses-')
    
            anat_dir = os.path.join(ses_dir, 'anat')
            pet_dir = os.path.join(ses_dir, 'pet')
    
            row = {}
            row['Subject'] = sub
            row['Session'] = ses
    
            # get expected preproc outputs from path table
            try:
                
                selection = paths_table[paths_table['Subject'].eq(sub) & paths_table['Session'].eq(ses)]
                expected = list(selection.iloc[0, :])
                row['InPathTable'] = True
            except Exception:
                expected = []
                row['InPathTable'] = False
                
            # record files
            if os.path.isdir(anat_dir):
                anat_names = [file for file in os.listdir(anat_dir) if not file.startswith('.')]
                anat_files = [os.path.join(anat_dir, file) for file in anat_names]
    
                row['AnatDir'] = True
                row['AnatFiles'] = len(anat_files)
                row['AnatPreprocFiles'] = len([f for f in anat_files if f in expected])
                row['AnatNIFTI'] = len([f for f in anat_files if f.endswith('.nii.gz')])
                row['AnatPNG'] = len([f for f in anat_files if f.endswith('.png')])
                row['AnatMAT'] = len([f for f in anat_files if f.endswith('.mat')])
                row['AnatJSON'] = len([f for f in anat_files if f.endswith('.json')])
                row['AnatCSV'] = len([f for f in anat_files if f.endswith('.csv')])
    
            else:
                row['AnatDir'] = False
                row['AnatFiles'] = 0
                row['AnatPreprocFiles'] = 0
                row['AnatNIFTI'] = 0
                row['AnatPNG'] = 0
                row['AnatMAT'] = 0
                row['AnatJSON'] = 0
                row['AnatCSV'] = 0
    
            if os.path.isdir(pet_dir):
                pet_names = [file for file in os.listdir(pet_dir) if not file.startswith('.')]
                pet_files = [os.path.join(pet_dir, file) for file in pet_names]
    
                row['PetDir'] = True
                row['PetFiles'] = len(pet_files)
                row['PetPreprocFiles'] = len([f for f in pet_files if f in expected])
                row['PetNIFTI'] = len([f for f in pet_files if f.endswith('.nii.gz')])
                row['PetPNG'] = len([f for f in pet_files if f.endswith('.png')])
                row['PetMAT'] = len([f for f in pet_files if f.endswith('.mat')])
                row['PetJSON'] = len([f for f in pet_files if f.endswith('.json')])
                row['PetCSV'] = len([f for f in pet_files if f.endswith('.csv')])
    
            else:
                row['PetDir'] = False
                row['PetFiles'] = 0
                row['PetPreprocFiles'] = 0
                row['PetNIFTI'] = 0
                row['PetPNG'] = 0
                row['PetMAT'] = 0
                row['PetJSON'] = 0
                row['PetCSV'] = 0
    
            rows.append(row)
    
    filecounts = pd.DataFrame(rows)

    return filecounts

def _backup(old_qctable, new_qctable, backup_dir, qctable_name):
    
    if not os.path.isdir(backup_dir):
        os.mkdir(backup_dir)

    existing_backups = [os.path.join(backup_dir, file) for file in os.listdir(backup_dir)]
    if existing_backups:
        most_recent = max(existing_backups, key=os.path.getctime)
    else:
        most_recent = None

    try:
        backup_qctable = pd.read_csv(most_recent, dtype={'Subject':str, 'Session':str})
    except Exception:
        backup_qctable = None

    # Skip case 1: old is same as new
    if old_qctable.equals(new_qctable):
        print()
        print('-> BACKUP: Skipping backup; existing screenshot QC table and new one are equal.')
        return

    # Skip case 2: old is the same as most recent backup
    elif (backup_qctable is not None) and old_qctable.equals(backup_qctable):
        print()
        print('-> BACKUP: Skipping backup; existing screenshot QC table is equal to most recent backup.')
        return

    # proceed with backup
    tag = dt.datetime.now().strftime('%Y%m%d%H%M%S')
    path = os.path.join(backup_dir, f'{qctable_name}_{tag}.csv')
    old_qctable.to_csv(path, index=False)

def _symlink(src, dest):
    # https://stackoverflow.com/questions/8299386/modifying-a-symlink-in-python

    if not os.path.exists(dest):
        os.symlink(src, dest)

    else:
        tmp = dest + '.new'
        os.symlink(src, tmp)
        os.replace(tmp, dest)

def create_imagestats(preproc_dir, paths_table,
                      include=('t1_fullwarp', 't1_registered', 'amyloid_origsuvr', 'amyloid_registered', 'tau_origsuvr', 'tau_registered'),
                      zcols=('Min', 'Max', 'Mean', 'NonZeroMin', 'NonZeroMax', 'NonZeroMean'),
                      verbose=True):
    
    vprint = print if verbose else lambda *args, **kwargs: None

    vprint()
    vprint('COMPUTING IMAGE STATISTICS')
    vprint('--------------------------')
        
    output = []
    total = len(paths_table) * len(include)

    for c, column in enumerate(include):

        vprint()
        vprint(f'*** *** *** IMAGE KEY: {column} [{c+1}/{len(include)}] *** *** ***')
        vprint()
            
        rows = []
        
        for i, index in enumerate(paths_table.index):

            sub = paths_table.loc[index, 'Subject']
            ses = paths_table.loc[index, 'Session']
            
            z = c * len(paths_table)
            pct = round(((z + i + 1)/total) * 100, 2)
            vprint(f'  > #{i}, Index={index}, Subject={sub}, Session={ses} [{pct}%]')
            
            row = {}
            row['Subject'] = sub
            row['Session'] = ses
            row['Index'] = index

            try:
                imginfo = imagestats(paths_table.loc[index, column])
            except Exception as e:
                print('* FAILURE: Error while processing image.')
                print('!!! !!! !!! !!!')
                print(repr(e))
                print('!!! !!! !!! !!!')
            row.update(imginfo)

            rows.append(row)

        df = pd.DataFrame(rows)
        for col in zcols:
            newcol = 'Z' + col
            df[newcol] = (df[col] - df[col].mean()) / df[col].std()
            
        output.append(df)

    return output

def create_musestats(paths_table, pettype):

    pettype = pettype.lower()
    if pettype == 'a':
        pettype = 'amyloid'
    if pettype == 't':
        pettype = 'tau'
    if pettype not in ['amyloid', 'tau']:
        raise ValueError('`pettype` must be "amyloid" or "tau"')

    # load the MUSE stats for each subject
    muse_column = f'{pettype}_musestats'
    dfs = []

    for index in paths_table.index:

        sub = paths_table.loc[index, 'Subject']
        ses = paths_table.loc[index, 'Session']
        muse_path = paths_table.loc[index, muse_column]

        try:
            muse = pd.read_csv(muse_path)
            muse = muse[['Name', 'MUSEVolume', 'MUSEAverage']]
            muse.insert(0, 'Subject', sub)
            muse.insert(1, 'Session', ses)
            dfs.append(muse)
        except Exception as e:
            print()
            print(f'* FAILURE: Error while loading stats for Subject={sub}, Session={ses}.')
            print('!!! !!! !!! !!!')
            print(repr(e))
            print('!!! !!! !!! !!!')

    # create dataframe with all stats and reshape from long to wide
    allmuse = pd.concat(dfs)
    allmuse = allmuse.pivot(columns='Name', index=['Subject', 'Session'], values=['MUSEVolume', 'MUSEAverage'])
    coltype = allmuse.columns.get_level_values(0)
    region = allmuse.columns.get_level_values(1)
    allmuse.columns = region + coltype.map({'MUSEVolume': '_VOLUME', 'MUSEAverage': '_SUVR'})
    allmuse = allmuse[sorted(allmuse.columns)]
    allmuse = allmuse.reset_index()

    return allmuse
    
def create_screenshotQC(preproc_dir, paths_table, output_dir, save_behavior='update', backup=True, missing_str='<MISSING>'):
    # fixed variables
    qc_img_cols = [col for col in paths_table.columns if 'qc-' in col]
    qctable_name = 'screenshotQC'
    qctable_savepath = os.path.join(output_dir, f'{qctable_name}.csv')
    backup_dir = os.path.join(output_dir, "backup")
    screenshots_dir = os.path.join(output_dir, 'screenshots')

    if not os.path.isdir(screenshots_dir):
        os.mkdir(screenshots_dir)
    
    # Create the symlinks to all PNG images
    # Also create a CSV record for tracking QC
    rows = []

    for index in paths_table.index:
    
        sub = paths_table.loc[index, 'Subject']
        ses = paths_table.loc[index, 'Session']
    
        row = {}
        row['Subject'] = sub
        row['Session'] = ses
        row['Index'] = index
        
        for col in qc_img_cols:
            linkdir = os.path.join(screenshots_dir, col)
            if not os.path.isdir(linkdir):
                os.mkdir(linkdir)
    
            src = paths_table.loc[index, col]
            dest = os.path.join(linkdir, f"sub-{sub}_ses-{ses}.png")
    
            if os.path.isfile(src):
                row[f'{col}_PASS'] = np.nan
                row[f'{col}_NOTE'] = ''
                _symlink(src, dest)
            else:
                row[f'{col}_PASS'] = missing_str
                row[f'{col}_NOTE'] = missing_str
    
        rows.append(row)
    
    new_qctable = pd.DataFrame(rows)
    
    # read in existing table and backup if desired
    try:
        old_qctable = pd.read_csv(qctable_savepath, dtype={'Subject':str, 'Session':str})
    except FileNotFoundError:
        old_qctable = None
    
    if (old_qctable is not None) and backup:
        _backup(old_qctable=old_qctable, new_qctable=new_qctable, backup_dir=backup_dir, qctable_name=qctable_name)

    # save the new qc table
    if save_behavior == 'overwrite':
        new_qctable.to_csv(qctable_savepath, index=False)
    elif (save_behavior == 'update') and (old_qctable is None):
        new_qctable.to_csv(qctable_savepath, index=False)
    elif (save_behavior == 'update') and (old_qctable is not None):
        updater = old_qctable.drop(columns=['Index'])
        updater = updater.set_index(['Subject', 'Session'])
        new_qctable = new_qctable.set_index(['Subject', 'Session'])
        new_qctable.update(updater)
        new_qctable = new_qctable.reset_index()
        new_qctable.to_csv(qctable_savepath, index=False)
    elif (save_behavior == 'none') and (old_qctable is None):
        new_qctable.to_csv(qctable_savepath, index=False)
    elif (save_behavior == 'none') and (old_qctable is not None):
        pass
    else:
        raise ValueError(f'`save_behavior` must be "update", "overwrite", or "none", not "{save_behavior}"')

    return 

def create_epilogues(preproc_dir, extension='.slurmlog'):

    if extension is None:
        extension = ''

    logdir = os.path.join(preproc_dir, 'logs')
    logfiles = [os.path.join(logdir, log) for log in os.listdir(logdir) if log.endswith(extension)]

    rows = []
    
    for log in logfiles:

        with open(log, 'r') as f:
            logtext = f.read()
        
        start = re.search('Begin Slurm Epilogue', logtext)
        end = re.search('End Slurm Epilogue', logtext)
        
        if (not start) or (not end):
            warnings.warn(f'Unable to parse SLURM epilogue for log {log}.', RuntimeWarning)
            continue
        
        epilogue = logtext[start.start():end.end()]
        colon_lines = [line for line in epilogue.splitlines() if ' : ' in line]
        split_by_colon = [line.split(' : ') for line in colon_lines]
        key_value_pairs = {k.strip(): v.strip() for k, v in split_by_colon}

        row = {}
        row['Log'] = log
        row.update(key_value_pairs)

        rows.append(row)

    epilogues = pd.DataFrame(rows)
    return epilogues

def setup_qc(preproc_dir, screenshot_save_behavior='update', screenshot_backup=True, rerun_imagestats=False):

    QC_DIR = os.path.join(preproc_dir, 'qc')
    PATH_FILECOUNTS = os.path.join(QC_DIR, 'filecounts.csv')
    PATH_EPILOGUES = os.path.join(QC_DIR, 'epilogues.csv')
    PATH_IMAGESTATS = os.path.join(QC_DIR, 'imagestats.xlsx')
    PATH_MUSEAMYLOID = os.path.join(QC_DIR, 'musestats_amyloid.csv')
    PATH_MUSETAU = os.path.join(QC_DIR, 'musestats_tau.csv')

    print()
    print('QC Setup')
    print('--------')
    print(f'Directory: {preproc_dir}')

    print()
    print('> Loading image paths from paths sub folder...')
    paths_dir = os.path.join(preproc_dir, 'paths')
    paths_table = paths_folder_to_dataframe(paths_dir)
    print('> Done.')

    print()
    print('> Creating QC directory...')
    if not os.path.isdir(QC_DIR):
        os.mkdir(QC_DIR)
    print(f'> Done.  [{QC_DIR}]')

    print()
    print('> Tallying file counts for preprocessing outputs.')
    filecounts = create_filecounts(preproc_dir, paths_table)
    filecounts.to_csv(PATH_FILECOUNTS, index=False)
    print(f'> Done.  [{PATH_FILECOUNTS}]')

    print()
    print('> Creating table of parsed SLURM epilogues..')
    epilogues = create_epilogues(preproc_dir)
    epilogues.to_csv(PATH_EPILOGUES, index=False)
    print(f'> Done.  [{PATH_EPILOGUES}]')

    print()
    print('> Setting up screenshot link directories and QC record')
    create_screenshotQC(
        preproc_dir=preproc_dir,
        paths_table=paths_table,
        output_dir=QC_DIR,
        save_behavior=screenshot_save_behavior,
        backup=screenshot_backup,
        missing_str='<MISSING>'
    )
    print(f'> Done.  [see {QC_DIR}]')

    print()
    print('> Creating descriptive statistics for images.')
    if os.path.isfile(PATH_IMAGESTATS) and not rerun_imagestats:
        print('> Existing image statistics found; not rerunning.')
    else:
        include=('t1_fullwarp', 't1_registered', 'amyloid_origsuvr', 'amyloid_registered', 'tau_origsuvr', 'tau_registered')
        zcols=('Min', 'Max', 'Mean', 'NonZeroMin', 'NonZeroMax', 'NonZeroMean')
        tables = create_imagestats(
            preproc_dir=preproc_dir,
            paths_table=paths_table,
            zcols=zcols,
            include=include)
        write_imagestats_excel(
            output=tables,
            sheetnames=include,
            destination=PATH_IMAGESTATS
        )
    print(f'> Done.  [{PATH_IMAGESTATS}]')

    print()
    print('> Creating table of MUSE statistics for amyloid.')
    amystats = create_musestats(paths_table=paths_table, pettype='amyloid')
    amystats.to_csv(PATH_MUSEAMYLOID, index=False)
    print(f'> Done.  [{PATH_MUSEAMYLOID}]')

    print()
    print('> Creating table of MUSE statistics for tau.')
    taustats = create_musestats(paths_table=paths_table, pettype='tau')
    taustats.to_csv(PATH_MUSETAU, index=False)
    print(f'> Done.  [{PATH_MUSETAU}]')
    
def imagestats(nifti_path):
    
    nii = nib.load(nifti_path)
    data = nii.get_fdata()
    nonzero = np.where(data == 0, np.nan, data)
    shape = {i:nii.shape[i] for i in range(len(nii.shape))}

    # setup return data
    res = {}

    res['Path'] = nifti_path
    res['Basename'] = os.path.basename(nifti_path)

    for k, v in shape.items():
        res[f"Dim{k}"] = v

    res['Min'] = data.min()
    res['Max'] = data.max()
    res['Mean'] = data.mean()
    res['Voxels'] = data.size

    res['NonZeroMin'] = np.nanmin(nonzero)
    res['NonZeroMax'] = np.nanmax(nonzero)
    res['NonZeroMean'] = np.nanmean(nonzero)
    res['NonZeroVoxels'] = np.sum(~ np.isnan(nonzero))

    return res

def write_imagestats_excel(output, sheetnames, destination):
        
    with pd.ExcelWriter(destination) as writer:
        for df, name in zip(output, sheetnames):
            df.to_excel(writer, sheet_name=name, index=False)