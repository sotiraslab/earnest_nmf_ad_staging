
from execute import execute

from atstaging.config import get

def run_deepmrseg_dlicv(inpath, outpath):

    command = [
        'conda',
        'run',
        '--name', get('deepmrseg_env'),
        '--live-stream',
        'deepmrseg_apply',
        '--task', 'dlicv',
        '--inImg', inpath,
        '--outImg', outpath
    ]

    execute(command)
