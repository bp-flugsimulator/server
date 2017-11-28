import pip
import os
from platform import system, architecture
from sys import stderr, version_info

# update pip
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
pip.main(['install', '-r', 'requirements.txt'])
