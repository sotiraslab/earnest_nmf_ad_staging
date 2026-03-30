# Quality Control (QC)

After preprocessing, images are manually QCed.  This folder contains some code for implementing the QC process.

First, `step0_run_qc_setup.py` will run [`atstaging.preprocessing.qc_tools.setup_qc()`](https://github.com/sotiraslab/earnest_nmf_ad_staging/blob/main/atstaging/preprocessing/qc_tools.py#L378) for all subjects, which generates QC records from processing outputs (derivative file counts, metadata extracted from SLURM epilogues, average image statistics and outlier records, screenshots of key processing steps).  QC data are stored in a folder generated within the BIDS output for all subjects: `OUTPUTDIRECTORY/preprocessing/images/[DATASET]/qc`

Next, the user should manually go through the screenshots for manual visual QC of all outputs, recording a QC pass/fail (specifically, `1` or `0`) for each image in the screenshotsQC.csv.  The screenshots to verify are:

- Brain mask overlap with T1
- Checkerboard of T1 and MNI template
- PET/T1 registration overlap in T1 space (both amyloid & tau)
- SUVR map with colors ranging from 1.0 to 2.5 (both amyloid & tau)
- Overlap of PET image with MNI template (both amyloid & tau)

Then `step1_compile_qc.py` can be used to collect all the QC information into a single file, saved at `OUTPUTDIRECTORY/masterTables/FILTER_QC.csv`.  This is used for automatically filtering out subjects which failed QC when loading the master table.

Optionally, `step2_groupwise_SUVRs.py` can be used to generate bar plots showing average PET uptakes in regions of interest across each dataset.

Finally, `step3_write_pathstable.py` will save a table containing the paths to each output for each subject at `OUTPUTDIRECTORY/preprocessing/paths/paths.csv`



