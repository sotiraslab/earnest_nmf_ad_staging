# Image preprocessing

This image documents the MRI/PET preprocessing pipeline and provides instructions on how to rerun it.  It is more generally covering the pipeline rather than the specific processing used for the research project.

## Overview

This pipeline does volumetric PET processing.  A T1 MRI is required for preprocessing to generate a registration to a standard template space (in this case, MNI152 1mm).  Basically a PET>T1 registration is learned, as well as a T1>MNI registration.  These are concatenated to move the PET image to MNI space.

Specific steps are as follows, with specific softwares highlighted in brackets.  **Please also consult the following section for additional notes and caveats regarding the processing.**

* **T1 processing**
  * Conversion from DICOM to NIFTI, if neeed [dcm2niix]
  * Reorientation of the image to RPI [nibabel]
  * Bias correction [ANTS:N4]
  * Skullstripping [DeepMRSeg:DLIVC]
  * Regional segmentation [DeepMRSeg:MUSE]
  * Registration to MNI template [ANTS:SyN]
* **PET processing**
  * Conversion to NIFTI format, from DICOM [dcm2niix] or ECAT [nibabel]
  * Reorientation of the image to RPI [nibabel]
  * If a multiframe image, frame realignment [FSL:MCFLIRT] and averaging [nibabel]
  * Smoothing [AFNI:3dFWHMx/python]
  * Coregistration of the PET image with the T1 [FSL:FLIRT]
  * Creation of an SUVR image (in PET space), using a reference mask defined by the T1 segmentation
  * Skullstripping the SUVR image by moving the brainmask to PET space.
  * Registering the SUVR image to MNI space using a concatentation of the PET>T1 and T1>MNI registrations

## Additional processing notes

