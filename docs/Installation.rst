Installation
=============================================================================
Developed, tested and used in production on Ubuntu 18.04 and 20.04

Uses:

* Python venv, to simplify dependency management
* Django as web framework and ORM, with gunicorn as WSGI server
* Apache2 as external web frontend
  * Manages TLS
  * proxies to gunicorn WSGI server
* RabbitMQ as message bus
* PostgreSQL as database
* A background_worker, which runs background/long running tasks


There are two ways to install factum

- using setup.py script  (WIP)
- manual


Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All factum supported services can be run on the same server, or distributed
on multiple servers, using rabbitmq for communication.

If the functionality is distributed on more than one server, install factum
on all servers, then adjust the /etc/factum/factum.yaml

The "roles:" section controls what functions are handled on each server.




**Example, one server**


server::

    # Globally enabled roles
    enabled_roles:
        factum: true
        rabbitmq: true

        becs_sync: false
        dns: true
        freeradius: false
        icinga: false
        openldap: true
        librenms: true
        netbox: true
        oxidized: true

    # enabled roles on this server
    roles:
        factum: true
        dns: true
        icinga: true
        ldap: true
        librenms: true
        oxidized: true
        netbox: true
        rabbitmq: true
        becs_sync: true


**Example, three servers**

server1::

    # Globally enabled roles
    enabled_roles:
        factum: true
        rabbitmq: true

        becs_sync: false
        dns: true
        freeradius: false
        icinga: false
        openldap: true
        librenms: true
        netbox: true
        oxidized: true

    # enabled roles on this server
    roles:
        factum: true
        dns: true
        icinga: false
        ldap: true
        librenms: false
        oxidized: false
        netbox: true
        rabbitmq: true
        becs_sync: true

server2::

    # enabled roles on this server
    roles:
        factum: false
        dns: false
        icinga: true
        ldap: false
        librenms: false
        oxidized: false
        netbox: false
        rabbitmq: false
        becs_sync: false

server3::

    # enabled roles on this server
    roles:
        factum: false
        dns: false
        icinga: false
        ldap: false
        librenms: true
        oxidized: true
        netbox: false
        rabbitmq: false
        becs_sync: false



Installation - Script
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

NOTE: The script is Work In Progress, only use in lab setups

Most of the installation/configuration is done by the setup.py script. 
The script must be  executed multiple times to do a proper installation, 
optionally on each server in the installation.


factum
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
factum must be installed in /opt/factum

Install::

    cd /opt
    git clone https://github.com/abundo/factum.git


setup.py
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Most of the installation task can be done by the setup.py script.

The first time setup.py runs it checks if there is a configuration file in 
/etc/factum/factum.py

If not, it creates the directory /etc/factum and copies a template file 
into this directory and stops.

NOTE:
If you want to run factum and all it's supported applications on more than
one server, adjust the "enabled_roles:" and "roles:" section according to 
Deployment above before running the setup.py script again.

The "enabled_roles:" indicites on the main factum server what roles is active.

The "roles:" section indicates on each server what software to install and configure.

In a multiple-server setup, factum needs to be installed and configured on
each server.

run::

    cd /opt/factum
    ./setup.py



Installation - Manual
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Depencies
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Install::

    # dependencies to build python-ldap
    apt install libsasl2-dev libldap2-dev libssl-dev

    # Python virtual environment, Access control
    apt install python3-pip python3-venv acl

    # Docker
    apt install docker docker-compose


ablib
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Install::

    cd /opt
    git clone https://github.com/abundo/ablib.git


BECS
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
BECS EAPI is SOAP/XML based. There is no high-performance SOAP/XML library 
for Python, therefore a small PHP script is used for the communication with
BECS. This PHP script generates an JSON file that is used by the sync script.

Install::

    apt install php-soap php-yaml


Verify that the php-soap and php-yaml module is activated::

    todo


Dnsmgr
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Install::

    cd /opt
    git clone https://github.com/abundo/dnsmgr.git


Copy configuration template::

    mkdir /etc/dnsmgr
    cd /opt/dnsmgr/
    cp dnsmgr-example.conf /etc/dnsmgr/dnsmgr.conf
    pip3 install orderedattrdict
    # pip3 install -r requirements.txt


bind/named
.............................................................................

Install, Ubuntu 20.04::

    apt install named


Install, Ubuntu 18.04::

    apt install bind9


OpenLDAP, as a docker instance
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Docker homepage: https://github.com/tiredofit/docker-openldap-fusiondirectory

Install::

    mkdir -p /opt/openldap
    cp /opt/factum/contrib/openldap/docker-compose.yaml .


Postgresql, as a docker instance
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Docker homepage: todo

Create directory and copy compose file::

    mkdir /opt/postgresql
    cp /opt/factum/contrib/postgresql/docker-compose.yaml .



Rabbitmq, as a docker instance
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
Docker homepage: todo

Create directory and copy file::

    mkdir /opt/rabbitmq
    cp /opt/factum/contrib/rabbitmq/docker-compose.yaml /opt/rabbitmq



NetBox, as a docker instance
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Docker homepage: https://github.com/netbox-community/netbox-docker

Use the netbox-docker image::

    cd /opt
    git clone https://github.com/netbox-community/netbox-docker.git

Start netbox::

    cd /opt/netbox
    docker-compose up -d



Librenms, as docker instance
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Docker homepage: todo

Install:

    mkdir /opt/librenms

Create docker-compose.yaml::

    cp contrib/librenmr/docker-compose.yaml /opt/librenms


Icinga, as docker instance
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Icinga homepage: https://icinga.com/

Install::

    todo


factum
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

create python virtual environment::

    cd /opt/factum
    python3 -m venv venv


Activate python virtual environment and install dependencies::

    cd /opt/factum
    source venv/bin/activate
    pip3 install -r requirements.txt


Create log directory::

    mkdir /var/log/factum
    setfacl -R -m u:www-data:rwX /var/log/factum
    setfacl -d -R -m u:www-data:rwX /var/log/factum


Create work directory::

    mkdir /var/lib/factum
    setfacl -R -m u:www-data:rwX /var/lib/factum
    setfacl -d -R -m u:www-data:rwX /var/lib/factum


Rebuild documentation::

    cd /opt/factum/docs
    make html


Create link to factum cli, for easy access::

    ln -s /opt/factum/app/tools/factum/factum.sh /usr/bin/factum
