# Collecting some extra variables (Race, ethnicity, education, BMI)
# This should have been done at the beginng
# Rather than potentially alter the subject selection with updated data
# Decided to just add here

import os

import numpy as np
import pandas as pd

from atstaging.config import get, set_config
from atstaging.dataorg.utils import add_features_by_subject, add_features_by_date
from atstaging.outputs import load_split

# LOAD MASTER
set_config('main')

master = load_split(None, None, verbose=False)
roster = master[['Subject', 'Session', 'DataSet', 'TauAmyloidMeanDate']].copy()
final_columns = ['Subject', 'Session', 'Race', 'Hispanic', 'Education', 'BMI']

# A4
########

a4_subject_info = '/home/tom.earnest/a4_clinical/DerivedData/SUBJINFO.csv'

subj = pd.read_csv(a4_subject_info)

features_a4 = add_features_by_subject(roster[roster['DataSet'].eq('A4')], subj, fields=['RACE', 'ETHNIC', 'EDCCNTU', 'BMIBL'], a_subject='Subject', b_subject='BID', drop_missing=False)
features_a4['Race'] = features_a4['RACE'].map({
    1: 'White',
    2: 'Black',
    58: 'Asian',
    79: 'Other',
    84: 'Other',
    97: 'NA',
    100: 'Other'
}) 
features_a4['Hispanic'] = features_a4['ETHNIC'].map({50: 1., 56: 0., 97: np.nan})
features_a4['Education'] = features_a4['EDCCNTU']
features_a4['BMI'] = features_a4['BMIBL']

features_a4 = features_a4[final_columns].copy()

# ADNI
########

ptdemog = '/home/tom.earnest/adni_clinical/ptdemog.csv'
vitals = '/home/tom.earnest/adni_clinical/vitals.csv'

ptdemog = pd.read_csv(ptdemog)
vitals = pd.read_csv(vitals)

# demographics
ptdemog['Subject'] = ptdemog['PTID'].str.replace('_', '')
ptdemog = ptdemog.groupby('Subject', as_index=False).first()
features_adni = add_features_by_subject(roster[roster['DataSet'].eq('ADNI')], ptdemog, fields=['PTEDUCAT', 'PTRACCAT', 'PTETHCAT'], a_subject='Subject', b_subject='Subject')
features_adni['Race'] = features_adni['PTRACCAT'].map(
    {
        '5': 'White',
        '4': 'Black',
        '2': 'Asian',
        '7': 'NA',
        '-4': 'NA',
        '9': 'NA',
        '6': 'Other',
        '1': 'Other',
        '3': 'Other',
    }
)
features_adni.loc[features_adni['PTRACCAT'].str.contains('|', regex=False).fillna(False), 'Race'] = 'Other'
features_adni.loc[features_adni['PTRACCAT'].isna(), 'Race'] = 'NA'
features_adni['Hispanic'] = features_adni['PTETHCAT'].eq(1).astype(float)
features_adni.loc[features_adni['PTETHCAT'].eq(3) | features_adni['PTETHCAT'].eq(-4), 'Hispanic'] = np.nan
features_adni['Education'] = features_adni['PTEDUCAT']

# BMI
vitals['Subject'] = vitals['PTID'].str.replace('_', '')

features_adni = add_features_by_date(features_adni, vitals, fields=['VSWEIGHT', 'VSHEIGHT', 'VSHTUNIT', 'VSWTUNIT'], a_subject='Subject', a_date='TauAmyloidMeanDate',
                                     b_subject='Subject', b_date='VISDATE', b_name='vitals', include_gap_cols=False)

# seems to be a lot of miscoded height values
# the units of inches and centimeters are not really overlapping for human heights,
# so can be automatically inferred
features_adni['VSHEIGHT'] = features_adni.groupby('Subject')['VSHEIGHT'].ffill()
features_adni.loc[features_adni['VSHEIGHT'].lt(100), 'VSHTUNIT'] = 1
features_adni.loc[features_adni['VSHEIGHT'].ge(100), 'VSHTUNIT'] = 2

# recode NA
features_adni.loc[features_adni['VSWEIGHT'].le(0), 'VSWEIGHT'] = np.nan
features_adni.loc[features_adni['VSHEIGHT'].le(0), 'VSHEIGHT'] = np.nan

