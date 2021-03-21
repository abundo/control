# abcontrol installation

Developed, tested and used in production on Ubuntu 18.04


# Installation and setup

## Install dependies

### postgresql, as docker

Todo

### rabbitmq, as docker

Todo

Create user and set permission

    rabbitmqctl add_user abcontrol <passwd>
    rabbitmqctl set_permissions -p / abcontrol ".*' ".*" ".*"


## 

    sudo apt-get install python3-venv

    cd /opt
    python3 -m venv abcontrol
    cd abconttrol
    source bin/activate

    cd /opt
    git clone <todo> https://github.com/xxxx

    cd /opt/abottols
    pip3 install -r requirements.txt


    
#    django-admin startproject app .
#    cd app
#    django-admin startapp app
#    # todo, adminlte


DNSMGR



## Konfiguration netbox

Add webhook, so changes will propagate faster


# Deployment

All functions can be run on the same server, or distributed using 


## Create directories and adjust permissions

    sudo mkdir /etc/abcontrol
    sudo chown anders /etc/dnsmgr
    cp /opt/dnsmgr/records-example.com records

## Activate services

copy systemd definitions

activate services


## Test

Todo


# Docker

Todo


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

