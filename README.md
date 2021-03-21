# abcontrol

## Overview

A collection of applications, with a web gui, that connects
- netbox
- becs
- dns
- icinga
- librenms
- oxidized


abcontrol major components consists of
- python venv, to simplify dependency management
- apache2 as web frontend
  - manages TLS
  - proxies to gunicorn WSGI server
- django with gunicorn as web framework/ORM
- rabbitmq message bus
- postgresql database
- a msg_handler, that runs background/long running tasks



## Documentation

The documentation is
- Local in the web gui
- Online at "Read the Docs" https://readthedocs.org/
  todo: add link to online doc

