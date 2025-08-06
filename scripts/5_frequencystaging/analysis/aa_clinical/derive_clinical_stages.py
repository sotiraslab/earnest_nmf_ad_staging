
# IMPORTS
# =====

import os

import numpy as np
import pandas as pd

from atstaging.config import get, set_config
from atstaging.dataorg.utils import add_features_by_date, load_csv_by_match
from atstaging.outputs import load_split

set_config('main')

# HELPER FUNCTIONS
# =====
def a4_viscode_to_date(viscode, basedate=pd.Timestamp(year=2001, month=1, day=1)):
    date = basedate + pd.to_timedelta(viscode, unit='W')
    date[viscode > 700] = np.nan
    return date

def oasis_days_to_date(days, basedate=pd.Timestamp(year=2001, month=1, day=1)):
    date = basedate + pd.to_timedelta(days, unit='D')
    return date

def assemble_pacc_a4(df, fcsrt, logimem, digits, mmse, a_subject='Subject', a_date='Date', basedate=pd.Timestamp(year=2001, month=1, day=1)):

    fcsrt['Subject'] = fcsrt['BID']
    fcsrt['Date'] = a4_viscode_to_date(fcsrt['VISCODE'], basedate=basedate)
    fcsrt['FCSRTTotal'] = fcsrt['FCTOTF'] + 	fcsrt['FCTOTC']

    logimem['Subject'] = logimem['BID']
    logimem['Date'] = a4_viscode_to_date(logimem['VISCODE'], basedate=basedate)
    logimem['LogicalMemoryDelayedRecall'] = logimem['LDELTOTAL']

    digits['Subject'] = digits['BID']
    digits['Date'] = a4_viscode_to_date(digits['VISCODE'], basedate=basedate)
    digits['DigitSymbolSubstitution'] = digits['DIGITTOTAL']

    mmse['Subject'] = mmse['BID']
    mmse['Date'] = a4_viscode_to_date(mmse['VISCODE'], basedate=basedate)
    mmse['MMSE'] = mmse['MMSCORE']

    df = add_features_by_date(a=df, b=fcsrt, fields=['FCSRTTotal'], a_subject=a_subject, a_date=a_date, include_gap_cols=False)
    df = add_features_by_date(a=df, b=logimem, fields=['LogicalMemoryDelayedRecall'], a_subject=a_subject, a_date=a_date, include_gap_cols=False)
    df = add_features_by_date(a=df, b=digits, fields=['DigitSymbolSubstitution'], a_subject=a_subject, a_date=a_date, include_gap_cols=False)
    df = add_features_by_date(a=df, b=mmse, fields=['MMSE'], a_subject=a_subject, a_date=a_date, include_gap_cols=False)

    return df
    
def assemble_pacc_adni(df, neurobat, mmse, adas, a_subject='Subject', a_date='Date'):
    
    neurobat = neurobat[['PTID', 'VISDATE', 'LDELTOTAL', 'TRABSCOR']].copy()
    neurobat.columns = ['Subject', 'Date', 'LogicalMemoryDelayedRecall', 'TrailsB']
    neurobat['Subject'] = neurobat['Subject'].str.replace('_', '')
    
    mmse = mmse[['PTID', 'VISDATE', 'MMSCORE']].copy()
    mmse.columns = ['Subject', 'Date', 'MMSE']
    mmse['Subject'] = mmse['Subject'].str.replace('_', '')
    
    adas = adas[['PTID', 'USERDATE', 'Q4SCORE']].copy()
    adas.columns = ['Subject', 'Date', 'ADASDelayedRecall']
    adas['Subject'] = adas['Subject'].str.replace('_', '')

    df = add_features_by_date(a=df, b=neurobat, fields=['LogicalMemoryDelayedRecall', 'TrailsB'], include_gap_cols=False, a_subject=a_subject, a_date=a_date)
    df = add_features_by_date(a=df, b=mmse, fields=['MMSE'], include_gap_cols=False, a_subject=a_subject, a_date=a_date)
    df = add_features_by_date(a=df, b=adas, fields=['ADASDelayedRecall'], include_gap_cols=False, a_subject=a_subject, a_date=a_date)

    return df

