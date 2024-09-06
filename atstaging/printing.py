
import datetime as dt

def begin_command(command):
    print()
    print(f'---------- BEGIN: {command} ----------')

def end_command(command):
    print(f'----------  END : {command} ----------')
    print()

def timestamp_print(*args, **kwargs):
    t = str(dt.datetime.now())
    print(f'[ {t} ] ', *args, **kwargs)
