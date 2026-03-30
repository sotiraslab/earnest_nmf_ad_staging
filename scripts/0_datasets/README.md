# Data wrangling scripts

This folder contains code for data wrangling, identifying the subjects to select for preprocessing and identifying basic variables of interest for each.

**Note that many paths in this folder in particular are hardcoded, and will need to be manually updated to rerun each script.**

For each source dataset (A4, ADNI, GS1, GS2, HABS, HABS-HD, OASIS, SCAN), there is a corresponding Python file which does the following:

- Searches across download folders to identify the MRI, amyloid-PET, and tau-PET images which are available.
- Creates a table showing the available subjects (and session) and paths to input images
- Identifies basic demographic/clinical variables where available, namely age, sex, APOE E4 status, amyloid positivity, and CDR
- Saves a CSV record.  Under the output folder specified by the config file (`OUTPUTDIRECTORY`, these CSVs will be saved in the "datasetTables" subfolder.

Some specific notes for each dataset:

- For ADNI, SCAN, and HABS-HD, there are notes about how image searches were conducted on LONI in the `earnest_nmf_ad_staging/notes/image_searches.md` file.  For all other datasets, images are either automatically searched from the download folder or the LONI search was less complicated and not documented.
- For OASIS, some PET data were only provided in the dynamic format.  The script `oasis_pull_frames.py` must first be run to extract the active window from each PET image and save a version.
- For GS2, some PET images were separated into separate DICOM folders.  The script `gs2_reorganize_images.py` will identify those images and created merged NIFTI files such that there is one file for each multiframe scan.

After running each dataset wrangling script, run `create_master.py` to initialize a master version of the data which is used for easy reloading.  See `atstaging.outputs.load_master` and `atstaging.outputs.load_split`, for example.  In short, an output folder called `masterTables` is created and a root document called `MASTER.csv` is saved, containing a row for each unique scanning session for each subject across datasets.  This folder is than later populated with additional features (`FEATURE_[].csv`) and filters (`FILTER_[].csv`) which (respectively) add additional variables and omit sessions failing inclusion requirements.

