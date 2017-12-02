import pip
import os
from platform import system, architecture
from sys import stderr, version_info, argv


def install_local(lib_name):
    """ 
    Installes a libary from a local file in ./libs
    
    Parameters 
    ----------
    lib_name: str
        the name of the libary that will be installed

    Returns
    -------
    nothing

    Exception
    ---------
    Raises an Exception if the libary can't be installed
    from a local file
    """
    if pip.main([
        'install', lib_name, '--no-index', '--find-links',
        'file://' + os.getcwd() + '/libs'
    ]) != 0:
        raise Exception('could not install ' + lib_name + ' from file')


def download(lib_name):
    """ 
    Downloads a libary to ./libs
    
    Parameters 
    ----------
    lib_name: str
        the name of the libary that will be downloaded

    Returns
    -------
    nothing

    Exception
    ---------
    Raises an Exception if the libary can't be 
    downloaded from a local file
    """
    if pip.main(['download', lib_name, '-d', './libs']) != 0:
        raise Exception('could not download ' + lib_name)


def install(lib_name):
    """ 
    Installes a libary from ./libs or downloads it from the 
    Internet to ./libs and then install it from there

    Parameters 
    ----------
    lib_name: str
        the name of the libary that will be installed

    Returns
    -------
    nothing

    Exception
    ---------
    Raises an Exception if the libary can't be installed
    from a local file or from the internet
    """

    # try to install libary from file
    try:
        install_local(lib_name)
    except Exception as err:
        stderr.write("{}".format(err))
        # try to download libary and then install from file
        download(lib_name)
        install_local(lib_name)


if __name__ == "__main__":
    # try to update pip'
    pip.main(['install', '-U', 'pip'])
  
    # if --update flage is set update all dependecies 
    # from requirements.txt in ./libs
    if len(argv) > 1 and argv[1] == '--update':
        with open('requirements.txt') as requirements:
            for libary in requirements:
                download(libary)
        
    # install wheel
    install('wheel')

    # on windows install pypiwin32
    if system() == 'Windows':
        install('pypiwin32')
    elif system() == 'Linux':
        pass
    else:
        stderr.write(system() + ' is not officaly supported but may work\n')

    # install all other dependecies
    with open('requirements.txt') as requirements:
        for libary in requirements:
            install_local(libary)
