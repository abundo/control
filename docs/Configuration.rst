Configuration
=============================================================================


BECS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If BECS integration is enabled:

On the abcontrol server, configure the "becs:" section in 
/etc/abcontrol/abcontrol.yaml


Dnsmgr
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If DNS integration is enabled:

On the Abcontrol server, configure the "sync_dns:" section in 
/etc/abcontrol/abcontrol.yaml


Freeradius
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If FreeRadius integration is enabled:

Todo


Icinga
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If Icinga integration is enabled:

On the abcontrol server, configure the "icinga:" section in 
/etc/abcontrol/abcontrol.yaml


Librenms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If Librenms integration is enabled:

On the abcontrol server, configure the "librenms:" section in 
/etc/abcontrol/abcontrol.yaml


named/bind
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Abcontrol does not directly control named. It uses Dnsmgr for this.

Configure named for the forward and reverse domains, then
check Dnsmgr section for how to integrate Dnsmgr and named.


Netbox
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
On the abcontrol server, configure the "netbox:" section in 
/etc/abcontrol/abcontrol.yaml

Start NetBox::

    cd /opt/netbox
    docker-compose up -d

Wait for 2-3 minutes. First startup takes a while.


Using the web GUI, add custom fields needed for abcontrol

===================   =====================================  ==========  ==========  =============  =================== =======  ===============
NAME                  MODELS                                 TYPE        REQUIRED    FILTER LOGIC   DEFAULT             WEIGHT   DESCRIPTION
===================   =====================================  ==========  ==========  =============  =================== =======  ===============
alarm_destination     device,device_type,virtual machine     Selection   no          Loose          notify@example.com  100

alarm_interfaces      device,device_type,virtual machine     Boolean     no          Exact          False               100      If True, librenms will generate alerts for all interfaces

alarm_timeperiod      device,device_type,virtual machine     Selection   no          Loose          sla1                100

backup_oxidzed        device,device_type                     Boolean     no          Exact          true                100
 
becs_oid              device,IP address                      Integer     no          Exact

connection_method     device,device_type,virtual machine     Selection   no          Exact          'ssh'               110      If device is created by BECS synk, this is set automatically

location              device                                 Text        no          Loose                               90      Freetext descibing location of device, use if there is no Site defined

monitor_grafana       device,device_type,virtual machine     Boolean     no          Exact           False              100      If True, Grafana will generate dashboards, only for Huawei

monitor_icinga        device,device_type,virtual machine     Boolean     no          Exact           True               100

monitor_librenms      device,device_type,virtual machine     Boolean     no          Exact           True               100

parents               device,device_type,virtual machine     Text        no          Loose                              100      Comma separated list of parents. If all parents are down no alarms will be generated for this device
===================   =====================================  ==========  ==========  =============  =================== =======  ===============



OpenLDAP, FusionDirectory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
On the OpenLDAP server, configure /opt/openldap/docker-compose.yaml

Start the OpenLDAP server:

    cd /opt/openldap
    docker-compose up -d


On the Abcontrol server, configure the "django: ldap:" section in 
/etc/abcontrol/abcontrol.yaml


Oxidized
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
On the Abcontrol server, configure the "oxidized:" section in 
/etc/abcontrol/abcontrol.yaml

Start oxidized::

    cd /opt/oxidized
    docker-compose up -d


PostgreSQL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
On the Abcontrol server, configure the "django: db:" section in 
/etc/abcontrol/abcontrol.yaml

Change the POSTGRES_PASSWORD in the /opt/postgresql/docker-compose.yaml file
so it matches the above password

Start postgresql::

    cd /opt/postgresql
    docker-compose up -d


RabbitMQ
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In /opt/rabbitmq/docker-compose.yaml adjust::

    RABBITMQ_ERLANG_COOKIE=
    RABBITMQ_DEFAULT_PASSWORD=


Start RabbitMQ::

    docker-compose up -d


Create user and set password and permissions::

    docker-compose exec rabbitmq bash
    rabbitmqctl add_user abcontrol <passwd>
    rabbitmqctl set_permissions -p / abcontrol ".*" ".*" ".*"

    
Activate services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

copy systemd definitions::

    cd /opt/abcontrol
    cp contrib/abcontrol/abcontrol.service /etc/systemd/system
    cp contrib/abcontrol/abcontrol_worker.service /etc/systemd/system

   
enable and activate services::

    systemctl daemon-reload

    systemctl enable abcontrol.service
    systemctl enable abcontrol_worker.service
    
    systemctl start abcontrol.service
    systemctl start abcontrol_worker.service