* For the most part, the specific softwares required for processing are fixed.  There are some exceptions for which multiple versions of tools have been implemented (see the section below on configuration).
* The code was written for processing of individuals who had amyloid-PET, tau-PET, T1 imaging.  As such, many of the tools are setup to expect those as inputs.  However, the minimum requirement for processing is just a T1 image.  None, either, or both PET tracers can be specified.
* The code requires you to specify the tracer used for amyloid or tau.  This is purely for labeling of outputs within the BIDS structure.  It has specifically been tested on various amyloid (FBP, FBB, PIB, NAV) and tau (FTP, PI2620, MK6240) tracers.
* **⚠️ The reference region used is the cerebellar gray matter (from the MUSE segmentation) and it is currently hardcoded to be so.**  The same region is used for both amyloid and tau.  Correspondingly, passing tracers for other biological targets is probably not recommended (unless the same reference region is suitable).
* Smoothing is done as a last step prior to registration (although it can be done post-registration, see configuration).  The specific algorithm is a modified version of the that described in the robust PET only processing (rPOP) paper ([https://doi.org/10.1016/j.neuroimage.2021.118775](https://doi.org/10.1016/j.neuroimage.2021.118775)).  The idea is to use AFNI's 3dFWHMx to estimate the current resolution of the image and apply smoothing to reach a desired resolution (again, as measured by 3dFWHMx\*).  Rather than calculating the kernel to use analytically as rPOP does\*\*, we start with a small kernel and gradually increase it to reach the desired resolution.  [The specific function is found here.](https://github.com/sotiraslab/at_nmf_sustain/blob/144450194be75de3c3a7f9a324bcb16a3bde8eee/atstaging/preprocessing/smoothing.py#L76)
  * \* We found that 3dFWHMx may disagree with other measures of effective resolution.  Specifically, ADNI images labeled to have 8mm FWHM tended to read as 10mm FWHM under 3dFWHMx.  But the 3dFWHMx readings are consistent, and the algorithm does a decent job at getting images to a specified resolution.
  * \*\* We found that the rPOP approach tended to over-smooth images, so we developed this iterative approach as an alternative.
* ⚠️ **The pipeline is ignorant of specific frame timings and does not automatically extract active windows!**  If a multiframe image is passed, it must only include the frames of interest for the image.  Single volume images can also be passed (i.e., already averaged or summed).

## Pipeline outputs

Each subject is directed to an output folder when processing.  This folder will be populated with BIDS-like output (it will almost certainly fail a BIDS validation tool).  The basic structure of image outputs is as follows:

```bash
[OUTPUTFOLDER]/sub-[SUBJECT]/ses-[SESSION]/anat/<t1outputimage>.nii.gz
[OUTPUTFOLDER]/sub-[SUBJECT]/ses-[SESSION]/pet/<petoutputimage>.nii.gz
```

The square bracketed information are user specified parameters when calling the pipeline; the triangular bracket text names are generated automatically by the pipeline.

The output folder will mostly be populated by subject folders.  Additional subfolders are also automatically generated:

- `logs`: If running with SLURM, the output log files from each job of batch processing.  These are labelled with `sub-[SUBJECT]_ses-[SESSION].log` format, and will be overwritten when the same subject/session pair is reprocessed.
- `paths`: A JSON file for each subject/session which specifies the paths to all potential pipeline derivatives for that subject.  These [can be stitched into a table](https://github.com/sotiraslab/at_nmf_sustain/blob/2ee1ecce20499f9e252ba624a02f0f817e412179/atstaging/outputs.py#L164) which shows output paths for all processed files.  Though note, not all paths specified by this file will actually exist - in part because not all derivatives are saved and in part because of processing failures.
- `qc`: a folder to contain quality control outputs.  This is not automatically generated but can be created with an additional command.  See the QC section below.

# Installing the pipline

This section will cover the installation of the pipeline.  The basic things that need to be done are:

1. Install all software dependencies
2. Install the Python package contained in this repo
3. Set the configuration files, specifically the JSON config and the SLURM setup script.

## 1. Install software dependencies

The following softwares must be installed to use this pipeline.  Specifically, the commands specified below must be available within the Python environment from which you run the command to start processing, or instead in the compute environment where the preprocessing is done.

| Software  | Tools Required                                                                                                                                                                   | Versions used for this project (approximate) |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| AFNI      | `3dFWHMx`                                                                                                                                                                      | v20.3.03                                     |
| ANTS      | `antsApplyTransforms`,<br />`antsRegistrationSyN.sh `, `antsRegistrationSyNQuick.sh `, `CreateJacobianDeterminantImage `, `ImageMath`,<br />`N4BiasFieldCorrection`, | v2.4.0                                       |
| C3D       | `c3d_affine_tool`                                                                                                                                                              | v1.0                                         |
| dcm2niix  | `dcm2niix`                                                                                                                                                                     | v1.0.20220505                                |
| DeepMRSeg | `deepmrseg_apply`                                                                                                                                                              | Python v3.8.20, DeepMRSeg v0.1.0             |
| FSL       | `flirt`, `mcflirt`                                                                                                                                                           | v6.0.7.8                                     |

For DeepMRSeg installation, you need to set up a conda enviornment containing the software.  The basic steps of how to do so are described [here](https://github.com/CBICA/DeepMRSeg?tab=readme-ov-file#installation-instructions).

Whenever a subject is processed, the software will run a depenency check which will check if the software is installed (only for a general tool from each suite, not all the needed tools).  The code will not exit if all dependencie are not found, but a warning will be shown in the text output/log.

## 2. Install the Python code

This repository contains a python package called `atstaging`.  This package contains the preprocessing code (most of which is in `atstaging.preprocessing`).  You can clone/download the respository and install the required code (in a Python environment):

```bash
cd at_nmf_sustain
pip install -e .
```

**You need to set configurations by editing a couple files in this source folder, so keep track of it (next section).**

Python dependenices are specified in `setup.py` and `pyproject.toml`.  Please let me know if some required dependencies are not covered.  This code was run successfully with Python=3.10.16.

After installation, some new command line shortcuts should become available.  Test (for example) with:

```bash
atproc_subject -h
```

## 3. Set your configuration

There are two primary files that need to be configured.  Configuration files are stored in `atstaging/config`.  **Both of these will need to be manually updated!**

1. The configuration JSON file.
2. The SLURM setup script (only needed if running with SLURM)

### Setting the configuration JSON

The most important is a JSON file which sets several parameters.  There is an example `example.json` committed to the repo - this will not be a working configuration but it can be used as a template.  Make a copy of this file and rename it to anything you choose (e.g., `main.json` or `config.json` or `experiment_parameters.json`).  The table below denotes all the configuration settings.  **All of these must be set to some value, however not all are strictly necessary for processing.** For non-required fields, the default value can be left.

| Field                       | Type    | Required | Description                                                |
| --------------------------- | ------- | -------- | ---------------------------------------------------------- |
| `AUTOUSE`                 | boolean | yes      | Automatically use this config file if not otherwise set    |
| `amy_preproc_keep`        | list    | yes      | Specify amyloid-PET derivatives to keep after processing.  |
| `amyloidpetnet_directory` | string  | no       | Path to the source code AmyloidPETNet                      |
| `amyloidpetnet_env`       | string  | no       | Conda environment name for AmyloidPETNet                   |
| `deepmrseg_env`           | string  | yes      | Name of the conda environment with DeepMRSeg installed.    |
| `hdbet_env`               | string  | no       | Name of the conda environment with HD-BET installed.       |
| `font_for_plots`          | string  | no       | Path to a TTF font file used for plotting                  |
| `font_for_plots_bold`     | string  | no       | Path to a (bold) TTF font file used for plotting           |
| `mni152_brain`            | string  | yes      | Path to the MNI152 template.                               |
| `mri_preproc_keep`        | string  | yes      | Specify T1 derivatives to keep                             |
| `mri2mni_transformation`  | string  | yes      | Type of ANTs registration for T1>MNI                       |
| `output_directory`        | string  | no       | Root output folder for the project                         |
| `overwrite_pet`           | boolean | yes      | Overwrite existing PET outputs                             |
| `overwrite_t1`            | boolean | yes      | Overwrite existing T1 outputs                              |
| `quick`                   | boolean | yes      | Use the fast ANTs registration rather than full version.   |
| `skullstrip_method`       | string  | no       | Tool to use for skullstripping                             |
| `smoothing`               | struct  | yes      | Parameters for PET smoothing                               |
| `slurm`                   | struct  | yes      | Parameters for running jobs with SLURM                     |
| `tablecols`               | struct  | yes      | Format the table headers for `atproc_table`              |
| `tau_preproc_keep`        | list    | yes      | Specify the tau-PET derivatives to keep after processing.  |
| `use_muse_brain`          | boolean | no       | Use MUSE mask for skullstripping (has no effect currently) |

- `AUTOUSE` allows one config to be automatically set.  This allows for a bit more automation, as one set of parameters will be used by default and the config need not be specified for every preprocessing call.  However, I found it is nice to still explicitly set the config to be sure.
- `amy_preproc_keep`, `mri_preproc_keep`, and `tau_preproc_keep` specify the derivative files that are saved.  The total list of possible keys are listed [here for MRI ](https://github.com/sotiraslab/at_nmf_sustain/blob/2ee1ecce20499f9e252ba624a02f0f817e412179/atstaging/preprocessing/bids.py#L83-L101)and [here for PET](https://github.com/sotiraslab/at_nmf_sustain/blob/2ee1ecce20499f9e252ba624a02f0f817e412179/atstaging/preprocessing/bids.py#L109-L125).  They are also listed in the JSON files of the `paths` folder.  Note that for PET, you should not include `amyloid-` or `tau-` (as they appear in the `paths` folder).
  - **Files are only included if they are specified!**  The `example.json` config is basically the minimum amount of files that should be kept for PET analysis.
  - It is advisable to keep files which are expensive to create, especially the brain mask and the nonlinear registration.  These files can be reused for reruns if needing to create more files.
  - You can instead include `"all"` to skip the cleanup step which removes files.
- AmyloidPETNet is not run as part of the preprocessing pipeline, but was used for some downstream analysis.  So setting `amyloidpetnet_directory` and `amyloidpetnet_env` are not needed.
- `skullstrip_method` can be set to `"dlicv"` or `"hdbet"` to run DeepMRSeg or HD-BET respectively.  For whichever method is used, there must be a conda environment available containing the package (`deepmrseg_env` or `hdbet_env`).  However, DeepMRSeg is the default and also must be used for segementation currently.
  - `use_muse_brain` was a test option to use a very strict brain mask for processing, but this is not recommended and is currently harcoded to not work.
- The two `font...` configurations are strictly for downstream analysis and not relevant for processing.
- `mni152_brain` must be provided - it can be 1mm or 2mm (the former used for this project) and should be just the brain.
- `mri2mni_transformation` is passed to the transformation type `-t` argument of ANTs registration.  `s` specifies the SyN registration.
- `output_directory` is mostly relevant for the analysis that occurs after preprocessing in this repository.  **It is not the preprocessing output directory - rather a root output directory for all analyses.**
- If set to `false`, the `overwrite_...` arguments will not regenerate some derivative files if they are already found to exist.  It doesn't check all derivative files but some key ones.
- `quick` can be used to use `antsRegistrationSyNQuick.sh` instead of `antsRegistrationSyN.sh`.  The former is good for debugging but the latter is better for actual analysis.
- `smoothing` specifies the PET smoothing parameters:
  - If `prereg` is `true`, smoothing is done prior to registration (default).  Otherwise, smoothing can be applied as a last step after registration.
  - If `do_smoothing` is `false`, no smoothing will be done.
  - `x`, `y`, and `z` specify the target FWHM in each direction.
- `slurm` sets resource/time limits for running with SLURM on a computing cluster.

### Setting the SLURM configuration

For running parallel jobs with SLURM, the config folder has a script `slurm_setup.sh`.  This will be called by the [batch script that is submitted to the scheduler ](https://github.com/sotiraslab/at_nmf_sustain/blob/2ee1ecce20499f9e252ba624a02f0f817e412179/atstaging/cli/atproc_batch.sh)for each processing job.  It will probably need to be updated to match your computing cluster (although this will only work with SLURM!).  It should do the following:

- Activate the conda environment containing the `atstaging` package
- Load any required software.

# Running the pipeline

## Running individual subjects

The primary command for running a single subject is `atproc_subject` ([source](https://github.com/sotiraslab/at_nmf_sustain/blob/2ee1ecce20499f9e252ba624a02f0f817e412179/atstaging/cli/atproc_subject.py)).  The base call for running is as so (all arguments required):

```bash
atproc_subject --sub [SUBJECT] --ses [SESSION] --output [OUTPUTDIR] --t1 [T1PATH]
```

**Note that the subject and session must be manually supplied.**  They are not automatically detected from the image.

You can specify different sessions for the same subject to process different longitudinal sessions for a single subject.

You can additionally specify amyloid and tau images to process with:

```bash
atproc_subject ... --amyloid [AMYLOIDPATH] --amyloid-tracer [AMYLOIDTRACER] --tau [TAUPATH] --tau-tracer [TAUTRACER]
```

The tracers must be manually specified for labelling outputs.

Finally `--config` can be used to manually choose a config file, and `--slurm` can be used to submit the processing job to the cluster rather than processing it in the current compute environment (but note there is a tool for running batch processing with SLURM, see below).

Processing a single subject takes around 2-3 hours in our experience.

## Batch processing

The function `atproc_table` ([source](https://github.com/sotiraslab/at_nmf_sustain/blob/2ee1ecce20499f9e252ba624a02f0f817e412179/atstaging/cli/atproc_table.py)) can be used to process many individuals, ideally with the compute cluster for parallel processing.  The base call looks lke so:

```bash
atproc_table my_processing_table.csv 
```

The docstring for this function (`atproc_table -h`) contains information on how the table should be formatted to specify the subjects to process.

This is the recommended way to process many subjects with SLURM.  A few notes on this:

- SLURM is automatically used unless `--no-slurm` is passed.
- This is mostly geared towards the CHPC cluster at WashU; additional development may be needed to adapt this code to other clusters.
- In the configuration file, see the  `slurm` key to specify batch submission parameters.  Currently only a few key parameters are configureable.
- Also make sure to set the `slurm_setup.sh` script.

## Quality control (QC)

After processing, you can point `atproc_qc` ([source](https://github.com/sotiraslab/at_nmf_sustain/blob/2ee1ecce20499f9e252ba624a02f0f817e412179/atstaging/cli/atproc_qc.py)) to your output folder.  This will generate a `qc` subfolder in the output folder, and will generate the following outputs:

- epilogues.csv: Tabularized version of metadata pulled from the output logs of SLURM runs.
- filecounts.csv: Simple count of files in each subject/session subfolder.
- imagestats.xlsx: Coarse summary statistics for various images of interest ([specified here](https://github.com/sotiraslab/at_nmf_sustain/blob/2ee1ecce20499f9e252ba624a02f0f817e412179/atstaging/preprocessing/qc_tools.py#L433)).
- musestats_amyloid.csv and musestats_tau.csv: MUSE regional SUVRs and volumes collected into a table
- screenshots: A folder containing a subfolder for each type of QC image (that was specified to be saved; see configuration JSON).  A screenshotQC.csv file is also created which initiates a PASS and NOTES column for each variety of screenshot, which can be used for tracking visual inspection of files.

Note that rerunning atproc_qc will not overwrite existing QC information saved in screenshotsQC.csv.  If more images are processed at a later date, more rows will be added.
