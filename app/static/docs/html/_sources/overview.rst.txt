Overview
=====================================

A suite of integration components, that connects

* netbox
* becs
* dns
* icinga
* librenms
* oxidized


Uses

- Python venv, to simplify dependency management
- Django as web framework and ORM
- Apache2 as external web frontend
  - Manages TLS
  - proxies to gunicorn
- Rabbitmq as message bus
- Postgresql as database
- A background_worker, that runs background/long running tasks

Developed, tested and used in production on Ubuntu 18.04

Documentation is stored at Read the Docs. It is also available when the django application
is running.
