# Group assignment

The main script here (`assign_datasets.py`) implements some of inclusion/exclusion criteria and assigns participants to training/validation groups.  Training/validation assignment is mainly based on tracer and goes as follows:

- Training
  - FBP/FTP
- Validation
  - FBB/FTP (subset A)
  - FBB/P26 (subset B)
  - PIB/FTP (subset C)

Individuals are also only included if they meet one of two disease categories: normative control (amyloid-, tau-, CDR=0) or Alzheimer's Disease spectrum (amyloid+).  Other presentations (e.g., amyloid-/tau+, amyloid-/tau- with missing CDR) are excluded.  This script implements the amyloid positivity assignment (using what is provided by datasets with some imputation based on our processing outputs) and tau positivity (Gaussian mixture model applied to meta-temporal SUVR).

The assignments are stored in a "Split" column of the master dataframe, which labels the training/validation split and whether the scan is baseline or longitudinal (`TrainingBaseline`, `TrainingFollowup`, `ValidationBaseline`, `ValidationFollowup`).  This column is referenced when using `atstaging.outputs.load_split()` to load the master dataframe.

The other script `run_amyloid_pet_net.py` runs AmyloidPETNet for all subjects, a deep-learning based amyloid positivity assessment (https://doi.org/10.1148/radiol.231442).  This is (currently) not used in the manuscripts.
