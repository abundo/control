Development
==============================================================================
Developed using 

* Ubuntu server 20.04 64-bit
* python3.8, venv
* Desktop: Windows 10 pro
* Visual Studio Code, with plugins for Python, Remote SSH


Directories and Files
------------------------------------------------------------------------------


===========================================  =============================================================
Directory                                    Description
===========================================  =============================================================
/opt/factum                                  home director
/opt/factum/setup.py                         script to help with setup (WIP)
/opt/factum/app                              django project directory
/opt/factum/app/app                          django project
/opt/factum/app/app/settings.py              django project settings
/opt/factum/app/base                         django app, base
/opt/factum/app/base                         django app, device
/opt/factum/app/docs                         django app, shows documentation
/opt/factum/app/lib                          common libraries for the django project
/opt/factum/app/static                       collected static files, served by apache2
/opt/factum/app/tools                        command line tools
/opt/factum/app/templates                    templates for django auth
/opt/factum/contrib                          example config files, systemd services
/opt/factum/docs                             documentation source
/opt/factum/venv                             Python virtual environment files
===========================================  =============================================================



Django setup
------------------------------------------------------------------------------

Install::


    cd /opt/factum
    python3 -m venv venv
    source venv/bin/activate
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

    cd /opt/factum
    source venv/bin/activate
    cd /opt/factum/app
    ./manage.py runserver 0.0.0.0:5001
