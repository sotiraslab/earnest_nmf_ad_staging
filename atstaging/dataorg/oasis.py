
import glob
import os

import nibabel as nib
import pandas as pd

from atstaging.dataorg.utils import (
    get_bids_entities,
    get_shape
)

def _get_bids_json(oasis_image):
    nifti_dir = os.path.dirname(oasis_image)
    acq_dir = os.path.dirname(nifti_dir)
    bids_dir = os.path.join(acq_dir, 'BIDS')
    jsonfile = os.path.basename(oasis_image).removesuffix('.nii.gz') + '.json'
    fullpath = os.path.join(bids_dir, jsonfile)
    return fullpath

def _get_bids_tsv(oasis_image):
    nifti_dir = os.path.dirname(oasis_image)
    acq_dir = os.path.dirname(nifti_dir)
    bids_dir = os.path.join(acq_dir, 'BIDS')
    jsonfile = os.path.basename(oasis_image).removesuffix('.nii.gz') + '.tsv'
    fullpath = os.path.join(bids_dir, jsonfile)
    return fullpath

def _check_for_only_active_window_av45(frames):
    if len(frames) != 4:
        return False
    return [0, 1, 2, 3]

def _check_for_only_active_window_tau(frames):
    if len(frames) != 6:
        return False
    if any(a != b for a, b in zip(frames['Frame_Start'], [0, 300, 600, 900, 1200, 1500])):
        return False
    return [0, 1, 2, 3, 4, 5]

def _check_for_only_active_window(frames, tracer):
    if tracer.lower() in ['ftp', 'flortaucipir', 'av1451', 'av-1451']:
        return _check_for_only_active_window_tau(frames)
    elif tracer.lower() in ['fbp', 'fbr', 'av45', 'av-45', 'florbetapir']:
        return _check_for_only_active_window_av45(frames)
    elif tracer.lower() in ['pib', 'pittsburgh']:
        return False
    else:
        raise ValueError(f'Tracer {tracer} not recognized.')
    
def _find_frame_within_tolerance(target_seconds, frames_seconds, tolerance):
    diff = (frames_seconds - target_seconds).abs()
    acceptable = diff <= tolerance
    if acceptable.sum() == 0:
        raise ValueError(f'No frame within {tolerance}s of {target_seconds}: '
                        f'{list(frames_seconds)}')
    elif acceptable.sum() == 1:
        return acceptable.idxmax()
    else:
        matches = list(frames_seconds.loc[acceptable])
        raise ValueError(f'Multiple acceptable frames within {tolerance}s of {target_seconds}: '
                        f'{matches}')

def get_window_indices(frames, tracer, imgpath='<PathNotProvided>', tolerance=200):
    frames['Frame_End'] = frames['Frame_Start'] + frames['Frame_duration']
    frames['Frame_Start'] = frames['Frame_Start'].round()
    frames['Frame_End'] = frames['Frame_End'].round()
    framestarts = frames['Frame_Start']
    frameends = frames['Frame_End']

    # CASE 1: Many scans have a window starting at 0, with 6 frames (30 minutes)
    # These appear to be images for people who could not sit the whole time in the scanner
    # see the OASIS documentation section on AV1451 acquistion
    # in this case, we just keep all the frames
    potential_indices = _check_for_only_active_window(frames=frames, tracer=tracer)
    if potential_indices:
        print("@NOTE: Detected image with only active window.")
        print(f'@Tracer: {tracer}')
        print(f'@Frame indicies being used: {potential_indices}')
        tmp = list(frames['Frame_Start'].iloc[potential_indices])
        print(f'@Frame frame starts (s): {tmp}')
        indices = potential_indices
        starts = list(framestarts.loc[indices])
        ends = list(frameends.loc[indices])
        return indices, starts, ends

    # CASE 2: Otherwise, try and detect the frames based on the TSV
    start_seconds, end_seconds = oasis_tracer_window(tracer)
    
    try:
        start_index =_find_frame_within_tolerance(
            target_seconds=start_seconds,
            frames_seconds=framestarts,
            tolerance=tolerance)
    except ValueError:
        raise RuntimeError(f'Unable to find starting frame {start_seconds}s for image '
                           f'{imgpath} with tracer {tracer}. Available frame starts are'
                           f'{list(framestarts)}.')

    try:
        end_index = _find_frame_within_tolerance(
            target_seconds=end_seconds,
            frames_seconds=frameends,
            tolerance=tolerance)
    except ValueError:
        raise RuntimeError(f'Unable to find ending frame {end_seconds}s for image '
                           f'{imgpath} with tracer {tracer}. Available frame ends are'
                           f'{list(frameends)}.')

    indices = list(range(start_index, end_index + 1))
    starts = list(framestarts.loc[indices])
    ends = list(frameends.loc[indices])
    return indices, starts, ends

