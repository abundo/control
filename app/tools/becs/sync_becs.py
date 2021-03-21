#!/usr/bin/env python3
"""
Get all devices (element-attach) of type iBOS from BECS

For each device, fetch all interfaces and their ipv4 addresses.
Write this to database, protected by a transaction
Columns in database use (mostly) the netbox names
"""

# python standard modules
import os
import sys
import json
import subprocess

if sys.prefix == sys.base_prefix:
    print("Error: You must run this script in a python virtual environment")
    sys.exit(1)

if "/opt" not in sys.path:
    sys.path.insert(0, "/opt")
try:
    import ablib.utils as abutils
    from ablib.becs import BECS
except:
    print("Error: Cannot import ablib.* check PYTHONPATH")
    sys.exit(1)

try:
    # modules installed with pip

    # modules, installed with pip, django
    import django
    from django.db import transaction

    # Setup django environment
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

    # Setup django
    django.setup()

    # import ORM models
    from base.models import Device, Tag, Parent, Interface, InterfaceTag, Cache

    import lib.base_common as common

except:
    abutils.send_traceback()    # Error in script, send traceback to developer


oids = {}


def parse(data):
    abutils.pprint(data)
    for obj in data:
        print(type(obj), obj)
        if isinstance(obj, dict):
            pass
        elif isinstance(obj, list):
            pass
        else:
            oid = obj["oid"]
            oids[oid] = obj


def get_becs_elements(oid: int = 1):
    """
    Todo, use PHP and its SOAP XML, much faster than Python
    """
    r = subprocess.getoutput(f"/opt/abcontrol/app/tools/becs/get_becs_elements.php {oid}")
    data = json.loads(r)
    parse(data["objects"])
    abutils.pprint(oids)


def store_devices_in_db(becs):
    """
    Get all devices (element-attach) from BECS and store in database
    """

    print("----- Get BECS devices (element-attach) -----")
    becs.get_elements()

    print("----- Save devices in local database -----")
    src = "becs"

    with transaction.atomic():
        Device.objects.filter(field_src=src).delete()
        # Parent.objects.filter(field_src=src).delete()
        # Tag.objects.filter(field_src=src).delete()
        # Interface.objects.filter(field_src=src).delete()
        # InterfaceTag.objects.filter(field_src=src).delete()

        device_count = 0
        interface_count = 0
        for oid, device in becs.elements_oid.items():
            if device["elementtype"] != "ibos":
                continue
            print(device["name"])

            flags = device["flags"]
            if flags is None:
                enabled = True   # Default
            else:
                enabled = flags.find("disable") < 0

            model = ""
            if "parameters" in device:
                for p in device.parameters:
                    if "name" in p:
                        if p.name == "model":
                            try:
                                model = p.values[0].value
                            except KeyError:
                                pass
                            break

            # ASR5k does not support SSH
            if model.startswith("ASR5"):
                connection_method = "telnet"
            else:
                connection_method = "ssh"

            # Get interfaces and their IP addresses for this element-attach
            interfaces = becs.get_interfaces(oid)

            # Get management IPv4 address, default is to use loopback interface
            for interface in interfaces:
                if interface.name == "loopback0" and interface.prefix:
                    device.ipv4_prefix = interface.prefix
                    break

            if device.ipv4_prefix == "":
                # No loopback found or no prefix on loopback, pick first interface with an interface address
                for interface in interfaces:
                    if interface.prefix:
                        print("No loopback ip address found, using interface %s, %s" % (interface.name, interface.ipv4_prefix))
                        device.ipv4_prefix = interface.ipv4_prefix
                        break

            if not device.ipv4_prefix:
                print("No management ip address found, ignoring device")
                continue

            device.ipv6_prefix = ""   # Todo

            device_count += 1

            d = Device(
                name=device["name"],
                manufacturer="Waystream",
                model=model,
                comments="",
                role=device.role,
                site_name="",
                platform=device.elementtype,
                ipv4_prefix=device.ipv4_prefix,
                ipv6_prefix=device.ipv6_prefix,
                enabled=enabled,
                alarm_timeperiod=device["_alarm_timeperiod"],
                alarm_destination=device["_alarm_destination"],
                alarm_interfaces=False,
                connection_method=connection_method,
                monitor_grafana=False,
                monitor_icinga=True,
                monitor_librenms=True,
                backup_oxidized=False,
                field_src=src,
            )
            d.save()

            for parent in device["_parents"]:
                p = Parent(
                    device=d,
                    parent=parent,
                    field_src=src,
                )
                p.save()

            for interface in interfaces:
                if interface.prefix:
                    print("   ", interface.name, interface.role, interface.prefix)
                ipv4_prefix = interface.get("prefix", "")
                if ipv4_prefix is None:
                    ipv4_prefix = ""
                # ipv6_prefix = interface.get("ipv6_prefix", "")
                ipv6_prefix = ""
                interface_count += 1
                i = Interface(
                    device=d,
                    name=interface.name,
                    role=interface.role,
                    ipv4_prefix=ipv4_prefix,
                    ipv6_prefix=ipv6_prefix,
                    enabled=interface.enabled,
                    field_src=src,
                )
                i.save()

    print("Summary")
    print("   Total devices :", len(becs.elements_oid))
    print("   Saved devices :", device_count)
    print("   Interfaces     :", interface_count)


def main():
    becs = BECS(config.becs.eapi, config.becs.username, config.becs.password)
    store_devices_in_db(becs)
    becs.logout()


if __name__ == "__main__":
    try:
        main()
    except:
        # Error in script, send traceback to developer
        abutils.send_traceback()
