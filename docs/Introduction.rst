Introduction
==============================================================================
Abcontrol is a suite of components that integrates

* NetBox
* RabbitMQ
* OpenLDAP


It can optionally integrate with

* BECS
* DNS
* Freeradius
* Icinga
* Librenms
* Oxidized


Abcontrol Homepage: https://github.com/abundo/Abcontrol

Abcontrol Documentation: https://readthedocs.org/projects/Abcontrol/

The documentation is also available when the django application is running.


Applications
-----------------------------------------------------------------------------

Netbox
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature: Required

Netbox is a major component of Abcontrol. It contains all devices and
device IP addresses that Abcontrol manages.

Netbox homepage: https://github.com/netbox-community/netbox


OpenLDAP
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature: Required

OpenLDAP is an opensource LDAP server.

Abcontrol uses LDAP for access control.

Other applications can be configured to use LDAP, centralizing the authentification
and authorizaion.

OpenLDAP home: https://openldap.org/


PostgreSQL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature: Required

PostgreSQL is a relational SQL database.

Homepage: https://www.postgresql.org/


RabbitMQ
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature: Required

RabbitMQ is a message bus. It is used for log messages and communication
between different procesesses and servers.

RabbitMQ Homepage: https://www.rabbitmq.com/



Optional applications
-----------------------------------------------------------------------------

BECS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature: Optional

BECS is a BSS/OSS application.

Abcontrol does not manage BECS, devices in BECS can be syncronized with NetBox.
BECS integration is using the BECS EAPI.

BECS homepage: https://pfsw.com/becs/


DNS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature: Required for some components, recommended

Abcontrol can keep DNS up-to-date with forward and reverse entries for all
devices in NetBox.

Abcontrol can also parse all device configuration files and create reverse DNS 
entries for all their interfaces. This makes for example a traceroute more useful,
with names instead of IP addresses, describing the interfaces traversed.

Interface with the DNS software is done using the Dnsmgr program.

Dnsmgr homepage: https://github.com/abundo/dnsmgr


FreeRADIUS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature: Optional

FreeRADIUS is not directly part of Abcontrol. It is configured to use OpenLDAP
as the database backend. Adding a user to LDAP, with the correct group enables
the user in FreeRADIUS.

FreeRADIUS homepage: https://freeradius.org/


FusionDirectory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature: Optional

FusionDirectory is a web gui to easy administer users and groups in the LDAP server.

FusionDirectory homepage : https://www.fusiondirectory.org/en/


Icinga
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature: Optional

Abcontrol can syncronize devices in Netbox with Icinga.

Icinga homepage: https://icinga.com/


Librenms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature: Optional

Abcontrol can synchonize devices in Netbox with librenms. parent relationships
are also synchronzed. The LibreNMS API is used for all operations except 
adjusting parents due to the API missing some functionality. 
Parent adjustment is done by directly accessing the mariadb database.

Librenms homepage: https://www.librenms.org/


Oxidized
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature: Optional

Oxidized is an application that can do configuration backup on routers and switches.

Abcontrol can synchronize devices in Netbox with oxidized.

Oxidized homepage: https://github.com/ytti/oxidized


Dependencies
-----------------------------------------------------------------------------

ablib
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature: Required

ablib is a collection of support libraries used by Abcontrol

ablib Homepage: https://github.com/abundo/ablib


Apache2
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature: Optional, other web servers can be used

Apache2 is used on Abcontrol to show the main Web interface. It is also
used to proxy HTTPs to HTTP, handling X.509 certificates.

Apache2 homepage: https://httpd.apache.org/


Dnsmgr
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature: Optional, required if DNS integration  is used

Dnmsgr is a tool to simplify the configuration of a named/bind server.

Dnsmgr homepage: https://github.com/abundo/dnsmgr
