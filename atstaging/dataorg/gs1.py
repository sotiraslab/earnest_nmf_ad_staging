
import numpy as np
import pandas as pd

from atstaging.dataorg.utils import (
    add_features_by_date,
    add_features_by_subject,
    apply_amyloid_pos_filter,
    assign_training_validation,
    bin_cdr, 
    link_modalities,
    load_csv_by_match,
    report_download_coverage,
    report_feature_distribution,
    report_missingness
    )

def create_subject_table(pet_search, mri_search):
    
    # read files
    pet = pd.read_csv(pet_search, dtype={'Subject ID': str})
    mri = pd.read_csv(mri_search, dtype={'Subject ID': str})
                                        
    # prepare PET data
    # "S" is added to subject to avoid str/numeric confusion
    pet['Subject'] = 'S' + pet['Subject ID']
    pet['ScanDate'] = pd.to_datetime(pet['Study Date'])
    pet['ImageID'] = pet['Image ID']
    prot = pet['Imaging Protocol'].str.removeprefix('Radiopharmaceutical=')
    pet['Tracer'] = prot.map(
        {
            '18F-Flutemetamol': 'FMT',
            '18F-Florbetaben': 'FBB',
            '18F-Florbetapir': 'FBP',
            '18F-FDG': 'FDG',
            '18F-AV-1451': 'FTP'
        }
    )

    amy = pet[pet['Tracer'].isin(['FMT', 'FBB', 'FBP'])].copy()
    tau = pet[pet['Tracer'].eq('FTP')].copy()

    # prepare MRI data
    t1 = mri[mri['Description'].eq('3D T1-weighted')].copy()
    t1['Subject'] = 'S' + t1['Subject ID']
    t1['ScanDate'] = pd.to_datetime(t1['Study Date'])
    t1['ImageID'] = t1['Image ID']

    # merge
    merged = link_modalities(
        amyloid=amy,
        tau=tau,
        t1=t1,
        subject_col='Subject',
        date_col='ScanDate',
        extra_amyloid_columns=['ImageID'],
        extra_tau_columns=['ImageID'],
        extra_t1_columns=['ImageID']
    )
    
    merged['ImageIDTau'] = 'I' + merged['ImageIDTau'].astype(str)
    merged['ImageIDAmyloid'] = 'I' + merged['ImageIDAmyloid'].astype(str)
    merged['ImageIDT1'] = 'I' + merged['ImageIDT1'].astype(str)

    return merged

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

    features = preproc_table.copy() 

    # load tables
    demo = load_csv_by_match(tabular_folder, 'demographics', dtype={'Subject Identifier for the Study': str})
    gene = load_csv_by_match(tabular_folder, 'pharmacogenomics', dtype={'Subject Identifier for the Study': str})
    imag = load_csv_by_match(tabular_folder, 'imaging', dtype={'Subject Identifier for the Study': str})
    ques = load_csv_by_match(tabular_folder, 'questionnaires', dtype={'Subject Identifier for the Study': str})

    # Age, Sex
    demo = demo[['Subject Identifier for the Study', 'Age', 'Sex']]
    demo['Subject'] = 'S' + demo['Subject Identifier for the Study']
    demo['SexMale'] = demo['Sex'].eq('M').astype(float)
    features = add_features_by_subject(features, demo, fields=['Age', 'SexMale'], a_subject='Subject', b_subject='Subject')

    # APOE
    gene['Subject'] = 'S' + gene['Subject Identifier for the Study']
    gene['HasE4'] = gene['Result or Finding in Original Units'].str.contains('E4').astype(float)
    features = add_features_by_subject(features, gene, fields=['HasE4'], a_subject='Subject', b_subject='Subject')

    # AmyloidPositive
    imag['Subject'] = 'S' + imag['Subject Identifier for the Study']
    imag['Date'] = imag['Date/Time of Imaging Assessment']
    imag = imag.loc[imag['Imaging Assessment Test Name'].eq('CENTILOID'), ['Subject', 'Date', 'Character Result/Finding in Std Format']]
    imag['Centiloid'] = imag['Character Result/Finding in Std Format']
    imag['AmyloidPositive'] = imag['Centiloid'].gt(24).astype(float)
    features = add_features_by_date(features, imag, fields=['Centiloid', 'AmyloidPositive'], a_subject='Subject', b_subject='Subject',
                                    a_date='ScanDateAmyloid', b_date='Date', b_name='Centiloid')

    # CDR
    ques = ques.loc[ques['Question Name'].eq('CDR-Global CDR'), ['Subject Identifier for the Study', 'Date/Time of Finding', 'Finding in Original Units']]
    ques['Subject'] = 'S' + ques['Subject Identifier for the Study']
    ques['Date'] = ques['Date/Time of Finding']
    ques['CDR'] = ques['Finding in Original Units'].map(
        {
            '0 NONE': 0,
            '0.5 QUESTIONABLE': 0.5,
            '1 MILD': 1,
            'NOT APPLICABLE': np.nan
        }
    ) 
    ques['CDRBinned'] = bin_cdr(ques['CDR'])
    features = add_features_by_date(features, ques, fields=['CDR', 'CDRBinned'], a_subject='Subject', b_subject='Subject',
                                    a_date='TauAmyloidMeanDate', b_date='Date', b_name='CDR', drop_missing=False)

    
    report_missingness(features)

    # assign training/validation
    final = apply_amyloid_pos_filter(features)
    final = assign_training_validation(final)

    report_feature_distribution(final)

    return final