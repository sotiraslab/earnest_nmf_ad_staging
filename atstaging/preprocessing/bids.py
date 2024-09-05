
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

    def delete_files(self, keys):
        for key in keys:
            path = self.get_path(key)
            if not os.path.isfile(path):
                continue
            os.remove(path)

    def make_img_dir(self):
        Path(self.bids_img_dir).mkdir(parents=True, exist_ok=True)
    
class MRIOutputNamer(BIDSOutputNamer):
    
    def __init__(self, subject, session, modality=None, directory=None):
        super().__init__(subject=subject, session=session, modality=modality, directory=directory)
        
        self.namestore = {
            'dcm2niix': 'sub-{SUBJECT}_ses-{SESSION}_space-orig_desc-original_T1w.nii.gz',
            'preskullstrip': 'sub-{SUBJECT}_ses-{SESSION}_space-orig_desc-preskullstrip_T1w.nii.gz',
            'brain': 'sub-{SUBJECT}_ses-{SESSION}_space-orig_desc-brain_T1w.nii.gz',
            'brainmask': 'sub-{SUBJECT}_ses-{SESSION}_space-orig_desc-brainmask_T1w.nii.gz',
        }
