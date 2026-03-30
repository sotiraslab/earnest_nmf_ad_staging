# Image preprocessing

The main function of this repository is to create tables which can be supplied to the preprocessing pipeline. The major important script is `dataset_proctables.py`.  For each dataset, this will create a table (saved at `OUTPUTDIRECTORY/preprocessing/preproc_tables`) containing one row for each scan set (MRI + amyloid-PET + tau-PET) to be processed.  Each of these tables can be submitted for processing using command line tools bundled with the `atstaging` package.  For example:

```
atproc_table preprocessing/preproc_tables/adni.csv
```

[See this document for further description of the preprocessing pipeline.](https://github.com/sotiraslab/earnest_nmf_ad_staging/blob/main/docs/preprocessing.md)

The other scripts are:

- `subset_proctable.py`: A piloting script which randomly selects 50 subjects from each dataset for processing.
- `average_pet_images`: Creates average PET uptake figures, grouped by disease status.