
# IMPORTS
# =======

import os

import numpy as np
import pandas as pd

from atstaging.config import set_config, get
from atstaging.dataorg.utils import add_features_by_date, load_csv_by_match, longitudinal_features
from atstaging.outputs import load_split, setup_outputs_folder

# CONFIG
# =====
set_config('main')

# LOAD THE BASELINE DATA
# =======

df = load_split(None, 'baseline')
bl = df[['Subject', 'Session', 'TauAmyloidMeanDate']].copy().reset_index(drop=True)
bl.columns = ['Subject', 'Session', 'DateBaseline']
bl['DateBaseline'] = pd.to_datetime(bl['DateBaseline'])

# ADNI
# =======

adni_tabular = '/home/tom.earnest/adni_clinical/'

# CDR
cdr = load_csv_by_match(adni_tabular, 'cdr')
cdr['Subject'] = cdr['PTID'].str.replace('_', '')
adni_cdr = longitudinal_features(bl, cdr, ['CDGLOBAL', 'CDRSB'], long_date='USERDATE', dest_long_features=['CDR', 'CDRSumBoxes'])

# MMSE
mmse = load_csv_by_match(adni_tabular, 'mmse')
mmse['Subject'] = mmse['PTID'].str.replace('_', '')
adni_mmse = longitudinal_features(bl, mmse, ['MMSCORE'], long_date='VISDATE', dest_long_features=['MMSE'])

# A4
# =======

basedate = pd.Timestamp(year=2001, month=1, day=1)

# For A4, some visits (in the 700s and 900s) indicate unscheduled vists
# for these, the CDDY can be used, as this is the number of days since screening
cdr = pd.read_csv('/home/tom.earnest/a4_clinical/RawData/cdr.csv')
cdr['Date'] = basedate + pd.to_timedelta(cdr['VISCODE'], unit='W')
cdr.loc[cdr['VISCODE'].gt(700), 'Date'] = basedate + pd.to_timedelta(cdr['CDDY'], unit='D')
a4_cdr = longitudinal_features(bl, cdr, ['CDGLOBAL', 'CDRSB'], long_subject='BID', dest_long_features=['CDR', 'CDRSumBoxes'])

# For MMSE, similar column doesn't exist, so those rows are omitted
mmse = pd.read_csv('/home/tom.earnest/a4_clinical/RawData/mmse.csv')
mmse = mmse[mmse['VISCODE'].le(500)]
mmse['Date'] = basedate + pd.to_timedelta(mmse['VISCODE'], unit='W')
a4_mmse = longitudinal_features(bl, mmse, 'MMSCORE', long_subject='BID', dest_long_features='MMSE')

# GS1
# =====

tabular_folder = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/GS1/tabular/raw_sdtm/csv'
ques = load_csv_by_match(tabular_folder, 'quest', dtype={'Subject Identifier for the Study': str})
ques['Subject Identifier for the Study'] = 'S' + ques['Subject Identifier for the Study']

cdr = ques[ques['Category of Question'].eq('CLINICAL DEMENTIA RATING (CDR)')].copy()

cols = ['Subject Identifier for the Study', 'Date/Time of Finding', 'Finding in Original Units']
a = ques.loc[ques['Question Name'].eq('CDR-Global CDR'), cols]
b = ques.loc[ques['Question Name'].eq('CDR-Sum of Boxes'), cols]
a.columns = ['Subject', 'Date', 'CDR']
b.columns = ['Subject', 'Date', 'CDRSumBoxes']
cdr = add_features_by_date(a=a, b=b, fields=['CDRSumBoxes'], a_date='Date', b_date='Date', include_gap_cols=False)
cdr['CDR'] = cdr['CDR'].map({'0 NONE': 0, '0.5 QUESTIONABLE': 0.5, '1 MILD': 1, 'NOT APPLICABLE': np.nan}).astype(float)
cdr['CDRSumBoxes'] = cdr['CDRSumBoxes'].replace('NOT APPLICABLE', np.nan).astype(float)

gs1_cdr = longitudinal_features(bl, cdr, ['CDR', 'CDRSumBoxes']).dropna()

