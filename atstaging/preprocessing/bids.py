
import os
from pathlib import Path

class BIDSOutputNamer:

    def __init__(self, subject, session, modality='', directory=''):
        self.subject = subject
        self.session = session
        self.modality = modality
        self.directory = directory

        self.namestore = {}

    @property
    def bids_subject(self):
        return f'sub-{self.subject}'

    @property
    def bids_session(self):
        return f'ses-{self.session}'

    @property
    def bids_img_dir(self):
        return os.path.join(self.directory, self.bids_subject, self.bids_session, self.modality)

    def get_name(self, key):

        try:
            pattern = self.namestore[key]
        except KeyError:
            raise KeyError(f'Key "{key}" not found in the name store.')

        name = pattern.format(SUBJECT=self.subject, SESSION=self.session)
        return name

    def get_path(self, key):
        name = self.get_name(key)
        path = os.path.join(self.bids_img_dir, name)
        return path

    def keep_only(self, keys, verbose=False):
        '''Keeps only the files corresponding to the specified keys,
        and deletes other ones that are in the namestore.  Used for
        cleaning up unwanted files at the end of preprocessing.'''
        if isinstance(keys, str):
            keys = list(keys)
        allkeys = set(self.namestore.keys())
        keepkeys = set(keys)
        removekeys = allkeys - keepkeys
        self.delete_files(removekeys, verbose=verbose)

    def delete_files(self, keys, verbose=False):
        vprint = print if verbose else lambda *args, **kwargs: None

        vprint()
        vprint('Deleting files...')
        vprint('-----------------')
        for key in keys:
            vprint(f'* {key}', end='')
            path = self.get_path(key)
            if not os.path.isfile(path):
                vprint(' --> Not found.')
                continue
            os.remove(path)
            vprint(' --> Removed.')

    def make_img_dir(self):
        Path(self.bids_img_dir).mkdir(parents=True, exist_ok=True)

class ATPreprocMRINamer(BIDSOutputNamer):

    def __init__(self, subject, session, modality='anat', directory=None):
        super().__init__(subject=subject, session=session, modality=modality, directory=directory)

        self.namestore = {
            'dcm2niix': 'sub-{SUBJECT}_ses-{SESSION}_space-orig_desc-original_T1w.nii.gz',
            'preskullstrip': 'sub-{SUBJECT}_ses-{SESSION}_space-orig_desc-preskullstrip_T1w.nii.gz',
            'brain': 'sub-{SUBJECT}_ses-{SESSION}_space-orig_desc-brain_T1w.nii.gz',
            'brainmask': 'sub-{SUBJECT}_ses-{SESSION}_space-orig_desc-brainmask_T1w.nii.gz',
            'affine': 'sub-{SUBJECT}_ses-{SESSION}_from-orig_to-MNI152NLin6ASym_desc-affine_transform.mat',
            'warp': 'sub-{SUBJECT}_ses-{SESSION}_from-orig_to-MNI152NLin6ASym_desc-nonlinear_warpfield.nii.gz',
            'jacobian': 'sub-{SUBJECT}_ses-{SESSION}_from-orig_to-MNI152NLin6ASym_jacobian.nii.gz',
            'fullwarp': 'sub-{SUBJECT}_ses-{SESSION}_from-orig_to-MNI152NLin6ASym_desc-fullwarp_warpfield.nii.gz',
            'registered': 'sub-{SUBJECT}_ses-{SESSION}_space-MNI152NLin6ASym_desc-nonlinear_T1w.nii.gz',
            'muse': 'sub-{SUBJECT}_ses-{SESSION}_space-orig_desc-muse_seg.nii.gz',
            'volumes': 'sub-{SUBJECT}_ses-{SESSION}_desc-musevolumes_table.csv',
            'petreference': 'sub-{SUBJECT}_ses-{SESSION}_space-orig_desc-petreference_mask.nii.gz',
            'qc-skullstrip': 'sub-{SUBJECT}_ses-{SESSION}_space-orig_desc-brainmask_qc.png',
            'qc-checkerboard': 'sub-{SUBJECT}_ses-{SESSION}_space-MNI152NLin6ASym_desc-checkerboard_qc.png'
        }

class ATPreprocPETNamer(BIDSOutputNamer):

    def __init__(self, subject, session, tracer, modality='pet', directory=None):
        super().__init__(subject=subject, session=session, modality=modality, directory=directory)
        self.tracer = tracer

        self.namestore = {
            'nifti': 'sub-{SUBJECT}_ses-{SESSION}_trc-{TRACER}_space-pet_desc-nifti_pet.nii.gz',
            'realigned': 'sub-{SUBJECT}_ses-{SESSION}_trc-{TRACER}_space-pet_desc-realigned_pet.nii.gz',
            'averaged': 'sub-{SUBJECT}_ses-{SESSION}_trc-{TRACER}_space-pet_desc-averaged_pet.nii.gz',
            'smoothed': 'sub-{SUBJECT}_ses-{SESSION}_trc-{TRACER}_space-pet_desc-smoothed10mm_pet.nii.gz',
            'registered': 'sub-{SUBJECT}_ses-{SESSION}_trc-{TRACER}_space-MNI152NLin6ASym_desc-registered_pet.nii.gz',
            'rigid': 'sub-{SUBJECT}_ses-{SESSION}_trc-{TRACER}_space-t1_desc-rigid_pet.nii.gz',
            'origsuvr': 'sub-{SUBJECT}_ses-{SESSION}_trc-{TRACER}_space-pet_desc-suvr_pet.nii.gz',
            'fullwarp': 'sub-{SUBJECT}_ses-{SESSION}_trc-{TRACER}_from-pet_to-MNI152NLin6ASym_desc-fullwarp_warpfield.nii.gz',
            'brain': 'sub-{SUBJECT}_ses-{SESSION}_trc-{TRACER}_space-pet_desc-brain_pet.nii.gz',
            'musestats': 'sub-{SUBJECT}_ses-{SESSION}_trc-{TRACER}_space-pet_desc-musestats_table.csv',
            'petstats': 'sub-{SUBJECT}_ses-{SESSION}_trc-{TRACER}_desc-petstats_table.json',
        }

    def get_name(self, key):

        try:
            pattern = self.namestore[key]
        except KeyError:
            raise KeyError(f'Key "{key}" not found in the name store.')

        name = pattern.format(SUBJECT=self.subject, SESSION=self.session, TRACER=self.tracer)
        return name
