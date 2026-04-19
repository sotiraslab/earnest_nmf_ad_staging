# Amyloid and tau staging

This repository contains code for research from the [Aristeidis Sotiras group](https://www.med.upenn.edu/apps/faculty/index.php/g275/p8337457) aimed at defining biological staging  models for Alzheimer's Disease.

## Background

This project focuses on applying data-driven analysis to derive biological staging models for Alzheimer's Disease (AD).  We particularly aim to define staging for **both amyloid and tau**, following [recent research guidelines](https://doi.org/10.1002/alz.13859) which define the core role of both pathologies in AD.

Our approach focuses on positron emission tomography (PET), allowing for *in vivo* analysis of the spatial spread of both pathologies in a large sample of individuals.  We applying unsupervised machine learning ([non-negative matrix factorization - NMF](https://github.com/asotiras/brainparts)) to identify reproducible, interpretable factors of amyloid and tau pathology.  These factors are used to inform models which estimate the spatiotemporal spread of pathology.

## Repository overview

This repository contains code for running analyses and generating figures related to the project.  It also contains the preprocessing pipeline used for deriving MNI space PET SUVR maps for amyloid and tau.

The folder `scripts` contains the majority of code which documents the project.  Numbered subfolders (e.g. `0_datasets`, `1_preprocessing`, ...) show the order of major steps for the project.  Each of these subfolders will contain a README documenting the major things accomplished therein.  This folder also contains `scripts/misc` (miscellaneous code applied for some analysis/data wrangling steps) and `scripts/rsource` (R helper functions).

Most of the Python scripts reference a Python package which is contained in the `atstaging` folder.  Running code from this repository will likely require installation of this package (see next section).

## Using this repository

Here are a few ways this repository can be used for external research:

- **Applying the preprocessing pipeline**.  This repo contains code for the neuroimaging preprocessing pipeline which can be used for MRI & PET.  [A document describing how to use it is provided here](https://github.com/sotiraslab/earnest_nmf_ad_staging/blob/main/docs/preprocessing.md).
- **Projecting new data onto NMF components**.  The four amyloid and seven tau NMF factors are shared in the `nmf_factors` folder as NIFTIs.  The omitted reference, subcortical, and white matter factors are also included.  There is also code for projecting data onto these factors, which allows users to estimate SUVRs for new data.
- **Staging new data**.  Data which have been projected to NMF components can be staged to derive amyloid/tau biological severity labels for new individuals.

[**For the latter two points, see this readme for more details.**](https://github.com/sotiraslab/earnest_nmf_ad_staging/blob/main/docs/external.md)

### Code installation

Many functions will require installation of the Python package contained in this repo, `atstaging`.  To do so, clone/download the repo, move into it, and run a pip install.

```bash
cd earnest_nmf_ad_staging
pip install -e .
```

You may want to do so in an isolated Python environment (this project used [miniconda](https://www.anaconda.com/docs/getting-started/miniconda/main)).  General requirements for this project are Python>=3.10, and specific packages listed in the pyproject.toml file.

This repository also contains R code - the required packages are listed in `r_requirements.txt`.

### Manuscript code (figures, statistical analyses)

Most code used to generate content for the manuscript(s) is contained in the `scripts` folder. Due to several factors, this code will not be easily runnable by new users.

- Source data need to be provided (A4, ADNI, GS1, GS2, HABS, HABS-HD, OASIS, SCAN).
  - *This repository should not contain data from any of these datasets in accordance with data use agreements - please inform the maintainer if you find anything that you think should not be being shared.*
- Some paths have been hardcoded.
- All data need to be passed through the preprocessing pipeline and QCed.

 It is more intended to document the project and show how analyses were conducted.  That said, anyone is welcome to use/adapt all code from this repository given proper attribution (see "Citation" section).  Additionally, you are welcome to raise an issue or contact the author to discuss specific steps/scripts.

Note that procedures in `scripts` make some use of a configuration file, which should be placed in `atstaging/config`.  An example is provided at `atstaging/config/example.json`.  The crucial key to set is `"output_directory"`, which sets where derivative files/plots are saved to and loaded from.  READMEs in the scripts folder will refer to this directory as `OUTPUTDIRECTORY`.  The other key-values are primarily required when doing preprocessing.

Setting this file is only really needed when doing preprocessing or when trying to directly run code in the `scripts` folder.  For other applications (deriving NMF projections, staging new data) it should not be necessary.

## Citation

Part of this work is available as a preprint:

- **A unified model for staging amyloid and tau pathology in Alzheimer’s disease** (https://doi.org/10.64898/2026.03.30.26349752)

Additional works are being submitted for publication.  Check back!
