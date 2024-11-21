
import argparse
import datetime as dt
import json
import os
import time

from colorama import Fore, Style

from .bias_correction import run_N4_bias_correction
from .bids import ATPreprocMRINamer, ATPreprocPETNamer
from .conversion import run_dcm2niix
from .qc import skullstripping_qc_image, registration_checkerboard_qc_image
from .pet import prepare_registration_pet, register_pet_image
from .reorient import reorient_image
from .registration import apply_transform, create_jacobian_determinant_image, registration_mni_pipeline
from .segmentation import segmentation_pipeline
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

def _apply_file_keep(keep, namer, identifier):
    
    if 'all' in keep:
        print()
        tsp(f'Detected "all" for {identifier}; saving all files.')

    else:
        print()
        tsp('Cleaning up files.')
        tsp(f'Files being kept: {keep}')

        begin_command('cleanup')
        namer.keep_only(keep, verbose=True)
        end_command('cleanup')

def at_mri_pipeline(t1_img, amyloid_img, amyloid_tracer, tau_img, tau_tracer,
                    subject, session, output_directory, config=None):

    if config is not None:
        set_config_by_name(config)
    else:
        set_config_automatic()

    print(Fore.MAGENTA)
    print('-------------------------')
    print('|                       |')
    print('|   * Preprocessing *   |')
    print('|                       |')
    print('-------------------------')
    print(Style.RESET_ALL)

    run_dependency_check()

    print()
    print(Fore.RED + Style.BRIGHT + 'INPUTS' + Style.RESET_ALL)
    print(f'  - Date: {str(dt.datetime.now())}')
    print( '  - Input images:')
    print(f'      * T1: {t1_img}')
    print(f'      * Amyloid PET ({amyloid_tracer}): {amyloid_img}')
    print(f'      * Tau PET ({tau_tracer}): {tau_img}')
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
    t1namer = ATPreprocMRINamer(
        subject=subject,
        session=session,
        modality='anat',
        directory=output_directory)
    amynamer = ATPreprocPETNamer(
        subject=subject,
        session=session,
        tracer=amyloid_tracer,
        modality='pet',
        directory=output_directory)
    taunamer = ATPreprocPETNamer(
        subject=subject,
        session=session,
        tracer=tau_tracer,
        modality='pet',
        directory=output_directory)
    t1namer.make_img_dir()
    amynamer.make_img_dir()
    taunamer.make_img_dir()

    # Information returned by the pipeline
    PATHS = {}
    PATHS['Subject'] = subject
    PATHS['Session'] = session
    PATHS['PathT1'] = t1_img
    PATHS['PathAmyloid'] = amyloid_img
    PATHS['PathTau'] = tau_img

    for name, path in t1namer.namestore.items():
        PATHS['t1_' + name] = path
    
    for name, path in amynamer.namestore.items():
        PATHS['amyloid_' + name] = path

    for name, path in taunamer.namestore.items():
        PATHS['tau_' + name] = path

    # # # # # # # #
    # T1
    # # # # # # # #

    mni_brain = get('mni152_brain')
    
    print()
    tsp('Beginnging with T1 processing...')

    # convert to dicom (if needed)
    if is_dicom:

        starting_image = t1namer.get_path('dcm2niix')
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
    preskullstrip = t1namer.get_path('preskullstrip')
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
    brainmask = t1namer.get_path('brainmask')
    brain = t1namer.get_path('brain')

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
    fullwarp = t1namer.get_path('fullwarp')
    jacobian = t1namer.get_path('jacobian')
    registered = t1namer.get_path('registered')

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

    if not os.path.exists(jacobian) or overwrite:

        print()
        tsp('Creating Jacobian Determinant image.')
        tsp(f'Source (warpfield): {fullwarp}')

        begin_command('jacobian')
        create_jacobian_determinant_image(fullwarp, jacobian)
        end_command('jacobian')

    if not os.path.exists(registered) or overwrite:

        mni_brain = get('mni152_brain')

        print()
        tsp('Creating brain image warped to MNI space.')

        begin_command('apply warp')
        apply_transform(brain, mni_brain, fullwarp, registered)
        end_command('apply warp')

    # segmentation
    #  ---> MUSE, volume CSV generation, PET reference generation
    segmentation = t1namer.get_path('muse')
    volumes = t1namer.get_path('volumes')
    petreference = t1namer.get_path('petreference')

    print()
    tsp('Beginnging MRI segmentation.')

    begin_command('segmentation')
    segmentation_pipeline(brain=brain,
                          out_segmentation=segmentation,
                          out_petreference=petreference,
                          out_volumes=volumes)
    end_command('segmentation')


    # MRI QC images
    # skullstrip_qc = t1namer.get_path('qc-skullstrip')
    # checkerboard_qc = t1namer.get_path('qc-checkerboard')

    # print()
    # tsp('Generating QC images')

    # begin_command('qc-skullstrip')
    # skullstripping_qc_image(preskullstrip, brainmask, skullstrip_qc)
    # end_command('qc-skullstrip')

    # begin_command('qc-checkerboard')
    # registration_checkerboard_qc_image(registered, mni_brain, checkerboard_qc)
    # end_command('qc-checkerboard')

    # # # # # # # #
    # AMYLOID
    # # # # # # # #

    AMYINFO = {}
    amystats = amynamer.get_path('petstats')

    print()
    tsp('Beginnging with amyloid-PET processing...')
    
    # preregistration
    # ---> dcm2niix, coreg, avg, smoothing
    amy_smoothed = amynamer.get_path('smoothed')

    if not os.path.exists(amy_smoothed) or overwrite:
        print()
        tsp('Creating pre-regsitration image for amyloid.')

        begin_command('amyloid-prereg')
        out = prepare_registration_pet(amyloid_img, out_smoothed=amy_smoothed)
        AMYINFO.update(out)
        end_command('amyloid-prereg')
    else:
        print()
        tsp('Existing pre-registration image for amyloid detected; not rerunning.')
    
    # registration
    # ---> registration, SUVR calculation
    amy_registered = amynamer.get_path('registered')
    amy_warp = amynamer.get_path('fullwarp')
    amy_rigid = amynamer.get_path('rigid')
    amy_suvr = amynamer.get_path('origsuvr')
    amy_stats = amynamer.get_path('musestats')
    
    if not os.path.exists(amy_registered) or overwrite:
        print()
        tsp('Registering PET image')
        
        begin_command('amyloid-registration')
        
        out = register_pet_image(pet=amy_smoothed,
                        t1=preskullstrip,
                        brainmask=brainmask,
                        warp=fullwarp,
                        muse_segmentation=segmentation,
                        suvr_reference_mask=petreference,
                        mni_brain=mni_brain,
                        out_registered=amy_registered,
                        out_warp=amy_warp,
                        out_rigid_reg=amy_rigid,
                        out_suvr=amy_suvr,
                        out_regional_suvrs=amy_stats)
        AMYINFO.update(out)
        end_command('amyloid-registration')
    else:
        print()
        tsp('Existing registered image for amyloid detected; not rerunning.')

    if (not os.path.exists(amystats) or overwrite) and len(AMYINFO):
        with open(amystats, 'w') as f:
            json.dump(AMYINFO, f, indent=4)
    
    # # # # # # # #
    # TAU
    # # # # # # # #

    TAUINFO = {}
    taustats = taunamer.get_path('petstats')
    
    print()
    tsp('Beginnging with amyloid-PET processing...')
    
    # preregistration
    # ---> dcm2niix, coreg, avg, smoothing
    tau_smoothed = taunamer.get_path('smoothed')

    if not os.path.exists(tau_smoothed) or overwrite:
        print()
        tsp('Creating pre-regsitration image for tau.')

        begin_command('tau-prereg')
        info = prepare_registration_pet(tau_img, out_smoothed=tau_smoothed)
        TAUINFO.update(info)
        end_command('tau-prereg')
    else:
        print()
        tsp('Existing pre-registration image for tau detected; not rerunning.')
    
    # registration
    # ---> registration, SUVR calculation
    tau_registered = taunamer.get_path('registered')
    tau_warp = taunamer.get_path('fullwarp')
    tau_rigid = taunamer.get_path('rigid')
    tau_suvr = taunamer.get_path('origsuvr')
    tau_stats = taunamer.get_path('musestats')
    
    if not os.path.exists(tau_registered) or overwrite:
        print()
        tsp('Registering PET image')
        
        begin_command('tau-registration')
        
        info = register_pet_image(pet=tau_smoothed,
                        t1=preskullstrip,
                        brainmask=brainmask,
                        warp=fullwarp,
                        muse_segmentation=segmentation,
                        suvr_reference_mask=petreference,
                        mni_brain=mni_brain,
                        out_registered=tau_registered,
                        out_warp=tau_warp,
                        out_rigid_reg=tau_rigid,
                        out_suvr=tau_suvr,
                        out_regional_suvrs=tau_stats)
        TAUINFO.update(info)
        end_command('tau-registration')
    else:
        print()
        tsp('Existing registered image for tau detected; not rerunning.')

    if (not os.path.exists(taustats) or overwrite) and len(TAUINFO):
        with open(taustats, 'w') as f:
            json.dump(TAUINFO, f, indent=4)

    # # # # # # # #
    # CLEANUP
    # # # # # # # #
    
    keep_t1 = get('mri_preproc_keep')
    keep_amy = get('amy_preproc_keep')
    keep_tau = get('tau_preproc_keep')
    _apply_file_keep(keep_t1, t1namer, 'T1')
    _apply_file_keep(keep_amy, amynamer, 'amyloid-PET')
    _apply_file_keep(keep_tau, taunamer, 'tau-PET')

    print(Fore.MAGENTA + Style.BRIGHT + ' * * * * END OF PREPROCESSING * * * *' + Style.RESET_ALL)
    endtime = time.time()
    elapsed = int(endtime - starttime)
    m, s = divmod(elapsed, 60)
    h, m = divmod(m, 60)
    print(f'Elapsed Time: {h}h:{m}m:{s}s')
    print()

    return PATHS

def main():
    args = parse()
    at_mri_pipeline(**vars(args))

if __name__ == '__main__':
    main()
