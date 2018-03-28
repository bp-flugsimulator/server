# Server
[![Updates](https://pyup.io/repos/github/bp-flugsimulator/server/shield.svg)](https://pyup.io/repos/github/bp-flugsimulator/server/)
[![Build Status](https://travis-ci.org/bp-flugsimulator/server.svg?branch=travis)](https://travis-ci.org/bp-flugsimulator/server)
[![Updates](https://ci.appveyor.com/api/projects/status/32r7s2skrgm9ubva)](https://ci.appveyor.com/project/GreenM0nst3r/server/branch/master)

## Installation
1. Install python 3.4 or newer and git
1. Clone the Github repository
    ```sh
    git clone https://github.com/bp-flugsimulator/server.git
    ```
1. Run the deploy command, which will setup the server and output a zip file with all relevant files:
    ```sh
    cd server
    python manage.py deploy
    ```
1. Unzip the resulting file to the desired installation directory (the cloned repository can be deleted at this point):
    * On Linux:
    ```sh
    mkdir /home/fsim-user/fsim-master
    unzip ../server.zip /home/fsim-user/fsim-master/
    ```
    * On Windows use the Windows Explorer.

## Entwicklungsumgebung (intern)
Es bietet sich an, die Abhängigkeiten in ein virtualenv zu installieren, sodass sie unabhängig geupdatet werden können:

```
virtualenv3 venv
source venv/bin/activate
python3 install.py
npm install
python3 manage.py migrate
```

Der Server kann dann über `python3 manage.py runserver` gestartet werden.