mmse = ques[ques['Category of Question'].eq('MINI MENTAL STATE EXAMINATION')].copy()
mmse = mmse[mmse['Question Name'].eq('TOTAL SCORE DERIVED')].copy()
mmse = mmse[cols]
mmse.columns = ['Subject', 'Date', 'MMSE']
mmse['MMSE'] = mmse['MMSE'].replace('NOT APPLICABLE', np.nan).astype(float)
gs1_mmse = longitudinal_features(bl, mmse, 'MMSE').dropna()

# GS2
# =====
tabular_folder = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/GS2/tabular/raw_sdtm/csv'
ques = load_csv_by_match(tabular_folder, 'quest', dtype={'Subject Identifier for the Study': str})
ques['Subject Identifier for the Study'] = 'S' + ques['Subject Identifier for the Study']

cdr = ques[ques['Category of Question'].eq('CLINICAL DEMENTIA RATING (CDR)')].copy()

cols = ['Subject Identifier for the Study', 'Date/Time of Finding', 'Finding in Original Units']
a = ques.loc[ques['Question Name'].eq('CDR-Global CDR'), cols]
b = ques.loc[ques['Question Name'].eq('CDR-Sum of Boxes'), cols]
a.columns = ['Subject', 'Date', 'CDR']
b.columns = ['Subject', 'Date', 'CDRSumBoxes']
cdr = add_features_by_date(a=a, b=b, fields=['CDRSumBoxes'], a_date='Date', b_date='Date', include_gap_cols=False)
cdr['CDR'] = cdr['CDR'].map({'0 NONE': 0, '0.5 QUESTIONABLE': 0.5, '1 MILD': 1, 'NOT APPLICABLE': np.nan}).astype(float)
cdr['CDRSumBoxes'] = cdr['CDRSumBoxes'].replace('NOT APPLICABLE', np.nan).astype(float)

gs2_cdr = longitudinal_features(bl, cdr, ['CDR', 'CDRSumBoxes']).dropna()

mmse = ques[ques['Category of Question'].eq('MINI MENTAL STATE EXAMINATION')].copy()
mmse = mmse[mmse['Question Name'].eq('TOTAL SCORE DERIVED')].copy()
mmse = mmse[cols]
mmse.columns = ['Subject', 'Date', 'MMSE']
mmse['MMSE'] = mmse['MMSE'].replace('NOT APPLICABLE', np.nan).astype(float)
gs2_mmse = longitudinal_features(bl, mmse, 'MMSE').dropna()

# OASIS
# =====

basedate = pd.Timestamp(year=2001, month=1, day=1)
clinical = pd.read_csv('/home/tom.earnest/OASIS3_data_files/scans/UDSb4-Form_B4__Global_Staging__CDR__Standard_and_Supplemental/resources/csv/files/OASIS3_UDSb4_cdr.csv')
clinical['Date'] = basedate + pd.to_timedelta(clinical['days_to_visit'], unit='days')

oasis_cdr = longitudinal_features(bl, clinical, long_features=['CDRTOT', 'CDRSUM'], long_subject='OASISID', dest_long_features=['CDR', 'CDRSumBoxes'])

oasis_mmse = longitudinal_features(bl, clinical, long_features=['MMSE'], long_subject='OASISID').dropna()

# SCAN
# =====

nacc = pd.read_csv('/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/NACC_SCAN/tabular/investigator_nacc66_atsubset.csv')
nacc['Date'] = pd.to_datetime(
    {'year': nacc['VISITYR'],
    'month': nacc['VISITMO'],
    'day': nacc['VISITDAY']}
)

scan_cdr = longitudinal_features(bl, nacc, long_features=['CDRGLOB', 'CDRSUM'], long_subject='NACCID', dest_long_features=['CDR', 'CDRSumBoxes'])

# not really any MMSE for SCAN with my dataset
scan_mmse = longitudinal_features(bl, nacc, long_features=['NACCMMSE'], long_subject='NACCID', dest_long_features=['MMSE'])
scan_mmse['MMSE'] = scan_mmse['MMSE'].replace(-4, np.nan)
scan_mmse = scan_mmse.dropna(subset=['MMSE'])

# HABS
# =====

habs_tabular_directory = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/HABS/tabular/'
clinical = load_csv_by_match(habs_tabular_directory, 'ClinicalMeasures')
clinical['Subject'] = clinical['SubjIDshort'].str.replace('_', '')

