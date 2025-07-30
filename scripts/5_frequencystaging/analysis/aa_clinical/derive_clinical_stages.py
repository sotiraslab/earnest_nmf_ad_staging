
# IMPORTS
# =====
import numpy as np
import pandas as pd

from atstaging.dataorg.utils import add_features_by_date

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
    cognition['LogicalMemoryDelayedRecall'] = cognition['lmdelay']
    cognition['DigitSymbolSubstitution'] = cognition['digsym']

    clinical['Subject'] = clinical['OASISID']
    clinical['Date'] = oasis_days_to_date(clinical['days_to_visit'], basedate=basedate)

    df = add_features_by_date(a=df, b=cognition, fields=['FCSRTTotal', 'LogicalMemoryDelayedRecall', 'DigitSymbolSubstitution'], a_date=a_date, a_subject=a_subject, include_gap_cols=False)
    df = add_features_by_date(a=df, b=clinical, fields=['MMSE'], a_date=a_date, a_subject=a_subject, include_gap_cols=False)

    return df

def calculate_pacc(df, columns, cn_mask, min_required=2, higher_better=None):

    cn = df[cn_mask].copy()
    n = len(df)
    k = len(columns)

    normed_scores = pd.DataFrame(np.full((n, k), np.nan))
    normed_scores.columns = columns
    normed_scores.index = df.index
    
    if higher_better is None:
        higher_better = [True] * k

    for i in range(k):
        col = columns[i]
        mu = cn[col].mean()
        s = cn[col].std()
        z = (df[col] - mu) / s

        if not higher_better[i]:
            z *= -1

        normed_scores[col] = z

    score = np.nanmean(normed_scores, axis=1)
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

master = pd.read_csv('master.csv')
master['ControlForStaging'] = master['Split'].str.contains('Baseline') & master['CDRBinned'].eq('0.0') & master['FinalAmyloidStatus'].eq(0) & master['GMMTauStatus'].eq(0)

# separate into different datasets with PACC information
master_adni = master.loc[master['DataSet'].eq('ADNI'), ['Subject', 'TauAmyloidMeanDate']]
master_a4 = master.loc[master['DataSet'].eq('A4'), ['Subject', 'TauAmyloidMeanDate']]
master_oasis = master.loc[master['DataSet'].eq('OASIS'), ['Subject', 'TauAmyloidMeanDate']]
master_habs = master.loc[master['DataSet'].eq('HABS'), ['Subject', 'TauAmyloidMeanDate']]
master_habshd = master.loc[master['DataSet'].eq('HABSHD'), ['Subject', 'TauAmyloidMeanDate']]

# ===================
# COLLECT PACC DATA
# ===================

# ADNI
# =====

# Read in data
cdr = pd.read_csv('adni_clinical/cdr.csv')
neurobat = pd.read_csv('adni_clinical/neurobat.csv')
mmse = pd.read_csv('adni_clinical/mmse.csv')
adas = pd.read_csv('adni_clinical/adas.csv')

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
cdr = pd.read_csv('a4_clinical/RawData/cdr.csv')
mmse = pd.read_csv('a4_clinical/RawData/mmse.csv')
fcsrt = pd.read_csv('a4_clinical/RawData/cogfcsr16.csv')
logimem = pd.read_csv('a4_clinical/RawData/coglogic.csv')
digits = pd.read_csv('a4_clinical/RawData/cogdigit.csv')

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

cognition = pd.read_csv('habs_tabular/Cognition_HABS_DataRelease_2.0.csv')
clinical = pd.read_csv('habs_tabular/ClinicalMeasures_HABS_DataRelease_2.0.csv')

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
clinical = pd.read_csv('OASIS3_data_files/scans/UDSb4-Form_B4__Global_Staging__CDR__Standard_and_Supplemental/resources/csv/files/OASIS3_UDSb4_cdr.csv')
cognition = pd.read_csv('OASIS3_data_files/scans/pychometrics-Form_C1__Cognitive_Assessments/resources/csv/files/OASIS3_UDSc1_cognitive_assessments.csv')
clinical['Date'] = oasis_days_to_date(clinical['days_to_visit'], basedate=basedate)
cognition['Date'] = oasis_days_to_date(cognition['days_to_visit'], basedate=basedate)

# Select the stable cognitive individuals
cdr = clinical[['OASISID', 'Date', 'CDRTOT']].copy().dropna().sort_values(['OASISID', 'Date'])
cdr.columns = ['Subject', 'Date', 'CDR']
cn_long = select_consistent_cognitively_normal(cdr)
cn_baseline = cn_long[cn_long['YearsSinceBaseline'].eq(0)].copy()

oasis_cn_baseline = assemble_pacc_oasis(cn_baseline, cognition=cognition, clinical=clinical)
master_oasis = assemble_pacc_oasis(master_oasis, cognition=cognition, clinical=clinical, a_date='TauAmyloidMeanDate')


# EXTRA CODE
# =====

# adni = master.loc[master['DataSet'].eq('ADNI'), ['Subject', 'TauAmyloidMeanDate', 'ControlForStaging', 'CDRBinned']]
# adni.columns = ['Subject', 'Date', 'Control', 'CDRBinned']
# adni['Subject'] = adni['Subject'].str[:3] + '_S_' + adni['Subject'].str[-4:]

# adni = add_features_by_date(a=adni, b=neuro, fields=['CATANIMSC', 'TRABSCOR', 'LDELTOTAL', 'DIGITSCOR'], a_date='Date', a_subject='Subject',
#                             b_date='VISDATE', b_name='NeuroBat', b_subject='PTID', include_gap_cols=False)
# adni = add_features_by_date(a=adni, b=adas, fields=['Q4SCORE'], a_date='Date', a_subject='Subject',
#                             b_date='USERDATE', b_name='ADAS', b_subject='PTID', include_gap_cols=False)
# adni = add_features_by_date(a=adni, b=mmse, fields=['MMSCORE'], a_date='Date', a_subject='Subject',
#                             b_date='VISDATE', b_name='MMSE', b_subject='PTID', include_gap_cols=False)
# adni['Subject'] = adni['Subject'].str.replace('_','')
# adni

# # load tabular data
# tabular_folder = 'habshd_tabular'

# tables = [
#     'HD_1_African',
#     'HD_1_Mexican',
#     'HD_1_Non',
#     'HD_2_Mexican',
#     'HD_2_Non',
#     'HD_3_Mexican',
#     'HD_3_Non']
# habshd = pd.concat([load_csv_by_match(tabular_folder, t, dtype={'Med_ID': str}) for t in tables])
# habshd = habshd.drop_duplicates(['Med_ID', 'Visit_ID'])