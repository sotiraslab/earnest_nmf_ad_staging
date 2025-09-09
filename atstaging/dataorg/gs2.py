
# imports
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
    nan_compare,
    nan_eq,
    report_download_coverage,
    report_feature_distribution,
    report_missingness
    )

def create_preproc_table(pet_search, mri_search, gs2_reorganize_images_csv):

    # read files
    pet = pd.read_csv(pet_search, dtype={'Subject ID': str, 'Image ID': str})
    mri = pd.read_csv(mri_search, dtype={'Subject ID': str, 'Image ID': str})
    reorg = pd.read_csv(gs2_reorganize_images_csv, dtype={'Subject': str})

    # select PET data
    prot = pet['Imaging Protocol'].str.removeprefix('Radiopharmaceutical=')
    pet['ImageID'] = 'I' + pet['Image ID'].astype(str)
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
    t1['ImageID'] = 'I' + t1['Image ID']

    # prepare main table
    reorg['Subject'] = 'S' + reorg['Subject']
    reorg['ScanDate'] = pd.to_datetime(reorg['Date']).dt.floor('D')
    reorg['Path'] = reorg['NIFTIPath']

    # split the nifti record based on modality
    reorg['Modality'] = ''
    reorg.loc[reorg['ImageID'].isin(amy['ImageID']), 'Modality'] = 'AMYLOID'
    reorg.loc[reorg['ImageID'].isin(tau['ImageID']), 'Modality'] = 'TAU'
    reorg.loc[reorg['ImageID'].isin(t1['ImageID']), 'Modality'] = 'T1'

    reorg_amy = reorg[reorg['Modality'].eq('AMYLOID')].copy()
    reorg_tau = reorg[reorg['Modality'].eq('TAU')].copy()
    reorg_t1 = reorg[reorg['Modality'].eq('T1')].copy()

    tracer_merger = amy[['ImageID', 'Tracer']]
    reorg_amy = reorg_amy.merge(tracer_merger, on='ImageID', how='left')

    reorg_tau['Tracer'] = 'FTP'

    # link
    merged = link_modalities(
        amyloid=reorg_amy,
        tau=reorg_tau,
        t1=reorg_t1,
        subject_col='Subject',
        date_col='ScanDate',
        extra_amyloid_columns=['Path','ImageID'],
        extra_tau_columns=['Path','ImageID'],
        extra_t1_columns=['Path','ImageID']
    )

    report_download_coverage(merged, assume_from_na=False)
    
    return merged

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
    demo['SexMale'] = nan_eq(demo['Sex'], 'M')
    features = add_features_by_subject(features, demo, fields=['Age', 'SexMale'], a_subject='Subject', b_subject='Subject')

    # APOE
    gene['Subject'] = 'S' + gene['Subject Identifier for the Study']
    gene['HasE4'] = gene['Result or Finding in Original Units'].str.contains('E4').astype(float)
    features = add_features_by_subject(features, gene, fields=['HasE4'], a_subject='Subject', b_subject='Subject')

    # AmyloidPositive
    imag['Subject'] = 'S' + imag['Subject Identifier for the Study']
    imag['Date'] = imag['Date/Time of Imaging Assessment']
    imag = imag.loc[imag['Imaging Assessment Test Name'].eq('CENTILOID'), ['Subject', 'Date', 'Character Result/Finding in Std Format']]
    imag['Centiloid'] = pd.to_numeric(imag['Character Result/Finding in Std Format'], errors='coerce')
    imag['AmyloidPositive'] = nan_compare(imag['Centiloid'], 'gt', 24)
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
    features['CDRSumBoxes'] = np.nan


    report_missingness(features)

    # assign training/validation
    final = apply_amyloid_pos_filter(features)
    final = assign_training_validation(final)

    report_feature_distribution(final)

    return final