Development
==============================================================================
Developed using 

* Server: Ubuntu 18.04 64-bit
* Desktop: Windows 10 pro
* Visual Studio Code, with plugins for Python, Remote SSH
* python3.6
* venv


Django development server
------------------------------------------------------------------------------

    cd /opt/abcontrol
    source bin/activate
    ./manage.py runserver 0.0.0.0:5001


Files
------------------------------------------------------------------------------


============================    ===========================
Directory                       Description
============================    ===========================
/opt/abcontrol                  home director
/opt/abcontrol/app              django project
/opt/abcontrol/app/base         django app
/opt/abcontrol/app/tools        command line tools
/opt/abcontrol/app/lib          common libraries
/opt/abcontrol/app/templates    templates for django auth
/opt/abcontrol/docs             documentation
============================    ===========================



Initial django setup
------------------------------------------------------------------------------

    cd /opt/abcontrol
    source bin/activate
    django-admin startproject app .
    cd app
    django-admin startapp app

    # todo, adminlte
    # todo, adjust settings.py

# Development

Developed using 
- Ubuntu 20.04
- Visual Studio Code, with plugins for Python
- python3.6


## Run gunicorn development server

cd /opt/abcontrol
source bin/activate
./manage.py runserver 0.0.0.0:5000


## Files

/opt/abcontrol           home director
/opt/abcontrol/app       django application
/opt/abcontrol/script    command line tools