# Convert to same units, screen out realistic ranges
features_adni['weight'] = np.where(features_adni['VSWTUNIT'].eq(1), features_adni['VSWEIGHT'] * 0.453592, features_adni['VSWEIGHT'])
features_adni['height'] = np.where(features_adni['VSHTUNIT'].eq(1), features_adni['VSHEIGHT'] * 0.0254, features_adni['VSHEIGHT'] * 0.01)
features_adni.loc[~features_adni['weight'].between(40, 200), 'weight'] = np.nan
features_adni.loc[features_adni['VSHEIGHT'].le(0), 'VSHEIGHT'] = np.nan
features_adni['BMI'] = features_adni['weight'] / (features_adni['height']**2)

features_adni = features_adni[final_columns].copy()

# GS1 / GS2
########

# GS1
demo = pd.read_csv('/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/GS1/tabular/analysis_adam/csv/subject_level_analysis_dataset.csv')

demo['Subject'] = 'S' + demo['Subject Identifier for the Study'].astype(str)
features_gs1 = add_features_by_subject(roster[roster['DataSet'].eq('GS1')], demo, fields=['Race'], a_subject='Subject', b_subject='Subject')
features_gs1['Race'] = features_gs1['Race'].map({'WHITE': 'White', 'UNKNOWN': 'NA', np.nan: 'NA'})
features_gs1['Hispanic'] = np.nan
features_gs1['Education'] = np.nan
features_gs1['BMI'] = np.nan

# GS2
demo = pd.read_csv('/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/GS2/tabular/analysis_adam/csv/subject_level_analysis_dataset.csv')

demo['Subject'] = 'S' + demo['Subject Identifier for the Study'].astype(str)
features_gs2 = add_features_by_subject(roster[roster['DataSet'].eq('GS2')], demo, fields=['Race'], a_subject='Subject', b_subject='Subject')
features_gs2['Race'] = features_gs2['Race'].map({'WHITE': 'White', 'UNKNOWN': 'NA', np.nan: 'NA'})
features_gs2['Hispanic'] = np.nan
features_gs2['Education'] = np.nan
features_gs2['BMI'] = np.nan

# HABS
########
demo = pd.read_csv('/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/HABS/tabular/Demographics_HABS_DataRelease_2.0.csv')
demo = demo.groupby('SubjID', as_index=False).first()
demo['Subject'] = demo['SubjID'].str.replace('_', '')

features_habs = add_features_by_subject(roster[roster['DataSet'].eq('HABS')], demo, fields=['Race', 'Ethnicity', 'YrsOfEd'], a_subject='Subject', b_subject='Subject')
features_habs['Race'] = features_habs['Race'].map({'W': 'White', 'B': 'Black', 'None': 'NA', 'AS': 'Asian', 'NA/W': 'Other'})
features_habs['Hispanic'] = features_habs['Ethnicity'].map({'H': 1., 'NH': 0.})
features_habs['Education'] = features_habs['YrsOfEd']
features_habs['BMI'] = np.nan

features_habs = features_habs[final_columns].copy()

# HABS-HD
########

# Paths
habshd = pd.read_csv('/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/HABS-HD/tabular-release7/RP_HD_7_Clinical.csv')
habshd['Subject'] = habshd['Med_ID'].astype(str)

race_dummies = habshd.loc[:, habshd.columns.str.contains('ID_Race') & ~ habshd.columns.str.contains('Specify')].copy()
race_dummies.columns = race_dummies.columns.str.removeprefix('ID_Race_')
race_dummies[race_dummies < 0] = 0
mixed_race = race_dummies.sum(axis=1).gt(1)
race_dummies.loc[mixed_race, :] = 0
race_dummies.loc[mixed_race, 'Other'] = 1
race = pd.from_dummies(race_dummies, default_category='NAN')
race.columns = ['Race']
race['Subject'] = habshd['Subject']
race = race.drop_duplicates('Subject')
features_habshd = add_features_by_subject(a=roster[roster['DataSet'].eq('HABSHD')], a_subject='Subject', b=race, b_subject='Subject', fields=['Race'])

