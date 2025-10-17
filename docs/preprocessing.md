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
