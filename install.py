import pip
import os
from platform import system, architecture
from sys import stderr, version_info
from termcolor import colored


def install_local(lib_name):
    return pip.main([
        'install', lib_name, '--no-index', '--find-links',
        'file://' + os.getcwd() + '/libs'
    ])


def install(lib_name):
    # try to install libary from file
    if install_local(lib_name) != 0:
        stderr.write(
            colored('could not install ' + lib_name + ' from file\n:'), 'red')

        # try to download libary and then install from file
        if pip.main(['download', lib_name, '-d', './libs']) == 0:
            install_local(lib_name)
        else:
            stderr.write(
                colored('could not download and then install ' + lib_name +
                        ' from file:\n', 'red'))


# try to update pip'
pip.main(['install', '-U', 'pip'])

# on windows install wheel variant of twisted
if system() == 'Windows':
    # update wheel
    pip.main(['install', '-U', 'wheel'])

    # install pypiwin32
    pip.main(['install', 'pypiwin32'])

    # install twisted from static file
    twisted = 'Twisted-17.9.0-'
    if version_info.minor == 6:
        twisted += 'cp36-cp36m'
    elif version_info.minor == 5:
        twisted += 'cp35-cp35m'
    elif version_info.minor == 4:
        twisted += 'cp34-cp34m'
    else:
        raise Exception('This Software only supports Python 3.4 - 3.6 \n')

    if architecture()[0] == '64bit':
        twisted += '-win_amd64.whl'
    elif architecture()[0] == '32bit':
        twisted += '-win32.whl'
    else:
        raise Exception('This Software only supports 32 and 64 bit OS\n')

    pip.main(['install', './libs/' + twisted])

elif system() == 'Linux':
    pass
else:
    raise Exception(system() + ' is not supported\n')

# install all other dependecies
with open('requirements.txt') as requirements:
    for libary in requirements:
        install(libary)
