# Server
[![Updates](https://pyup.io/repos/github/bp-flugsimulator/server/shield.svg)](https://pyup.io/repos/github/bp-flugsimulator/server/)
[![Build Status](https://travis-ci.org/bp-flugsimulator/server.svg?branch=travis)](https://travis-ci.org/bp-flugsimulator/server)

## Entwicklungsumgebung
Es bietet sich an, die Abhängigkeiten in ein virtualenv zu installieren, sodass sie unabhängig geupdatet werden können:

```
virtualenv3 venv
source venv/bin/activate
pip3 install -r requirements.txt
npm install
python3 manage.py migrate
```

Der Server kann dann über `python3 manage.py runserver` gestartet werden.
