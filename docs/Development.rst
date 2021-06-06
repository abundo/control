Development
==============================================================================
Developed using 

* Ubuntu 20.04 64-bit
* python3.6, venv
* Desktop: Windows 10 pro
* Visual Studio Code, with plugins for Python, Remote SSH


Directories and Files
------------------------------------------------------------------------------


===========================================  =============================================================
Directory                                    Description
===========================================  =============================================================
/opt/abcontrol                               home director
/opt/abcontrol/setup.py                      script to help with setup
/opt/abcontrol/app                           django project directory
/opt/abcontrol/app/app                       django project
/opt/abcontrol/app/app/settings.py           django project settings
/opt/abcontrol/app/base                      django app
/opt/abcontrol/app/docs                      django app, shows documentation
/opt/abcontrol/app/lib                       common libraries for the django project
/opt/abcontrol/app/static                    collected static files, served by apache2
/opt/abcontrol/app/tools                     command line tools
/opt/abcontrol/app/templates                 templates for django auth
/opt/abcontrol/contrib                       example config files, systemd services
/opt/abcontrol/docs                          documentation source
/opt/abcontrol/bin                           Python virtual environment files
/opt/abcontrol/include                       Python virtual environment files
/opt/abcontrol/lib                           Python virtual environment files
/opt/abcontrol/lib64                         Python virtual environment files
/opt/abcontrol/share                         Python virtual environment files
===========================================  =============================================================



Django setup
------------------------------------------------------------------------------

Install::

    cd /opt/abcontrol
    source bin/activate
    django-admin startproject app .
    cd app
    django-admin startapp base

    # todo, adminlte
    # todo, adjust settings.py


Development server
------------------------------------------------------------------------------

During development the Django development server can be used. It supports 
dynamic reloading and displays errors directly

CLI::

    cd /opt/abcontrol
    source bin/activate
    cd /opt/abcontrol/app
    ./manage.py runserver 0.0.0.0:5001
