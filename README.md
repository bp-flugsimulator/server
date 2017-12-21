# Server
[![Updates](https://pyup.io/repos/github/bp-flugsimulator/server/shield.svg)](https://pyup.io/repos/github/bp-flugsimulator/server/)
[![Build Status](https://travis-ci.org/bp-flugsimulator/server.svg?branch=travis)](https://travis-ci.org/bp-flugsimulator/server)
[![Updates](https://ci.appveyor.com/api/projects/status/32r7s2skrgm9ubva)](https://ci.appveyor.com/project/GreenM0nst3r/server/branch/master)
## Entwicklungsumgebung
Es bietet sich an, die Abhängigkeiten in ein virtualenv zu installieren, sodass sie unabhängig geupdatet werden können:

```
virtualenv3 venv
source venv/bin/activate
python3 install.py
npm install
python3 manage.py migrate
```

Der Server kann dann über `python3 manage.py runserver` gestartet werden.

## CSS (SASS)

Um das Aussehen zu ändern müssen zuerst die Abhängigkeiten installiert werden.

```sh
pip install -r requirements_css.txt
```

Danach kann die Datei in `static/css/custom.scss` bearbeitet werden.
Um das ganze auf dem Produktionserver laufen zu lassen muss man die Dateien
compilen.

```sh
python manage.py compilescss
```
