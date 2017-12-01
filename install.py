import pip
import os
from platform import system, architecture
from sys import stderr, version_info


def install_local(lib_name):
    return pip.main([
        'install', lib_name, '--no-index', '--find-links',
        'file://' + os.getcwd() + '/libs'
    ])


def download(lib_name):
    return pip.main(['download', lib_name, '-d', './libs'])


def install(lib_name):
    # try to install libary from file
    if install_local(lib_name) != 0:
        stderr.write('could not install ' + lib_name + ' from file\n:')

        # try to download libary and then install from file
        if download(lib_name) == 0:
            install_local(lib_name)
        else:
            stderr.write('could not download and then install ' + lib_name +
                         ' from file:\n')


if __name__ == "__main__":
    # try to update pip'
    pip.main(['install', '-U', 'pip'])

    # try to download all normal dependecies
    with open('requirements.txt') as requirements:
        for libary in requirements:
            if download(libary) != 0:
                break

    # on windows install wheel variant of twisted
    if system() == 'Windows':
        # update wheel
        install('wheel')

        # install pypiwin32
        install('pypiwin32')

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

        install_local(twisted)

    elif system() == 'Linux':
        pass
    else:
        raise Exception(system() + ' is not supported\n')

    # install all other dependecies
    with open('requirements.txt') as requirements:
        for libary in requirements:
            install(libary)
