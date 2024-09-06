
import datetime as dt

from colorama import Fore, Style

def begin_command(command):
    print()
    print(Fore.RED + f'---------- BEGIN: {command} ----------' + Style.RESET_ALL)

def end_command(command):
    print(Fore.RED + f'----------  END : {command} ----------' + Style.RESET_ALL)
    print()

def timestamp_print(*args, **kwargs):
    t = str(dt.datetime.now())
    print(Fore.YELLOW + f'[ {t} ] ' + Style.RESET_ALL, *args, **kwargs)