def oasis3_image_list(oasis3_directory, add_shape=False):
    c = 0
    images = []

    print('OASIS3 IMAGE SEARCH ')
    print('~~~~~~~~~~~~~~~~~~~~~~~~')

    for subses in os.listdir(oasis3_directory):
        subses_dir = os.path.join(oasis3_directory, subses)
        if not os.path.isdir(subses_dir):
            continue

        if ('AV45' in subses) or ('PIB' in subses):
            kind = 'amyloid'
        elif 'AV1451' in subses:
            kind = 'tau'
        elif 'MR' in subses:
            kind = 'mri'
        else:
            continue

        img_files = glob.glob('SCANS/*/NIFTI/*.nii.gz', root_dir=subses_dir)
        for file in img_files:
            fullfile = os.path.join(subses_dir, file)

            if (kind == 'mri') and 'T1w' not in file:
                continue

            data = {
                'path': fullfile,
                'json': _get_bids_json(fullfile)
            }
            if kind in ['amyloid', 'tau']:
                data['tsv'] = _get_bids_tsv(fullfile)

            data.update(get_bids_entities(fullfile))
            images.append(data)
        
        c += 1
        if (c % 500) == 0:
            print(f'Visited {c} directories...')

    print('Search complete.')
    df = pd.DataFrame(images)

    print()
    print(f'Found {len(df)} scans.')

    if add_shape:
        print()
        print('Getting image shapes for PET images...')

        global COUNTER
        COUNTER = 0

        def foo(row):
            global COUNTER
            COUNTER += 1

            if COUNTER % 1000 == 0:
                print(f'Row #{COUNTER}...')
            
            if row['modality'] == 'T1w':
                return None

            return get_shape(row['path'])

        df['shape'] = df.apply(foo, axis=1)
        print('Complete.')

    return df

def oasis_table_pull_PET_frames(table, output_directory,
                                path_col='path', tsv_col='tsv', tracer_col='acq',
                                subject_col='sub', ses_col='ses', dry_run=False,
                                overwrite=False):
    record = []
    for i, (_, row) in enumerate(table.iterrows()):
        path = row[path_col]
        tsv = row[tsv_col]
        tracer = row[tracer_col]
        sub = row[subject_col]
        ses = row[ses_col]

        print()
        print('=' * 20)
        print(f'* Image {i+1}: {path}')
        try:
            output = pull_oasis_frames(imgpath=path,
                                       frames_tsv=tsv,
                                       tracer=tracer,
                                       output_directory=output_directory,
                                       dry_run=dry_run,
                                       overwrite=overwrite)
            output[subject_col] = sub
            output[ses_col] = ses
            record.append(output)
            print("* Success")
            print("* Selected frame starts:", output['frame_starts'])
        except Exception as e:
            print('* FAILURE: Error while processing image.')
            print('!!! !!! !!! !!!')
            print(repr(e))
            print('!!! !!! !!! !!!')
        print(f'* Running successes: {len(record)} / {len(table)}')
        print('=' * 20)

    record = pd.DataFrame(record)
    order = [subject_col, ses_col] + [col for col in record.columns if col not in [subject_col, ses_col]]
    record = record[order]

    print()
    print('Process Completed')
    print(f'Starting images: {len(table)}')
    print(f'Successful frame selection: {len(record)}')
    print(f'Subjects with a success: {len(record[subject_col].unique())} /  {len(table[subject_col].unique())}')
    print(f'Subjects with duplicate: {record[subject_col].duplicated().sum()}')
    print(f'Dry run? {dry_run}')

    return record

def oasis_tracer_window(tracer):
    if tracer.lower() in ['fbr', 'fbp', 'av45', 'av-45', 'florbetapir']:
        return 50 * 60, 70 * 60
    if tracer.lower() in ['pib', 'pittsburgh']:
        return 30 * 60, 60 * 60
    if tracer.lower() in ['ftp', 'flortaucipir', 'av1451', 'av-1451']:
        return 80 * 60, 100 * 60
    else:
        raise ValueError(f'Tracer key "{tracer}" is unrecognized; must provide '
                         'FBR, PIB, or FTP.')

def pull_oasis_frames(imgpath, frames_tsv, tracer, output_directory, dry_run=False, overwrite=False):
    nii = nib.load(imgpath)
    orig_shape = nii.shape

    # Non-4D: shouldn't happen but just to be explicit
    # There are 3D images, but turns out most of these also have a usuable 4D image
    if len(orig_shape) != 4:
        raise ValueError(f'Image is not 4D: {imgpath}')
    
    # 4D image: proceed to frame selection
    else:

        # read the frames TSV, can get the frames that should be selected based on tracer
        # this can raise error, if the timing in the frames TSV is not matching what we are looking for
        # or if the frames TSV can't be read
        frames = pd.read_csv(frames_tsv, sep='\t')
        indices, starts, ends = get_window_indices(frames, tracer, imgpath=imgpath)

        # The frames listed in the TSV do not correspond to the shape of the image,
        # which means the indices are probably incorrect
        if orig_shape[3] != len(frames):
            raise ValueError(f'Number of frames in TSV ({len(frames)}) '
                            f'does not equal the frames of the PET image ({orig_shape[3]}).')

    baseimg = os.path.basename(imgpath)
    saveimg = os.path.join(output_directory, baseimg)
    saveimg_exists = os.path.exists(saveimg)

    basetsv = os.path.basename(frames_tsv)
    savetsv = os.path.join(output_directory, basetsv)

    if dry_run:
        selected = nii
        new_shape = list(orig_shape)
        new_shape[3] = len(indices)
        new_shape = tuple(new_shape)
    else:
        data = nii.get_fdata()[:, :, :, indices]
        selected = nib.Nifti1Image(data, affine=nii.affine, header=nii.header)
        new_shape = selected.shape

        if saveimg_exists and not overwrite:
            print(f'> Not overwriting existing image at {saveimg}')
        else:
            if not os.path.isdir(output_directory):
                os.mkdir(output_directory)
            nib.save(selected, saveimg)
            frames.to_csv(savetsv, sep='\t', index=False)

    output = {
        'src_img': imgpath,
        'src_tsv': frames_tsv,
        'src_shape': orig_shape,
        'res_img': saveimg,
        'res_tsv': savetsv,
        'res_shape': new_shape,
        'dry_run': dry_run,
        'frame_starts': starts,
        'frame_ends': ends
    }

    return output
