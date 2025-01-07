
import datetime as dt
import json
import os
import time

from colorama import Fore, Style
import pandas as pd

from .bias_correction import run_N4_bias_correction
from .bids import ATPreprocMRINamer, ATPreprocPETNamer
from .conversion import run_dcm2niix
from .qc import (
    pet_mni_registration_qc_image,
    pet_t1_registration_qc_image,
    registration_checkerboard_qc_image,
    skullstripping_qc_image,
    suvr_qc_image,
    )
from .pet import prepare_registration_pet, register_pet_image
from .reorient import reorient_image
from .registration import apply_transform, registration_mni_pipeline
from .segmentation import segmentation_pipeline
from .skullstrip import apply_brainmask, run_deepmrseg_dlicv

from .debug import run_dependency_check

from atstaging.config import get, report_configuration, set_config_automatic, set_config_by_name
from atstaging.printing import timestamp_print as tsp
from atstaging.printing import begin_command, end_command

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

def at_mri_pipeline(subject, session, output_directory, t1_img,
                    amyloid_img=None, amyloid_tracer=None, tau_img=None, tau_tracer=None,
                    config=None):

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

    overwrite_pet = get('overwrite_pet')
    overwrite_t1 = get('overwrite_t1')

    print()
    print(Fore.RED + Style.BRIGHT + 'STATUS' + Style.RESET_ALL)
    print(f'  - Overwriting existing T1 outputs? {overwrite_t1}')
    print(f'  - Overwriting existing PET outputs? {overwrite_pet}')
    print(f'  - Image is DICOM? {is_dicom}')
    print(f'  - Output exists? {os.path.isdir(output_directory)}')

    report_configuration()

    # screen MRI2MNI transformation
    mri2mni_transformation = get('mri2mni_transformation')
    if mri2mni_transformation in['t', 'r', 'a']:
        is_linear_transformation = True
    elif mri2mni_transformation in ['s', 'sr', 'so']:
        is_linear_transformation = False
    else:
        raise ValueError(f'Transformation type {mri2mni_transformation} not recognized by this pipeline.')

    print()
    print(Fore.MAGENTA + Style.BRIGHT + ' * * * * BEGINNING PREPROCESSING * * * *' + Style.RESET_ALL)

    starttime = time.time()

    # variables for whether PET is being processed
    PROCESS_AMY = (amyloid_img is not None) and (amyloid_tracer is not None)
    PROCESS_TAU = (tau_img is not None) and (tau_tracer is not None)

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
    if PROCESS_AMY:
        amynamer.make_img_dir()
    if PROCESS_TAU:
        taunamer.make_img_dir()

    # Information returned by the pipeline
    PATHS = {}
    PATHS['Subject'] = subject
    PATHS['Session'] = session
    PATHS['PathT1'] = t1_img
    PATHS['PathAmyloid'] = amyloid_img
    PATHS['TracerAmyloid'] = amyloid_tracer
    PATHS['PathTau'] = tau_img
    PATHS['TracerTau'] = tau_tracer

    for name in t1namer.namestore.keys():
        PATHS['t1_' + name] = t1namer.get_path(name)
    
    if PROCESS_AMY:
        for name in amynamer.namestore.keys():
            PATHS['amyloid_' + name] = amynamer.get_path(name)

    if PROCESS_TAU:
        for name in taunamer.namestore.keys():
            PATHS['tau_' + name] = taunamer.get_path(name)

    # save path information
    procpathsdir = os.path.join(output_directory, 'paths')
    if not os.path.isdir(procpathsdir):
        os.mkdir(procpathsdir)
    
    pathsjson = os.path.join(procpathsdir, f'sub-{subject}_ses-{session}.json')
    with open(pathsjson, 'w') as f:
        json.dump(PATHS, f, indent=4)

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
    if not os.path.exists(preskullstrip) or overwrite_t1:

        print()
        tsp('Running pre-skullstripping steps.')
        tsp(f'Source: {starting_image}')
        tsp(f'Destination (reoriented): {preskullstrip}')
        tsp(f'Destination (bias-corrected): {preskullstrip}')

        begin_command('reorient')
        reorient_image(starting_image, 'RPI', preskullstrip)
        end_command('reorient')

        begin_command('debias')
        run_N4_bias_correction(preskullstrip, preskullstrip)
        end_command('debias')

    else:
        print()
        tsp('Existing preskullstripped image; not rerunning.')

    # skullstripping
    brainmask = t1namer.get_path('brainmask')
    brain = t1namer.get_path('brain')

    if not os.path.exists(brainmask) or overwrite_t1:

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

    if not os.path.exists(brain) or overwrite_t1:
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
    affine = t1namer.get_path('affine')
    fullwarp = t1namer.get_path('fullwarp')
    registered = t1namer.get_path('registered')

    mri2mni_transformation_file = affine if is_linear_transformation else fullwarp

    if not os.path.exists(mri2mni_transformation_file) or overwrite_t1:

        print()
        tsp('Registering brain to MNI template.')

        begin_command('registration')
        registration_mni_pipeline(brain=brain,
                                  quick=get('quick'),
                                  transformation=mri2mni_transformation,
                                  out_affine=affine,
                                  out_fullwarp=fullwarp,
                                  out_registered=registered)
        end_command('registration')

    else:
        print()
        tsp('Existing registration outputs, not rerunning.')

    if not os.path.exists(registered) or overwrite_t1:

        mni_brain = get('mni152_brain')

        print()
        tsp('Creating brain image warped to MNI space.')

        begin_command('apply warp')
        apply_transform(brain, mni_brain, mri2mni_transformation_file, registered)
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
    skullstrip_qc = t1namer.get_path('qc-skullstrip')
    checkerboard_qc = t1namer.get_path('qc-checkerboard')

    print()
    tsp('Generating QC images')

    begin_command('qc-skullstrip')
    skullstripping_qc_image(preskullstrip, brainmask, skullstrip_qc)
    end_command('qc-skullstrip')

    begin_command('qc-checkerboard')
    registration_checkerboard_qc_image(registered, mni_brain, checkerboard_qc)
    end_command('qc-checkerboard')

    # # # # # # # #
    # PET - SMOOTHING
    # # # # # # # # 

    do_smoothing = get('smoothing', 'do_smoothing')
    smooth_x = float(get('smoothing', 'x'))
    smooth_y = float(get('smoothing', 'y'))
    smooth_z = float(get('smoothing', 'z'))
    target_fwhm = (smooth_x, smooth_y, smooth_z) if do_smoothing else None

    # # # # # # # #
    # AMYLOID
    # # # # # # # #

    if PROCESS_AMY:
        AMYINFO = {}
        amystats = amynamer.get_path('petstats')

        print()
        tsp('Beginnging with amyloid-PET processing...')
        
        # preregistration
        # ---> dcm2niix, coreg, avg, smoothing
        amy_prereg = amynamer.get_path('preregistration')

        if not os.path.exists(amy_prereg) or overwrite_pet:
            print()
            tsp('Creating pre-regsitration image for amyloid.')

            begin_command('amyloid-prereg')
            out = prepare_registration_pet(amyloid_img, out_final=amy_prereg, target_fwhm=target_fwhm)
            AMYINFO.update(out)
            end_command('amyloid-prereg')
        else:
            print()
            tsp('Existing pre-registration image for amyloid detected; not rerunning.')
        
        # registration
        # ---> registration, SUVR calculation
        amy_registered = amynamer.get_path('registered')
        amy_pet2mni = amynamer.get_path('fullmat') if is_linear_transformation else amynamer.get_path('fullwarp')
        amy_rigid = amynamer.get_path('rigid')
        amy_suvr = amynamer.get_path('origsuvr')
        amy_stats = amynamer.get_path('musestats')
        
        if not os.path.exists(amy_registered) or overwrite_pet:
            print()
            tsp('Registering PET image')
            
            begin_command('amyloid-registration')
            
            out = register_pet_image(pet=amy_prereg,
                            t1=preskullstrip,
                            brainmask=brainmask,
                            mri2mni_transform=mri2mni_transformation_file,
                            muse_segmentation=segmentation,
                            suvr_reference_mask=petreference,
                            mni_brain=mni_brain,
                            out_registered=amy_registered,
                            out_pet2mni=amy_pet2mni,
                            out_rigid_reg=amy_rigid,
                            out_suvr=amy_suvr,
                            out_regional_suvrs=amy_stats)
            AMYINFO.update(out)
            end_command('amyloid-registration')
        else:
            print()
            tsp('Existing registered image for amyloid detected; not rerunning.')

        if (not os.path.exists(amystats) or overwrite_pet) and len(AMYINFO):
            with open(amystats, 'w') as f:
                json.dump(AMYINFO, f, indent=4)

        # amyloid QC images
        suvr_qc = amynamer.get_path('qc-suvr')
        coreg_qc = amynamer.get_path('qc-coregistration')
        petreg_qc = amynamer.get_path('qc-registration')

        print()
        tsp('Generating QC images')

        begin_command('qc-suvr')
        suvr_qc_image(amy_suvr, output=suvr_qc)
        end_command('qc-suvr')

        begin_command('qc-coregistration')
        pet_t1_registration_qc_image(registeredpet=amy_rigid, t1=preskullstrip, output=coreg_qc)
        end_command('qc-coregistration')

        begin_command('qc-registration')
        pet_mni_registration_qc_image(registeredpet=amy_registered, mni=mni_brain, output=petreg_qc)
        end_command('qc-registration')
    else:
        print()
        tsp("No amyloid image or amyloid tracer provided; not doing amyloid processing.")
    
    # # # # # # # #
    # TAU
    # # # # # # # #

    if PROCESS_TAU:
        TAUINFO = {}
        taustats = taunamer.get_path('petstats')
        
        print()
        tsp('Beginnging with tau-PET processing...')
        
        # preregistration
        # ---> dcm2niix, coreg, avg, smoothing
        tau_prereg = taunamer.get_path('preregistration')

        if not os.path.exists(tau_prereg) or overwrite_pet:
            print()
            tsp('Creating pre-regsitration image for tau.')

            begin_command('tau-prereg')
            info = prepare_registration_pet(tau_img, out_final=tau_prereg, target_fwhm=target_fwhm)
            TAUINFO.update(info)
            end_command('tau-prereg')
        else:
            print()
            tsp('Existing pre-registration image for tau detected; not rerunning.')
        
        # registration
        # ---> registration, SUVR calculation
        tau_registered = taunamer.get_path('registered')
        tau_pet2mni = taunamer.get_path('fullmat') if is_linear_transformation else taunamer.get_path('fullwarp')
        tau_rigid = taunamer.get_path('rigid')
        tau_suvr = taunamer.get_path('origsuvr')
        tau_stats = taunamer.get_path('musestats')
        
        if not os.path.exists(tau_registered) or overwrite_pet:
            print()
            tsp('Registering PET image')
            
            begin_command('tau-registration')
            
            info = register_pet_image(pet=tau_prereg,
                            t1=preskullstrip,
                            brainmask=brainmask,
                            mri2mni_transform=mri2mni_transformation_file,
                            muse_segmentation=segmentation,
                            suvr_reference_mask=petreference,
                            mni_brain=mni_brain,
                            out_registered=tau_registered,
                            out_pet2mni=tau_pet2mni,
                            out_rigid_reg=tau_rigid,
                            out_suvr=tau_suvr,
                            out_regional_suvrs=tau_stats)
            TAUINFO.update(info)
            end_command('tau-registration')
        else:
            print()
            tsp('Existing registered image for tau detected; not rerunning.')

        if (not os.path.exists(taustats) or overwrite_pet) and len(TAUINFO):
            with open(taustats, 'w') as f:
                json.dump(TAUINFO, f, indent=4)

        # tau QC images
        suvr_qc = taunamer.get_path('qc-suvr')
        coreg_qc = taunamer.get_path('qc-coregistration')
        petreg_qc = taunamer.get_path('qc-registration')

        print()
        tsp('Generating QC images')

        begin_command('qc-suvr')
        suvr_qc_image(tau_suvr, output=suvr_qc)
        end_command('qc-suvr')

        begin_command('qc-coregistration')
        pet_t1_registration_qc_image(registeredpet=tau_rigid, t1=preskullstrip, output=coreg_qc)
        end_command('qc-coregistration')

        begin_command('qc-registration')
        pet_mni_registration_qc_image(registeredpet=tau_registered, mni=mni_brain, output=petreg_qc)
        end_command('qc-registration')
    else:
        print()
        tsp("No tau image or tau tracer provided; not doing tau processing.")

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

def paths_folder_to_dataframe(paths_folder):
    files = [os.path.join(paths_folder, x) for x in os.listdir(paths_folder) if x.endswith('.json')]
    rows = []
    for file in files:
        with open(file, 'rb') as f:
            data = json.load(f)
            rows.append(data)

    df = pd.DataFrame(rows)
    df = df.sort_values(['Subject', 'Session'])
    return df