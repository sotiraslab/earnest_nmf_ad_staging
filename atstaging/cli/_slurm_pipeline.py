

import os

from atstaging.config import get, get_slurm_setup_script, set_config_by_name, set_config_automatic
from atstaging.preprocessing.execute import execute

BATCH_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), 'atproc_batch.sh')

def at_mri_pipeline_SLURM(subject, session, t1_img, output_directory, amyloid_img=None, amyloid_tracer=None,
                          tau_img=None, tau_tracer=None, config=None):
    
    if config is not None:
        set_config_by_name(config)
    else:
        set_config_automatic()

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
    if config is not None:
        command += ['-C', config]

    print()
    print('SBATCH call:')
    print(' '.join(command))

    execute(command)