def assemble_pacc_habs(df, cognition, clinical, a_subject='Subject', a_date='Date'):

    cognition['Subject'] = cognition['SubjIDshort'].str.replace('_', '')
    cognition['Date'] = cognition['NP_SessionDate']
    cognition['FCSRTTotal'] = cognition['FCsrt_FNC']
    cognition['LogicalMemoryDelayedRecall'] = cognition['LogicMem_DR']
    cognition['DigitSymbolSubstitution'] = cognition['DigitSym']

    clinical['Subject'] = clinical['SubjIDshort'].str.replace('_', '')
    clinical['Date'] = clinical['NP_SessionDate']
    clinical['MMSE'] = clinical['MMSE_Total']
    
    df = add_features_by_date(a=df, b=cognition, fields=['FCSRTTotal', 'LogicalMemoryDelayedRecall', 'DigitSymbolSubstitution'], a_date=a_date, a_subject=a_subject, include_gap_cols=False)
    df = add_features_by_date(a=df, b=clinical, fields=['MMSE'], a_date=a_date, a_subject=a_subject, include_gap_cols=False)

    return df

def assemble_pacc_oasis(df, cognition, clinical, a_subject='Subject', a_date='Date', basedate=pd.Timestamp(year=2001, month=1, day=1)):

    cognition['Subject'] = cognition['OASISID']
    cognition['Date'] = oasis_days_to_date(clinical['days_to_visit'], basedate=basedate)
    cognition['FCSRTTotal'] = cognition['srttotal']
    cognition['LogicalMemoryDelayedRecall'] = cognition['MEMUNITS']
    cognition['DigitSymbolSubstitution'] = cognition['digsym']

    clinical['Subject'] = clinical['OASISID']
    clinical['Date'] = oasis_days_to_date(clinical['days_to_visit'], basedate=basedate)

    df = add_features_by_date(a=df, b=cognition, fields=['FCSRTTotal', 'LogicalMemoryDelayedRecall', 'DigitSymbolSubstitution'], a_date=a_date, a_subject=a_subject, include_gap_cols=False)
    df = add_features_by_date(a=df, b=clinical, fields=['MMSE'], a_date=a_date, a_subject=a_subject, include_gap_cols=False)

    return df

def calculate_pacc(df, columns, cn_mask, min_required=2, higher_better=None, verbose=False):

    vprint = print if verbose else lambda *args, **kwargs: None
    
    cn = df[cn_mask].copy()
    n = len(df)
    k = len(columns)

    normed_scores = pd.DataFrame(np.full((n, k), np.nan))
    normed_scores.columns = columns
    normed_scores.index = df.index
    
    if higher_better is None:
        higher_better = [True] * k

    vprint('')
    for i in range(k):
        col = columns[i]
        mu = cn[col].mean()
        s = cn[col].std()
        z = (df[col] - mu) / s

        vprint(f'{col}: mean={mu}, std={s}')

        if not higher_better[i]:
            z *= -1

        normed_scores[col] = z

    score = np.nansum(normed_scores, axis=1)
    count_present = (~normed_scores.isna()).sum(axis=1)
    score[count_present < min_required] = np.nan

    return score

