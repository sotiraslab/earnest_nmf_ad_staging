
import argparse
import datetime as dt
import time
import os

from colorama import Fore, Style

from .bias_correction import run_N4_bias_correction
from .bids import ATPreprocOutputNamer
from .dicom_to_nifiti import run_dcm2niix
from .qc import skullstripping_qc_image, registration_checkerboard_qc_image
from .reorient import reorient_image
from .registration import apply_transform, create_jacobian_determinant_image, registration_mni_pipeline
from .skullstrip import apply_brainmask, run_deepmrseg_dlicv

from .debug import run_dependency_check

from atstaging.config import get, report_configuration, set_config_automatic, set_config_by_name
from atstaging.printing import timestamp_print as tsp
from atstaging.printing import begin_command, end_command

def parse(arguments=None):

    parser = argparse.ArgumentParser()

    parser.add_argument('-M', '--mri', required=True, dest='t1_img', help='Input T1 image to preprocess.')
    parser.add_argument('-A', '--amyloid', required=True, dest='amyloid_img', help='Input aymloid PET image to preprocess.')
    parser.add_argument('-T', '--tau', required=True, dest='tau_img', help='Input tau PET image to preprocess.')
    parser.add_argument('-o', '--output', required=True, dest='output_directory', help='BIDS directory to create outputs')
    parser.add_argument('--sub', required=True, dest='subject', help='BIDS subject for image.')
    parser.add_argument('--ses', required=True, dest='session', help='BIDS session for image.')
    parser.add_argument('-c', '--config', required=False, help='Name of a config file to use for this run.')

    args = parser.parse_args(args=arguments)

    return args

def at_mri_pipeline(t1_img, amyloid_img, tau_img,
                    subject, session, output_directory, config=None):

    if config is not None:
        set_config_by_name(config)
    else:
        set_config_automatic()

    print(Fore.MAGENTA)
    print('-------------------------')
    print('|                       |')
    print('| * MRI Preprocessing * |')
    print('|                       |')
    print('-------------------------')
    print(Style.RESET_ALL)

    run_dependency_check()

    print()
    print(Fore.RED + Style.BRIGHT + 'INPUTS' + Style.RESET_ALL)
    print(f'  - Date: {str(dt.datetime.now())}')
    print(f'  - Input image: {t1_img}')
    print(f'  - Output directory: {output_directory}')
    print(f'  - BIDS Subject: {subject}')
    print(f'  - BIDS session: {session}')

    is_dicom = os.path.isdir(t1_img)
    output_directory = os.path.abspath(output_directory)
    if not os.path.isdir(output_directory):
        os.mkdir(output_directory)

    overwrite = get('overwrite_preproc')

    print()
    print(Fore.RED + Style.BRIGHT + 'STATUS' + Style.RESET_ALL)
    print(f'  - Overwriting existing outputs? {overwrite}')
    print(f'  - Image is DICOM? {is_dicom}')
    print(f'  - Output exists? {os.path.isdir(output_directory)}')

    report_configuration()

    print()
    print(Fore.MAGENTA + Style.BRIGHT + ' * * * * BEGINNING PREPROCESSING * * * *' + Style.RESET_ALL)

    starttime = time.time()

    # setup naming
    namer = ATPreprocOutputNamer(
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
        tsp(f'Source image: {t1_img}')
        tsp(f'Destination image: {starting_image}')

        begin_command('dcm2niix')
        run_dcm2niix(t1_img, img_dir, base)
        end_command('dcm2niix')

    else:

        print()
        tsp('Input image is NIFTI; no conversion.')
        starting_image = t1_img

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
        print()
        tsp('Existing preskullstripped image; not rerunning.')

    # skullstripping
    brainmask = namer.get_path('brainmask')
    brain = namer.get_path('brain')

    if not os.path.exists(brainmask) or overwrite:

        print()
        tsp('Running skullstripping.')
        tsp(f'Source: {preskullstrip}')
        tsp(f'Destination (brain mask): {brainmask}')

        begin_command('skullstrip')
        run_deepmrseg_dlicv(preskullstrip, brainmask)
        end_command('skullstrip')
    else:
        print()
        tsp('Existing brain mask; not rerunning.')

    if not os.path.exists(brain) or overwrite:
        print()
        tsp('Generating skullstripped brain image.')
        tsp(f'Source (T1): {preskullstrip}')
        tsp(f'Source (brainmask): {brainmask}')
        tsp(f'Destination (brain): {brain}')

        begin_command('apply_brainmask')
        apply_brainmask(t1=preskullstrip, brainmask=brainmask, outpath=brain)
        end_command('apply_brainmask')

    # registration
    # ---> registration, warp concatenation, jacobian determinant
    fullwarp = namer.get_path('fullwarp')
    jacobian = namer.get_path('jacobian')
    registered = namer.get_path('registered')

    if not os.path.exists(fullwarp) or overwrite:

        print()
        tsp('Registering brain to MNI template.')

        begin_command('registration')
        registration_mni_pipeline(brain=brain,
                                  quick=get('quick'),
                                  transformation='s',
                                  out_fullwarp=fullwarp,
                                  out_jacobian=jacobian,
                                  out_registered=registered)
        end_command('registration')

    else:
        print()
        tsp('Existing registration outputs, not rerunning.')

    if not os.path.exists(jacobian):

        print()
        tsp('Creating Jacobian Determinant image.')
        tsp(f'Source (warpfield): {fullwarp}')

        begin_command('jacobian')
        create_jacobian_determinant_image(fullwarp, jacobian)
        end_command('jacobian')

    if not os.path.exists(registered):

        mni_brain = get('mni152_brain')

        print()
        tsp('Creating brain image warped to MNI space.')

        begin_command('apply warp')
        apply_transform(brain, mni_brain, fullwarp, registered)
        end_command('apply warp')

    # QC images
    skullstrip_qc = namer.get_path('qc-skullstrip')
    checkerboard_qc = namer.get_path('qc-checkerboard')

    print()
    tsp('Generating QC images')

    begin_command('qc-skullstrip')
    skullstripping_qc_image(preskullstrip, brainmask, skullstrip_qc)
    end_command('qc-skullstrip')

    begin_command('qc-checkerboard')
    mni_brain = get('mni152_brain')
    registration_checkerboard_qc_image(registered, mni_brain, checkerboard_qc)
    end_command('qc-checkerboard')

    # cleanup
    keep = get('mri_preproc_keep')

    if 'all' in keep:
        print()
        tsp('Detected "all" in "mri_preproc_keep"; saving all files.')

    else:
        print()
        tsp('Cleaning up files.')
        tsp(f'Files being kept: {keep}')

        begin_command('cleanup')
        namer.keep_only(keep, verbose=True)
        end_command('cleanup')

    print(Fore.MAGENTA + Style.BRIGHT + ' * * * * END OF PREPROCESSING * * * *' + Style.RESET_ALL)
    endtime = time.time()
    elapsed = int(endtime - starttime)
    m, s = divmod(elapsed, 60)
    h, m = divmod(m, 60)
    print(f'Elapsed Time: {h}h:{m}m:{s}s')
    print()

def main():
    args = parse()
    at_mri_pipeline(**vars(args))

if __name__ == '__main__':
    main()
