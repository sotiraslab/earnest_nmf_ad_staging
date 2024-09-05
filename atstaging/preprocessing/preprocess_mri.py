
import os

from bias_correction import run_N4_bias_correction
from bids import MRIOutputNamer
from dicom_to_nifiti import run_dcm2niix
from reorient import reorient_image

def bids_mri_pipeline(input_img, subject, session, output_directory):

    is_dicom = os.path.isdir(input_img)
    output_directory = os.path.abspath(output_directory)
    if not os.path.isdir(output_directory):
        os.mkdir(output_directory)

    # setup naming
    namer = MRIOutputNamer(
        subject=subject,
        session=session,
        modality='anat',
        directory=output_directory
        )
    namer.make_img_dir()

    # convert to dicom (if needed)
    if is_dicom:
        starting_image = namer.get_path('dcm2niix')
        img_dir = os.path.dirname(starting_image)
        base = os.path.basename(starting_image).removesuffix('.nii.gz')
        run_dcm2niix(input_img, img_dir, base)
    else:
        starting_image = input_img

    # "preskullstripping" steps
    #  ---> reorientation, bias correction
    preskullstrip = namer.get_path('preskullstrip')
    reorient_image(starting_image, 'RPI', preskullstrip)
    run_N4_bias_correction(preskullstrip, preskullstrip)

inpath = '/scratch/tom.earnest/preproc_testing/rawdata/Accelerated_Sagittal_MPRAGE/2017-03-13_13_38_31.0/I829296/'
subject = '002S0413'
session = '20240905'
output = '/scratch/tom.earnest/preproc_testing/output/'

bids_mri_pipeline(input_img=inpath, subject=subject, session=session, output_directory=output)