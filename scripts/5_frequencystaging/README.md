# Staging model for amyloid and tau

This folder contains the code which are (mostly) specific to the project, "A unified model for staging amyloid and tau pathology in Alzheimer’s disease".  This is the work which uses the dataset and NMF solution to inform a single biological staging model for AD, covering the development of amyloid and tau.

There are a lot of scripts in here.  This is a brief description of what most of them do, in roughly the order they should be run:

- `hardsave_master.py`: This generates a version of the master dataframe which can be read into R, necessary for the next step.
- `wscoring.R`: Fits the W-scoring model, converting SUVR uptakes in PACs/PTCs into normative deviations.
- `develop_staging.R`: Runs the bootstrapping algorithm to determine the optimal number of disease stages and grouping of PACs/PTCs into stages.
- `staging_heatmap_figure.R`: Creates the heatmap showing the pairwise log p-values showing if factors have significant differences in the rate of observed pathology.
- Some scripts to generate other features:
  - `derive_icv.py`: Generates intracranial volume measures from DLICV output.
  - `add_other_covariates.py`:  Collects some basic covariates not previously selected for (race, ethnicity, education, BMI).
  - `save_muse_rois.py`: Consolidates the MUSE SUVRs into more accessible tables.

The above scripts determine the staging model and generate stage assignments for all participants.  The additional scripts in the `analysis` folder then generate the statistical analyses and visualizations from these data:

- `overlay_stages_on_brain.py`: Creates NIFTI images showing the stages overlaid on a brain, based on a winner take all assignment of NMF factors.
- `table1.R`: Descriptives table.
- `distribution.py`: Stacked bar plots showing the distribution of stages across dataset and study group.
- `status_staging_concordance.py`: Compares the stage assignments against continuous measures of global amyloid and tau burden.
- `longitudinal_stability.py`: Evaluates the longitudinal consistency of stage assignments.
- `create_suvr_by_stage_images.py`: Creates NIFTI images showing the average SUVR across different disease stages.
- `compare_atypical.R`: Runs statistical models comparing non-stageable individuals to stageable ones.
- `cross_sectional`: Compares cross-sectional MMSE and CDR-SB scores across stage groups.  Also fits chi-squared models compared categorical variables across stages.
- `longitudinal`: Runs the mixed-effect models and survival models evaluating longitudinal trajectories associated with stages.
- `aa_biological`: Compares our staging model against the Alzheimer's Association proposed approach to biological staging of AD.
- `aa_clinical`: Compares our staging model against the Alzheimer's Association proposed approach to clinical staging of AD (i.e., based on cognitive performance).
