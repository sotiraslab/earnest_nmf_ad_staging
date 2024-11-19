import subprocess

def execute(cmd, shell=False, verbose=True, env=None):
    popen = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             universal_newlines=True,
                             shell=shell,
                             env=env)
    while True:
        line = popen.stdout.readline()
        if not line:
            break
        if verbose:
            print(line.strip())
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)
