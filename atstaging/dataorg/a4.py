import os

import pandas as pd

from atstaging.dataorg.utils import (
    add_features_by_date, 
    add_features_by_subject,
    assign_training_validation,
    bin_cdr,
    link_modalities,
    report_download_coverage,
    report_feature_distribution,
    report_missingness,
)

def a4_image_table(directory, basedate):
    paths = [os.path.join(directory, x) for x in os.listdir(directory) if x.endswith('.nii.gz')]
    df = pd.DataFrame({'Path': paths})
    df['Basename'] = df['Path'].apply(os.path.basename)
    df['Subject'] = df['Basename'].str.extract('(B\d+)', expand=False)
    df['Visit'] = df['Basename'].str.extract('(?<=_)(\d{3})(?=\.nii\.gz)', expand=False)
    df['Cohort'] = df['Basename'].str.extract('^([a-zA-Z0-9]+)(?=_)', expand=False)
    df = df[df['Visit'].ne('999')]
    df['ScanDate'] = basedate + pd.to_timedelta(df['Visit'].astype(int), unit='W')
    return df

def create_preproc_table(fbp_directory, ftp_directory, t1_directory,
                         basedate=pd.Timestamp(year=2001, month=1, day=1)):
    amyloid = a4_image_table(fbp_directory, basedate)
    amyloid['Tracer'] = 'FBP'
    
    tau = a4_image_table(ftp_directory, basedate)
    tau['Tracer'] = 'FTP'
    
    mri = a4_image_table(t1_directory, basedate)
    
    linked = link_modalities(
        tau=tau,
        amyloid=amyloid,
        t1=mri,
        date_col='ScanDate',
        tracer_col='Tracer',
        extra_amyloid_columns=['Visit', 'Path', 'Cohort'],
        extra_tau_columns=['Visit', 'Path'],
        extra_t1_columns=['Visit', 'Path']
    )
    linked = linked.sort_values(['Subject', 'VisitTau'])
    linked['BASEDATE'] = basedate

    report_download_coverage(linked)

    return linked

def create_feature_table(preproc, path_a4_subjinfo, path_a4_petva, path_a4_cdr, basedate):
    # Age, SexMale, HasE4, AmyloidPositive, CDR, CDRSumBoxes, CDRBinned
    features = preproc.copy()
    
    subjinfo = pd.read_csv(path_a4_subjinfo)
    features = add_features_by_subject(features, subjinfo, fields=['AGEYR', 'SEX', 'APOEGNPRSNFLG'],
                                       a_subject='Subject', b_subject='BID')
    features['BaselineAge'] = features['AGEYR']
    features['Age'] = features['AGEYR'] + (pd.to_timedelta(features['VisitTau'].astype(int), unit='W').dt.total_seconds() / (60 * 60 * 24 * 365.25))
    features['SexMale'] = features['SEX'].eq(2).astype(float)
    features['HasE4'] = features['APOEGNPRSNFLG'].astype(float)
    
    petva = pd.read_csv(path_a4_petva)
    features = add_features_by_subject(features, petva, fields=['overall_score'],
                                       a_subject='Subject', b_subject='BID')
    features['AmyloidPositive'] = features['overall_score'].eq('positive').astype(float)
    
    cdr = pd.read_csv(path_a4_cdr)
    cdr['Date'] = basedate + pd.to_timedelta(cdr['VISCODE'], unit='W')
    features = add_features_by_date(features, cdr, fields=['CDGLOBAL', 'CDRSB'],
                                    a_subject='Subject', b_subject='BID',
                                    a_date='TauAmyloidMeanDate', b_date='Date',
                                    b_name='CDR')
    features['CDR'] = features['CDGLOBAL']
    features['CDRSumBoxes'] = features['CDRSB']
    features['CDRBinned'] = bin_cdr(features['CDGLOBAL'])
    
    features = features[list(preproc.columns) + ['Age', 'SexMale', 'HasE4', 'AmyloidPositive', 'CDR', 'CDRSumBoxes', 'CDRBinned']]
    report_missingness(features)
    
    final = assign_training_validation(features)
    report_feature_distribution(final)

    return final