"""Script can be run after data splitting has been assigned (scripts/3_datasplitting/assign_datasets.py)
to make sure that some expected conditions are met.  Reports some numbers and does some simple unit tests.

An issue is indicated by a red FALSE printout after a test case.  If only green TRUE(s) are shown (plus)
the sample size numbers shown prior) then things are good."""

# IMPORTS
import itertools as it

from colorama import Fore, Style

from atstaging.outputs import load_split

# HELPERS
def colorbool(x):
    s = (Fore.GREEN + Style.BRIGHT + 'TRUE') if x else (Fore.RED + Style.BRIGHT + 'FALSE')
    return s + Style.RESET_ALL

def colornum(x):
    s = Fore.CYAN + Style.BRIGHT + str(x)
    return s + Style.RESET_ALL

def report_subs(df, name):
    nsubjects = df['Subject'].nunique()
    nvisits = len(df)
    nlong = nvisits - nsubjects
    print(f'Group={name}; N subjects: {colornum(nsubjects)}, N visits: {colornum(nvisits)}, N followup: {colornum(nlong)}')
    
# LOAD DATA

print()
print('LOADING DATA')

df = load_split(None, None, verbose=False)
training = load_split('training', None, verbose=False)
training_bl = load_split('training', 'baseline', verbose=False)

same_tracer_groups = [col for col in df.columns if 'SameTracerValidation' in col]

validations = {}
for col in same_tracer_groups:
    validations[col] = load_split('validation', None, validation_sub=col[-1], verbose=False)

validations_bl = {}
for col in same_tracer_groups:
    validations_bl[col] = load_split('validation', 'baseline', validation_sub=col[-1], verbose=False)

# report some numbers
print()
print("OVERVIEW")

# number of subjects
print()
print('Subject count; all')
report_subs(training, 'Training')
for name, frame in validations.items():
    report_subs(frame, name)

print()
print('Subject count; CN [only baseline is shown]')
report_subs(training_bl[~training_bl['CDRBinned'].isna() & training_bl['CDRBinned'].eq('0.0')], 'Training')
for name, frame in validations_bl.items():
    report_subs(frame[~frame['CDRBinned'].isna() & frame['CDRBinned'].eq('0.0')], name)
    
# essentially unit tests
print()
print("TEST CASES")

# unique subjects
test = ~ (df['Subject'] + df['Session']).duplicated().any()
print()
print('All rows are unique for Subject & Session?', colorbool(test))

# no lone followup
df['LabeledBaseline'] = df['Split'].str.contains('Baseline')
test = df.groupby('Subject')['LabeledBaseline'].any().all()
print()
print("All longitudinal visits have a baseline?", colorbool(test))

# all subjects have demographics
test = ~ ((df['Age'].isna()) | (df['SexMale'].isna())).any()
print()
print('All subjects have demographics?', colorbool(test))

# no overlap of same tracer subjects and training groups
subjects_dict = {}
subjects_dict['Training'] = training_bl['Subject'].to_list()
for name, frame in validations.items():
    subjects_dict[name] = frame['Subject'].to_list()

print()
for a, b in it.combinations(subjects_dict.keys(), 2):
    suba = subjects_dict[a]
    subb = subjects_dict[b]
    intersect = set(suba) & set(subb)
    test = len(intersect) == 0
    print(f'No overlapping subjects in {a} & {b}?', colorbool(test))

# consistent tracers within subjects
print()
test = df.groupby('Subject')['TracerAmyloid'].nunique().eq(1).all()
print("Consistent amyloid tracers for all subjects?", colorbool(test))
test = df.groupby('Subject')['TracerTau'].nunique().eq(1).all()
print("Consistent tau tracers for all subjects?", colorbool(test))

# consistent tracers within groups
print()
test = (training['TracerAmyloid'].nunique() == 1) and (training['TracerTau'].nunique() == 1)
print("Only one set of tracers in Training?", colorbool(test))
for name, frame in validations.items():
    test = (frame['TracerAmyloid'].nunique() == 1) and (frame['TracerTau'].nunique() == 1)
    print(f"Only one set of tracers in {name}?", colorbool(test))