def select_consistent_cognitively_normal(cdr, subject_col='Subject', date_col='Date', score_col='CDR', required_followup_years=5.0):

    # basic prep of data
    # NOTE: This is assuming the column order is Subject ID, date of assessment, CDR
    # And that there are only 3 columns!
    df = cdr.copy()
    df = df.rename(columns={subject_col: 'Subject', date_col: 'Date', score_col: 'CDR'}, errors='raise')
    df = df[['Subject', 'Date', 'CDR']]
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(['Subject', 'Date']).dropna()
    df['CN'] = df['CDR'].eq(0)

     # calculate followup
    df['YearsSinceBaseline'] = (df['Date'] - df.groupby('Subject')['Date'].transform('first')).dt.total_seconds() / (60 * 60 * 24 * 365.25)

    # Select subjects who have at least the required followup
    max_followup = df.groupby('Subject')['YearsSinceBaseline'].max().reset_index()
    subjects_with_followup = max_followup.loc[max_followup['YearsSinceBaseline'].gt(required_followup_years), 'Subject']

    # Find subjects who remain CN (only during the followup period, okay if they convert after)
    tmp = df[~df['YearsSinceBaseline'].gt(required_followup_years + 1)].copy()
    all_cn = tmp.groupby('Subject')['CN'].all().reset_index()
    subjects_always_cn = all_cn.loc[all_cn['CN'], 'Subject']

    # return selected data
    return df[df['Subject'].isin(subjects_with_followup) & df['Subject'].isin(subjects_always_cn)]

# ===================
# LOAD MASTER
# ===================

master = load_split(None, None, verbose=False)
master = master[[col for col in master.columns if 'PACC' not in col]]

# separate into different datasets with PACC information
master_adni = master.loc[master['DataSet'].eq('ADNI'), ['Subject', 'Session', 'TauAmyloidMeanDate', 'Split', 'ControlForStaging']]
master_a4 = master.loc[master['DataSet'].eq('A4'), ['Subject', 'Session', 'TauAmyloidMeanDate', 'Split', 'ControlForStaging']]
master_oasis = master.loc[master['DataSet'].eq('OASIS'), ['Subject', 'Session', 'TauAmyloidMeanDate', 'Split', 'ControlForStaging']]
master_habs = master.loc[master['DataSet'].eq('HABS'), ['Subject', 'Session', 'TauAmyloidMeanDate', 'Split', 'ControlForStaging']]
master_habshd = master.loc[master['DataSet'].eq('HABSHD'), ['Subject', 'Session', 'TauAmyloidMeanDate', 'Split', 'ControlForStaging']]

# ===================
# COLLECT PACC DATA
# ===================

# ADNI
# =====

# Read in data
cdr = pd.read_csv('/home/tom.earnest/adni_clinical/cdr.csv')
neurobat = pd.read_csv('/home/tom.earnest/adni_clinical/neurobat.csv')
mmse = pd.read_csv('/home/tom.earnest/adni_clinical/mmse.csv')
adas = pd.read_csv('/home/tom.earnest/adni_clinical/adas.csv')

# Select the stable individuals
cdr = cdr[~cdr['PHASE'].isin(['ADNI1', 'ADNIGO', 'ADNI2'])].copy()
cdr['PTID'] = cdr['PTID'].str.replace('_', '')
cn_long = select_consistent_cognitively_normal(cdr, subject_col='PTID', date_col='VISDATE', score_col='CDGLOBAL')
cn_baseline = cn_long[cn_long['YearsSinceBaseline'].eq(0)].copy()

# Add the PACC columns to the data
adni_cn_baseline = assemble_pacc_adni(cn_baseline, neurobat=neurobat, mmse=mmse, adas=adas)
master_adni = assemble_pacc_adni(master_adni, neurobat=neurobat, mmse=mmse, adas=adas, a_date='TauAmyloidMeanDate')

# A4
# =====

# set basedate for 
basedate = pd.Timestamp(year=2001, month=1, day=1)

# Read in data
cdr = pd.read_csv('/home/tom.earnest/a4_clinical/RawData/cdr.csv')
mmse = pd.read_csv('/home/tom.earnest/a4_clinical/RawData/mmse.csv')
fcsrt = pd.read_csv('/home/tom.earnest/a4_clinical/RawData/cogfcsr16.csv')
logimem = pd.read_csv('/home/tom.earnest/a4_clinical/RawData/coglogic.csv')
digits = pd.read_csv('/home/tom.earnest/a4_clinical/RawData/cogdigit.csv')

