import os
import sys
import platform
import subprocess
import shutil

if platform.machine() == 'AMD64':
    ARCH = '64'
    SYSDIR = 'C:\Program Files (x86)'
    SYSDIR64 = 'C:\Program Files'
else:
    ARCH = '32'
    SYSDIR = 'C:\Program Files'
    SYSDIR64 = None

DIR = os.path.dirname(sys.argv[0])
ACTION = sys.argv[2]


def check_files(files):
    err_f = [f for f in files if not os.path.isfile(os.path.join('', DIR, f))]

    if len(err_f):
        print("Отсутствуют файлы!!")
        for e in err_f:
            print(e)
        sys.exit()


def run_exe(*command):
    p = subprocess.call(list(command),
        shell=False, stdout=subprocess.PIPE, stderr=sys.stdout)
    return p


def run_msi(*command):
    p = subprocess.call(['msiexec', '/qn'] + list(command),
        shell=False, stdout=subprocess.PIPE)
    return p


def run_cmd(*command):
    p = subprocess.call(list(command),
        shell=False, stdout=subprocess.PIPE)
    return p


def copy(src, dst):
    shutil.copy(os.path.join('', DIR, src), dst)