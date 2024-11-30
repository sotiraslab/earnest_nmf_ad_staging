

import os

from atstaging.config import get, get_slurm_setup_script
from atstaging.preprocessing.execute import execute

BATCH_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), 'atproc_batch.sh')

def at_mri_pipeline_SLURM(t1_img, amyloid_img, amyloid_tracer, tau_img, tau_tracer,
                          subject, session, output_directory):
    tag = f"sub-{subject}_ses-{session}"
    setup_script = get_slurm_setup_script()
    
    nodes = get('slurm', 'nodes')
    ntasks = get('slurm', 'ntasks')
    mem = get('slurm', 'mem')
    time = get('slurm', 'time')
    account = get('slurm', 'account')
    partition = get('slurm', 'partition')

    if not os.path.isdir(output_directory):
        os.mkdir(output_directory)

    log_dir = os.path.join(output_directory, 'logs')
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    log_file = os.path.join(log_dir, f"{tag}.slurmlog")

    # required args
    command = [
        "sbatch",
        "-J", tag,
        f"--output={log_file}",
        "--parsable",
        f'--mem={mem}',
        '-n', ntasks,
        '-N', nodes,
        '-t', time,
        f'--account={account}',
        f'--partition={partition}',
        BATCH_SCRIPT_PATH,
        '-S', subject,
        '-s', session,
        '-O', output_directory,
        '-I', t1_img,
        '-U', setup_script
    ]

    # optional arguments
    if amyloid_img is not None:
        command += ['-A', amyloid_img]
    if amyloid_tracer is not None:
        command += ['-a', amyloid_tracer]
    if tau_img is not None:
        command += ['-T', tau_img]
    if tau_tracer is not None:
        command += ['-t', tau_tracer]
    
    print()
    print('SBATCH call:')
    print(' '.join(command))

    execute(command)