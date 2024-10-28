
import os
import re

import pandas as pd

from atstaging.dataorg.utils import (
    add_features_by_viscode,
    assign_training_validation, 
    link_modalities, 
    load_csv_by_match,
    report_download_coverage,
    report_feature_distribution)

def parse_habs_fields(image_path):
    name = os.path.basename(image_path)
    subject = re.search('P_[A-Za-z0-9_-]{6}', name)
    date = re.search('\d{4}-\d{2}-\d{2}', name)
    phase = re.search(r'HAB_\d\.\d', name)
    window = re.search(r'\d{2}-\d{3}(?=\.nii\.gz)', name)

    d = {'Path': image_path}
    if subject:
        d['Subject'] = subject.group()
    if date:
        d['ScanDate'] = date.group()
    if phase:
        d['HABSPhase'] = phase.group()
    if window:
        d['AcqWindow'] = window.group()

    return d

def table_habs_images(download_dir):
    rows = []
    for file in os.listdir(download_dir):
        fullfile = os.path.join(download_dir, file)
        if not file.endswith('.nii.gz'):
            continue
        row = parse_habs_fields(fullfile)
        rows.append(row)
    return pd.DataFrame(rows)

def create_preproc_table(tau_downloads, amyloid_downloads, t1_downloads):
    tau = table_habs_images(tau_downloads)
    tau['Tracer'] = 'FTP'

    amyloid = table_habs_images(amyloid_downloads)
    amyloid['Tracer'] = 'PIB'

    t1 = table_habs_images(t1_downloads)

    linked = link_modalities(tau=tau, amyloid=amyloid, t1=t1,
                            extra_amyloid_columns=['Path', 'HABSPhase'],
                            extra_tau_columns=['Path', 'HABSPhase'],
                            extra_t1_columns=['Path', 'HABSPhase'])
    
    report_download_coverage(linked)
    
    return linked

def create_feature_table(preproc_table, habs_tabular_directory, verbose=True):
    clinical = load_csv_by_match(habs_tabular_directory, 'ClinicalMeasures')
    demographics = load_csv_by_match(habs_tabular_directory, 'Demographics')
    pib = load_csv_by_match(habs_tabular_directory, 'PIB')

    features = preproc_table.copy()

    features = add_features_by_viscode(features, demographics, fields=['NP_Age', 'BiologicalSex', 'E4_Status'],
                                    a_subject='Subject', b_subject='SubjID',
                                    a_viscode='HABSPhaseTau', b_viscode='StudyArc')
    features = add_features_by_viscode(features, clinical, fields=['CDR_Global', 'CDR_SB'],
                                    a_subject='Subject', b_subject='SubjIDshort',
                                    a_viscode='HABSPhaseTau', b_viscode='StudyArc')
    features = add_features_by_viscode(features, pib, fields=['PIB_FS_SUVR_Group'],
                                    a_subject='Subject', b_subject='SubjIDshort',
                                    a_viscode='HABSPhaseTau', b_viscode='StudyArc')
    # recoding
    features['Age'] = features['NP_Age']
    features['SexMale'] = features['BiologicalSex'].eq('M').astype(float)
    features['HasE4'] = features['E4_Status'].eq('e4+').astype(float)
    features['AmyloidPositive'] = features['PIB_FS_SUVR_Group'].eq('PIB+').astype(float)
    features['CDR'] = features['CDR_Global']
    features['CDRSumBoxes'] = features['CDR_SB']
    features['CDRBinned'] = features['CDR']
    features.loc[features['CDR'].ge(1.0), 'CDRBinned'] = 1.0
    features['CDRBinned'] = features['CDRBinned'].map({0.0: '0.0', 0.5: '0.5', 1.0: '1.0+'})
    features['CDR'].value_counts()

    # filter columns
    keep_columns = list(preproc_table.columns) + ['Age', 'SexMale', 'HasE4', 'AmyloidPositive', 'CDR', 'CDRSumBoxes', 'CDRBinned']
    features_small = features[keep_columns]

     # add dataset assignment
    output = assign_training_validation(features_small)

    if verbose:
        report_feature_distribution(output)

    return output
