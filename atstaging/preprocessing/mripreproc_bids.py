
import datetime as dt
import os

from bias_correction import run_N4_bias_correction
from bids import MRIOutputNamer
from dicom_to_nifiti import run_dcm2niix
from reorient import reorient_image
from skullstrip import run_deepmrseg_dlicv

from atstaging.config import report_configuration
from atstaging.printing import timestamp_print as tsp
from atstaging.printing import begin_command, end_command

def mripreproc_bids(input_img, subject, session, output_directory,
                    overwrite=False):

    print()
    print('-------------------------')
    print('|                       |')
    print('| * MRI Preprocessing * |')
    print('|                       |')
    print('-------------------------')

    print()
    print(f'Date: {str(dt.datetime.now())}')
    print(f'Input image: {input_img}')
    print(f'Output directory: {output_directory}')
    print(f'BIDS Subject: {subject}')
    print(f'BIDS session: {session}')

    report_configuration()

    is_dicom = os.path.isdir(input_img)
    output_directory = os.path.abspath(output_directory)
    if not os.path.isdir(output_directory):
        os.mkdir(output_directory)

    print()
    print('Status:')
    print(f'  - Overwriting existing outputs? {overwrite}')
    print(f'  - Image is DICOM? {is_dicom}')
    print(f'  - Output exists? {os.path.isdir(output_directory)}')

    print()
    print(' * * * * BEGINNING PREPROCESSING * * * *')

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

        print()
        tsp('Running DICOM to NIFTI conversion.')
        tsp(f'Source image: {input_img}')
        tsp(f'Destination image: {starting_image}')

        begin_command('dcm2niix')
        run_dcm2niix(input_img, img_dir, base)
        end_command('dcm2niix')

    else:

        print()
        tsp('Input image is NIFTI; no conversion.')
        starting_image = input_img

    # "preskullstripping" steps
    #  ---> reorientation, bias correction
    preskullstrip = namer.get_path('preskullstrip')
    if not os.path.exists(preskullstrip) or overwrite:

        print()
        tsp('Running pre-skullstripping steps.')
        tsp(f'Source: {starting_image}')
        tsp(f'Destination (reoriented): {preskullstrip}')
        tsp(f'Destination (bias-corrected): {preskullstrip}')

        begin_command('reorient')
        reorient_image(starting_image, 'RPI', preskullstrip)
        end_command('reorient')

        end_command('debias')
        run_N4_bias_correction(preskullstrip, preskullstrip)
        end_command('debias')

    else:
        tsp('Existing preskullstripped image; not rerunning.')

    # skullstripping
    brainmask = namer.get_path('brainmask')
    brain = namer.get_path('brain')

    if not os.path.exists(brain) or overwrite:

        print()
        tsp('Running skullstripping.')
        tsp(f'Source: {preskullstrip}')
        tsp(f'Destination (brain mask): {brainmask}')

        begin_command('skullstrip')
        run_deepmrseg_dlicv(preskullstrip, brainmask)
        end_command('skullstrip')

    print(' * * * * END OF PREPROCESSING * * * *')
    # if not os.path.exists()



inpath = '/scratch/tom.earnest/preproc_testing/rawdata/Accelerated_Sagittal_MPRAGE/2017-03-13_13_38_31.0/I829296/'
subject = '002S0413'
session = '20240905'
output = '/scratch/tom.earnest/preproc_testing/output/'
overwrite = True

mripreproc_bids(input_img=inpath, subject=subject, session=session, output_directory=output, overwrite=overwrite)
