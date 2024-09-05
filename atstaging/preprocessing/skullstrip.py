
from execute import execute

DEEPMRSEG_ENV = 'DeepMRSeg'

def run_deepmrseg_dlicv(inpath, outpath):

    command = [
        'conda',
        'run',
        '--name', DEEPMRSEG_ENV,
        '--live-stream',
        'deepmrseg_apply',
        '--task', 'dlicv',
        '--inImg', inpath,
        '--outImg', outpath
    ]

    execute(command)
