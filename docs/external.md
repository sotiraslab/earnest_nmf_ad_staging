# Staging new data

This markdown file contains documentation for using the staging models described in manuscripts related to this repository.

All the code described here is in Python, and requires installation of the package contained within this repository.  After cloning/download:

```bash
cd earnest_nmf_ad_staging
pip install -e .
```

This should make a package called `atstaging` available in your Python environment.

## NMF projections

With new amyloid and/or tau images, you can compute SUVRs within the Patterns of Amyloid Covariance (PACs) and Patterns of Tau Covariance (PTCs).  Other modalities can also be provided (for instance, if you wanted to compute a regional volume within PTCs), but these examples will focus on computing amyloid and tau SUVRs.

The only main requirement is that the input images are in 1mm MNI space (dimension=[182, 218, 182]).  You also need to provide the path to the [`nmf_factors`](https://github.com/sotiraslab/earnest_nmf_ad_staging/tree/main/nmf_factors) directory, a subfolder at the root of this repository.

```python
from atstaging.external import compute_nmf_loadings

# Save the path to the nmf_factors directory
nmf_factors_directory = '~/Downloads/earnest_nmf_ad_staging/nmf_factors'

# provide paths to images in 1mm MNI space
# Here, we are assuming these are for three subjects
amyloid_paths = ['amyloid1.nii.gz', 'amyloid2.nii.gz', 'amyloid3.nii.gz']
tau_paths = ['tau1.nii.gz', 'tau2.nii.gz', 'tau3.nii.gz']

pac_suvrs = compute_nmf_loadings(
  images=amyloid_paths,
  nmf_factors_directory=nmf_factors_directory,
  pathology='amyloid'
    )

ptc_suvrs = compute_nmf_loadings(
  images=tau_paths,
  nmf_factors_directory=nmf_factors_directory,
  pathology='tau'
    )
```

The result will be a DataFrame with a column for each PAC/PTC, and the value being the projection (i.e., weighted average signal) for each.

## W-scoring

You can further convert these uptakes into W-scores.  Parameters for W-scoring are provided, using the models reported in the manuscript:

- `"training"`: Training data, tracers=FBP/FTP
- `"validationA"`: Validation data subset A, tracers=PIB/FTP
- `"validationB"`: Validation data subset B, tracers=FBB/P26
- `"validationC"`: Validation data subset C, tracers=FBB/FTP

For each subject, you need to provide an age (column name: `Age`) and binary indicator of male sex (column name: `SexMale`).

```python
from atstaging.external import apply_wscore_model

# Join the PACs & PTCs into one dataframe
import pandas as pd
all_predictions = pd.concat([pac_suvrs, ptc_suvrs], axis=1)

# Define the age/sex values for W-scoring
# These column names must be used!
all_predictions['Age'] = [72., 69., 88.]
all_predictions['SexMale'] = [1, 1, 0]

# Generate the W-scores
wdf = apply_wscore_model(all_predictions, model='training')
```

## AT-Staging

The following code can be used to generate AT stage assignments.  The required input is a measure of positivity (suprathreshold positivity) for each PAC and PTC.  This can be used by W-scoring the data (see above) and thresholding the values (e.g, at 2.5).   But different approaches for binarization are also possible (e.g., Gaussian mixture modeling).

This will generate labels showing the amyloid and tau stage (e.g., 'A0T0', 'A1T0', 'A2T0', 'A2T1', etc.).  Individuals with non-stageable presentations will be labeled as "NS".

```python
from atstaging.external import apply_atstaging

# This example uses W-scores computed above
positivity = (wdf >= 2.5).astype(float)
stages = apply_atstaging(positivity)
```