# Select the stable individuals
cdr['Date'] = basedate + pd.to_timedelta(cdr['VISCODE'], unit='W')
cdr.loc[cdr['VISCODE'].gt(700), 'Date'] = basedate + pd.to_timedelta(cdr['CDDY'], unit='D')
cdr = cdr[['BID', 'Date', 'CDGLOBAL']].copy().dropna().sort_values(['BID', 'Date'])
cdr.columns = ['Subject', 'Date', 'CDR']
cn_long = select_consistent_cognitively_normal(cdr)
cn_baseline = cn_long[cn_long['YearsSinceBaseline'].eq(0)].copy()

# Add the PACC columns to the data
a4_cn_baseline = assemble_pacc_a4(cn_baseline, fcsrt=fcsrt, logimem=logimem, digits=digits, mmse=mmse, a_subject='Subject')
master_a4 = assemble_pacc_a4(master_a4, fcsrt=fcsrt, logimem=logimem, digits=digits, mmse=mmse, a_date='TauAmyloidMeanDate')

# HABS
# =====

cognition = pd.read_csv('/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/HABS/tabular/Cognition_HABS_DataRelease_2.0.csv')
clinical = pd.read_csv('/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/HABS/tabular/ClinicalMeasures_HABS_DataRelease_2.0.csv')

# Select the stable individuals
cdr = clinical[['SubjIDshort', 'NP_SessionDate', 'CDR_Global']].copy().dropna().sort_values(['SubjIDshort', 'NP_SessionDate'])
cdr.columns = ['Subject', 'Date', 'CDR']
cdr['Subject'] = cdr['Subject'].str.replace('_', '')
cn_long = select_consistent_cognitively_normal(cdr)
cn_baseline = cn_long[cn_long['YearsSinceBaseline'].eq(0)].copy()

# Add the PACC columns
habs_cn_baseline = assemble_pacc_habs(cn_baseline, cognition=cognition, clinical=clinical)
master_habs = assemble_pacc_habs(master_habs, cognition=cognition, clinical=clinical, a_date='TauAmyloidMeanDate')

# OASIS
# =====

basedate=pd.Timestamp(year=2001, month=1, day=1)

# load data
clinical = pd.read_csv('/home/tom.earnest/OASIS3_data_files/scans/UDSb4-Form_B4__Global_Staging__CDR__Standard_and_Supplemental/resources/csv/files/OASIS3_UDSb4_cdr.csv')
cognition = pd.read_csv('/home/tom.earnest/OASIS3_data_files/scans/pychometrics-Form_C1__Cognitive_Assessments/resources/csv/files/OASIS3_UDSc1_cognitive_assessments.csv')
clinical['Date'] = oasis_days_to_date(clinical['days_to_visit'], basedate=basedate)
cognition['Date'] = oasis_days_to_date(cognition['days_to_visit'], basedate=basedate)

# Select the stable cognitive individuals
cdr = clinical[['OASISID', 'Date', 'CDRTOT']].copy().dropna().sort_values(['OASISID', 'Date'])
cdr.columns = ['Subject', 'Date', 'CDR']
cn_long = select_consistent_cognitively_normal(cdr)
cn_baseline = cn_long[cn_long['YearsSinceBaseline'].eq(0)].copy()

oasis_cn_baseline = assemble_pacc_oasis(cn_baseline, cognition=cognition, clinical=clinical)
master_oasis = assemble_pacc_oasis(master_oasis, cognition=cognition, clinical=clinical, a_date='TauAmyloidMeanDate')

# HABSHD
# =====

# load tabular data
tabular_folder = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/HABS-HD/tabular/'

tables = [
    'HD_1_African',
    'HD_1_Mexican',
    'HD_1_Non',
    'HD_2_Mexican',
    'HD_2_Non',
    'HD_3_Mexican',
    'HD_3_Non']
habshd = pd.concat([load_csv_by_match(tabular_folder, t, dtype={'Med_ID': str}) for t in tables])
habshd = habshd.drop_duplicates(['Med_ID', 'Visit_ID'])

