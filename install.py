"""
This script is used to install all requirements listed in requirements.txt from
./libs. If a library is not present, use the flag "--update" to download the
system specific version from the internet into ./libs.

Example
-------
    $python install.py --update
"""

from sys import stderr, argv
from platform import system, architecture
import os
import pip


def install_local(lib_name):
    """
    Installes a library from a local file in ./libs

    Parameters
    ----------
    lib_name: str
        the name of the library that will be installed

    Returns
    -------
    nothing

    Exception
    ---------
    Raises an Exception if the library can't be installed
    from a local file
    """
    if pip.main([
            'install', lib_name, '--no-index', '--find-links',
            'file://' + os.getcwd() + '/libs'
    ]) != 0:
        raise Exception('could not install ' + lib_name + ' from file')


def download(lib_name):
    """
    Downloads a library to ./libs

    Parameters
    ----------
    lib_name: str
        the name of the library that will be downloaded

    Returns
    -------
    nothing

    Exception
    ---------
    Raises an Exception if the library can't be
    downloaded from a local file
    """
    if pip.main(['download', lib_name, '-d', './libs']) != 0:
        raise Exception('could not download ' + lib_name)


def install(lib_name):
    """
    Installes a library from ./libs or downloads it from the
    Internet to ./libs and then install it from there

    Parameters
    ----------
    lib_name: str
        the name of the library that will be installed

    Returns
    -------
    nothing

    Exception
    ---------
    Raises an Exception if the library can't be installed
    from a local file or from the internet
    """

    # try to install library from file
    try:
        install_local(lib_name)
    except Exception as err:
        stderr.write("{}".format(err))
        # try to download library and then install from file
        download(lib_name)
        install_local(lib_name)


if __name__ == "__main__":
    # try to update pip'
    pip.main(['install', '-U', 'pip'])

    # if --update flag is set update all dependencies
    # from requirements.txt in ./libs
    if len(argv) > 1 and argv[1] == '--update':
        with open('requirements.txt') as requirements:
            for library in requirements:
                download(library)

    # install wheel
    install('wheel')

    # on windows install pypiwin32
    if system() == 'Windows':
        install('pypiwin32')
    elif system() == 'Linux':
        if architecture()[0] != '64bit':
            stderr.write(architecture()[0] +
                         ' is not officially supported but may work\n')
    else:
        stderr.write(system() + ' is not officially supported but may work\n')

    # install all other dependencies
    with open('requirements.txt') as requirements:
        for library in requirements:
            install_local(library)