habs_cdr = longitudinal_features(bl, clinical, long_features=['CDR_Global', 'CDR_SB'], long_date='NP_SessionDate', dest_long_features=['CDR', 'CDRSumBoxes'])

habs_mmse = longitudinal_features(bl, clinical, long_features=['MMSE_Total'], long_date='NP_SessionDate', dest_long_features=['MMSE'])

# HABS-HD
# =====

# load tabular data
tabular_folder = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/HABS-HD/tabular'

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

# Currently, only have visit IDs for HABS-HD to link tabular data
# this can be linked to scans from LONI, but needs to be done thru the MRI
# visit ID.
t1 = pd.read_csv('/scratch/tom.earnest/atstaging/searches/habshd_t1_10102024_12_05_2024.csv', dtype={'Subject':str})
t1['VisitID'] = t1['Visit'].map({'BL': 1,'M24': 2,'M48': 3,'M72': 4})
t1_visits = t1[['Subject', 'Acq Date', 'VisitID']].copy()
t1_visits.columns = ['Subject', 'DateT1', 'VisitID']
t1_visits['DateT1'] = pd.to_datetime(t1_visits['DateT1'])

# for HABS-HD, just using T1 scan date as the BL date, rather than the mean of amyloid and tau
# since visit seem to be organized aroung t1
habshd_bl = df[df['DataSet'].eq('HABSHD')].copy()
habshd_bl = habshd_bl[['Subject', 'Session', 'ScanDateT1']].copy().reset_index(drop=True)
habshd_bl.columns = ['Subject', 'Session', 'DateT1']
habshd_bl['DateT1'] = pd.to_datetime(habshd_bl['DateT1'])
habshd_bl = habshd_bl.merge(t1_visits, on=['Subject', 'DateT1'], how='left')
habshd_bl = habshd_bl.rename(columns={'VisitID': 'VisitIDBaseline', 'DateT1': 'DateBaseline'})

cdr = habshd[['Med_ID', 'Visit_ID', 'CDR_Global', 'CDR_Sum', 'MMSE_Total']]
cdr.columns = ['Subject', 'VisitIDClinical', 'CDR', 'CDRSumBoxes', 'MMSE']
habshd_long = habshd_bl.merge(cdr, on='Subject')
habshd_long = habshd_long[habshd_long['VisitIDClinical'].ge(habshd_long['VisitIDBaseline'])]
years = pd.Timedelta('730D') * (habshd_long['VisitIDClinical'] - habshd_long['VisitIDBaseline'])
habshd_long['DateLongitudinal'] = habshd_long['DateBaseline'] + years

habshd_cdr = habshd_long[['Subject', 'Session', 'DateBaseline', 'DateLongitudinal', 'CDR', 'CDRSumBoxes']].copy()
habshd_mmse = habshd_long[['Subject', 'Session', 'DateBaseline', 'DateLongitudinal', 'MMSE']].copy()

# MERGE RESULTS
# =====

cdr_dfs = [a4_cdr, adni_cdr, gs1_cdr, gs2_cdr, habs_cdr, habshd_cdr, oasis_cdr, scan_cdr]
cdr_long = pd.concat(cdr_dfs, axis=0, ignore_index=True)
cdr_long = cdr_long.drop(columns='Session')

mmse_dfs = [a4_mmse, adni_mmse, gs1_mmse, gs2_mmse, habs_mmse, habshd_mmse, oasis_mmse, scan_mmse]
mmse_long = pd.concat(mmse_dfs, axis=0, ignore_index=True)
mmse_long = mmse_long.drop(columns='Session')

# SAVE
# =====

output_directory = get('output_directory')
setup_outputs_folder(output_directory)
longitudinal_dir = os.path.join(output_directory, 'longitudinalTables')
cdr_path = os.path.join(longitudinal_dir, 'cdr_long.csv')
mmse_path = os.path.join(longitudinal_dir, 'mmse_long.csv')

cdr_long.to_csv(cdr_path, index=False)
mmse_long.to_csv(mmse_path, index=False)

# also save the baseline data for analysis in R
bl = load_split(None, 'baseline', verbose=False)
bl.to_csv(os.path.join(longitudinal_dir, 'baseline.csv'), index=False)