# load MRI information from LONI to link scan dates
mri = pd.read_csv('/scratch/tom.earnest/atstaging/searches/habshd_t1_10102024_12_05_2024.csv', dtype={'Subject': str})

# select needed columns
df = habshd[['Med_ID', 'Visit_ID', 'CDR_Global', 'LM2_A_Total', 'Digit_Symbol_Substitution', 'MMSE_Total']].copy()
df.columns = ['Subject', 'Visit', 'CDR', 'LogicalMemoryDelayedRecall', 'DigitSymbolSubstitution', 'MMSE']
df[df == -9999] = np.nan

# add date from MRI
linker = mri[['Subject', 'Visit', 'Acq Date']].copy()
linker.columns = ['Subject', 'Visit', 'Date']
linker['Visit'] = linker['Visit'].map({'Baseline': 1, 'Month 24 follow-up': 2, 'Month 48 follow-up': 3, 'Month 72 follow-up': 4})
df = df.merge(linker, on=['Subject', 'Visit'], how='left')

# find stable CNs
cdr = df[['Subject', 'Date', 'CDR']]
cn_long = select_consistent_cognitively_normal(cdr)
cn_baseline = cn_long[cn_long['YearsSinceBaseline'].eq(0)].copy()

# add PACC features
habshd_cn_baseline = add_features_by_date(a=cn_baseline, b=df, fields=['LogicalMemoryDelayedRecall', 'DigitSymbolSubstitution', 'MMSE'], include_gap_cols=False)
habshd_cn_baseline['FCSRTTotal'] = np.nan

master_habshd = add_features_by_date(a=master_habshd, b=df, fields=['LogicalMemoryDelayedRecall', 'DigitSymbolSubstitution', 'MMSE'], include_gap_cols=False, a_date='TauAmyloidMeanDate')
master_habshd['FCSRTTotal'] = np.nan

# SCI PACC CUTOFFs
# ======

# For ADNI PACC, ADNI is the only contributing dataset
adni_pacc_assessments = ['ADASDelayedRecall', 'LogicalMemoryDelayedRecall', 'TrailsB', 'MMSE']
adni_pacc_higher_better = [False, True, False, True]
adni_pacc = calculate_pacc(adni_cn_baseline, cn_mask=[True]*len(adni_cn_baseline), columns=adni_pacc_assessments, higher_better=adni_pacc_higher_better)
adni_pacc_sci_cutoff = np.nanquantile(adni_pacc, 0.1)
print(f'SCI cutoff for ADNI-PACC (10th percentile): {adni_pacc_sci_cutoff}')

# For OG PACC, all other datasets contribute
og_pacc_assessments = ['FCSRTTotal', 'LogicalMemoryDelayedRecall', 'DigitSymbolSubstitution', 'MMSE']
og_pacc_higher_better = [True]*4
combined_cns_for_og_pacc = pd.concat([a4_cn_baseline, habs_cn_baseline, habshd_cn_baseline, oasis_cn_baseline], ignore_index=True)
og_pacc = calculate_pacc(combined_cns_for_og_pacc, cn_mask=[True]*len(combined_cns_for_og_pacc), columns=og_pacc_assessments, higher_better=og_pacc_higher_better)
og_pacc_sci_cutoff = np.nanquantile(og_pacc, 0.1)
print(f'SCI cutoff for original PACC (10th percentile): {og_pacc_sci_cutoff}')

# APPLY PACC
# ======