hispanic = habshd[['Subject', 'ID_Hispanic']].copy()
hispanic['Hispanic'] = hispanic['ID_Hispanic'].ge(2).astype(float)
hispanic = hispanic.drop_duplicates('Subject')
features_habshd = add_features_by_subject(a=features_habshd, a_subject='Subject', b=hispanic, b_subject='Subject', fields=['Hispanic'])

temp = habshd.drop_duplicates('Subject')
features_habshd = add_features_by_subject(a=features_habshd, a_subject='Subject', b=temp, b_subject='Subject', fields=['Informant_EducationLevel', 'OM_BMI'])
features_habshd['Education'] = features_habshd['Informant_EducationLevel']
features_habshd.loc[features_habshd['Education'].lt(0), 'Education'] = np.nan
features_habshd['BMI'] = features_habshd['OM_BMI']
features_habshd.loc[features_habshd['BMI'].lt(0), 'BMI'] = np.nan

features_habshd = features_habshd[final_columns].copy()

# OASIS
########
basedate = pd.Timestamp(year=2001, month=1, day=1)

demo = pd.read_csv('/home/tom.earnest/OASIS3_data_files/scans/demo-demographics/resources/csv/files/OASIS3_demographics.csv')
phys = pd.read_csv('/home/tom.earnest/OASIS3_data_files/scans/UDSb1-Form_B1__Evaluation_Form_Physical/resources/csv/files/OASIS3_UDSb1_physical_eval.csv')
phys['Date'] = basedate + pd.to_timedelta(phys['days_to_visit'], unit='days')

features_oasis = add_features_by_subject(roster[roster['DataSet'].eq('OASIS')], demo, a_subject='Subject', b_subject='OASISID', fields=['race', 'EDUC', 'ETHNIC'])
features_oasis['Race'] = features_oasis['race'].map({
    'White': 'White', 'Black': 'Black', 'ASIAN': 'Asian', 'AIAN': 'Asian', 'more than one': 'Other'
})
features_oasis['Education'] = features_oasis['EDUC']
features_oasis['Hispanic'] = features_oasis['ETHNIC'].eq(1).astype(float)

features_oasis = add_features_by_date(a=features_oasis, a_date='TauAmyloidMeanDate', b=phys, b_subject='OASISID', b_date='Date', fields=['WEIGHT', 'HEIGHT'], include_gap_cols=False)
features_oasis['weight'] = features_oasis['WEIGHT'] * 0.453592
features_oasis['height'] = features_oasis['HEIGHT'] * 0.0254
features_oasis['BMI'] = features_oasis['weight'] / features_oasis['height'] ** 2

features_oasis = features_oasis[final_columns].copy()

# SCAN
########
nacc = pd.read_csv('/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/NACC_SCAN/tabular/investigator_nacc66_atsubset.csv')
nacc_bl = nacc.groupby('NACCID').first().reset_index()

features_scan = add_features_by_subject(roster[roster['DataSet'].eq('SCAN')], nacc_bl, fields=['RACE', 'HISPANIC', 'EDUC', 'NACCBMI'], a_subject='Subject', b_subject='NACCID')
features_scan['Race'] = features_scan['RACE'].map({
    1: 'White',
    2: 'Black',
    3: 'Other',
    4: 'Other',
    5: 'Asian',
    50: 'Other',
    99: 'NA'
})
features_scan['Hispanic'] = features_scan['HISPANIC'].map({0:0, 1:1, 9:np.nan}).astype(float)
features_scan['Education'] = features_scan['EDUC']
features_scan['BMI'] = features_scan['NACCBMI']
features_scan.loc[~features_scan['BMI'].between(0, 50), 'BMI'] = np.nan

features_scan = features_scan[final_columns].copy()

# COMBINE & SAVE
########
combined = pd.concat([
    features_a4, features_adni, features_gs1, features_gs2, features_habs, features_habshd, features_oasis, features_scan
], ignore_index=True)
combined.loc[combined['Race'].isna(), 'Race'] = 'NA'

# save
root_output = get('output_directory')
opath = os.path.join(root_output, 'masterTables', 'FEATURE_COVARIATES.csv')
combined.to_csv(opath, index=False)