def atstaging_pacc_computation_helper(df, pacc_type):

    if pacc_type == 'original':
        columns = ['FCSRTTotal', 'LogicalMemoryDelayedRecall', 'DigitSymbolSubstitution', 'MMSE']
        higher_better = [True] * 4
        name = 'PACCOriginal'
    elif pacc_type == 'adni':
        columns = ['ADASDelayedRecall', 'LogicalMemoryDelayedRecall', 'TrailsB', 'MMSE']
        higher_better = [False, True, False, True]
        name = 'PACCADNI'
    else:
        raise ValueError('Did not recognized value for `pacc_type`; must be "adni" or "original"')

    # Compute PACC for training
    training = df.loc[df['Split'].str.contains('Training'), :]
    training_cn_mask = training['ControlForStaging']
    out_training = training.loc[:, ['Subject', 'Session']]
    out_training[name] = calculate_pacc(training, cn_mask=training_cn_mask, columns=columns, higher_better=higher_better)
    
    validation = df.loc[df['Split'].str.contains('Validation'), :]
    validation_cn_mask = validation['ControlForStaging']
    out_validation = validation.loc[:, ['Subject', 'Session']]
    out_validation[name] = calculate_pacc(validation, cn_mask=validation_cn_mask, columns=columns, higher_better=higher_better)

    output = pd.concat([out_training, out_validation])

    return output

pacc_scores_adni = atstaging_pacc_computation_helper(master_adni, 'adni')
pacc_scores_og = atstaging_pacc_computation_helper(pd.concat([master_a4, master_habs, master_habshd, master_oasis]), 'original')

master_pacc = master.merge(pacc_scores_adni, on=['Subject', 'Session'], how='left')
master_pacc = master_pacc.merge(pacc_scores_og, on=['Subject', 'Session'], how='left')

# APPLY CLINICAL STAGING
# =======

master_pacc['AA2024Clinical'] = np.nan
master_pacc['AA2024Clinical'] = np.where(master_pacc['CDRBinned'].eq('1.0+'), 'Stage 4-6', master_pacc['AA2024Clinical'])
master_pacc['AA2024Clinical'] = np.where(master_pacc['CDRBinned'].eq('0.5'), 'Stage 3', master_pacc['AA2024Clinical'])
master_pacc['AA2024Clinical'] = np.where(master_pacc['CDRBinned'].eq('0.0') & master_pacc['PACCADNI'].le(adni_pacc_sci_cutoff), 'Stage 2', master_pacc['AA2024Clinical'])
master_pacc['AA2024Clinical'] = np.where(master_pacc['CDRBinned'].eq('0.0') & master_pacc['PACCOriginal'].le(og_pacc_sci_cutoff), 'Stage 2', master_pacc['AA2024Clinical'])
master_pacc['AA2024Clinical'] = np.where(master_pacc['CDRBinned'].eq('0.0') & master_pacc['PACCADNI'].gt(adni_pacc_sci_cutoff), 'Stage 1', master_pacc['AA2024Clinical'])
master_pacc['AA2024Clinical'] = np.where(master_pacc['CDRBinned'].eq('0.0') & master_pacc['PACCOriginal'].gt(og_pacc_sci_cutoff), 'Stage 1', master_pacc['AA2024Clinical'])
master_pacc['AA2024Clinical'] = np.where(master_pacc['AA2024Clinical'].eq('nan'), np.nan, master_pacc['AA2024Clinical'])

# RESILIENT vs VULNERABLE
# =====

mystage_levels = master_pacc['StageNumeric'].map({'0': 0, '1': 0, '2': 0, '3': 1, '4': 2, '5': 2, '6': 3, 'NS': np.nan}).astype(float)
clinstage_levels = master_pacc['AA2024Clinical'].map({'Stage 1': 0, 'Stage 2': 1, 'Stage 3': 2, 'Stage 4-6': 3}).astype(float)

master_pacc['ResilientVulnerable'] = np.sign(mystage_levels - clinstage_levels).map({1: 'Resilient', 0: 'Expected', -1: 'Vulnerable'})
master_pacc.loc[master_pacc['StageNumeric'].eq('NS'), 'ResilientVulnerable'] = 'Atypical'

# SAVE
# ======

features = master_pacc[['Subject', 'Session', 'PACCOriginal', 'PACCADNI', 'AA2024Clinical', 'ResilientVulnerable']].copy()
root_output = get('output_directory')
opath = os.path.join(root_output, 'masterTables', 'FEATURE_AA2024Clinical.csv')

features.to_csv(opath, index=False)

print(f'Saved stages for {len(features)} subjects at "{opath}".')