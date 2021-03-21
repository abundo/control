#!/usr/bin/env python3 
"""
Check connections between devices, and update Netbox

Uses emmgr, to discover the LLDP/L2_peers
"""

# python standard modules
import os
import sys
import time
import argparse

if sys.prefix == sys.base_prefix:
    print("Error: You must run this script in a python virtual environment")
    sys.exit(1)

if "/opt" not in sys.path:
    sys.path.insert(0, "/opt")
try:
    import ablib.utils as abutils
except:
    print("Error: Cannot import ablib.* check PYTHONPATH")
    sys.exit(1)

try:
    # modules installed with pip
    from orderedattrdict import AttrDict
    import pynetbox

    # modules, django
    import django
    from django.db import transaction

    # Setup django environment
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

    # Setup django
    django.setup()

    # Import ORM models 
    from base.models import Device, Tag, Parent, Interface, InterfaceTag, Cache

    import lib.base_common as common

    netbox = pynetbox.api(url=config.netbox.url, token=config.netbox.token)

except:
    abutils.send_traceback()    # Error in script, send traceback to developer


def full_name(name):
    name = name.lower()
    if "." not in name:
        name = f"{name}.{config.default_domain}"
    return name


def parse_netbox_data(src=None, devices=None, interfaces=None, addresses=None, vm=False):
    """
    Go through data from netbox API, and save in database
    """
    # Build dict, key is interface.id, value is interface, to quickly lookup interface based on interface.id
    # Build dict, key is device name,  value is interface, to quickly lookup interfaces for a device
    interfaces_id = {}      # Key is interface ID
    interfaces_name = {}    # key is device name
    for ifname, interface in interfaces.items():
        interface.addresses = []
        interfaces_id[interface.id] = interface

        #abutils.pprint(interface)
        if vm:
            device_name = full_name(interface.virtual_machine.name)
        else:
            device_name = full_name(interface.device.name)
        if device_name not in interfaces_name:
            interfaces_name[device_name] = {}
        interfaces_name[device_name][interface.name] = interface

    # Add addresses to interfaces
    for address in addresses.values():
        id_ = address.assigned_object_id
        if id_ in interfaces_id:
            interface = interfaces_id[id_]
            # abutils.pprint(interface)
            interface.addresses.append(address)

    # Get netbox interface ip-addresses, add to interfaces
    # todo, use interface.id to find interface?
    for id_, address in addresses.items():
        if address.assigned_object:
            ifname = address.assigned_object.name
            if ifname in interfaces:
                # interfaces[ifname].addresses.append(address)
                interfaces[ifname].ipv4_prefix = address
            else:
                pass
                # print(f"Error: address with ifname '{ifname}' does not exist in interfaces, ipaddr '{address.address}'")

    for name, device in devices.items():
        if not name:
            continue  # No name, ignore device

        # Todo, verify name for valid format/characters
        name = full_name(name)

        # print("name", name)
        # ----- Device -----
        d = Device()
        d.name = name
        d.field_src = src
        
        try:
            d.manufacturer = device.device_type.manufacturer.name
        except (AttributeError, NameError):
            d.manufacturer = ""

        try:
            d.model = device.device_type.model
        except (AttributeError, NameError):
            d.model = ""

        d.comments = device.comments

        try:
            d.role = device.role.name
        except (AttributeError, NameError):
            d.role = None

        if d.role is None:
            # Try old name, netbox is (slowly) changing device_role -> role
            try:
                d.role = device.device_role.name
            except (AttributeError, NameError):
                d.role = ""

        try:
            d.site_name = device.site.name
            if d.site_name == "Default": d.site_name = ""
        except (AttributeError, NameError):
            d.site_name = ""
        
        try:
            d.platform = device.platform.name
        except (AttributeError, NameError):
            d.platform = ""

        try:
            d.ipv4_prefix = device.primary_ip4.address
        except (AttributeError, NameError, KeyError, TypeError):
            d.ipv4_prefix = ""

        try:
            d.ipv6_prefix = device.primary_ip6.address
        except (AttributeError, NameError, KeyError, TypeError):
            d.ipv6_prefix = ""
        
        # 'status': {'value': 1, 'label': 'Active'}, 
        d.enabled = True
        try:
            label = device.status.label
            if label != "Active":
                d.enabled = False
        except (AttributeError, NameError):
            pass

        try:
            tmp = device.custom_fields["alarm_timeperiod"]["label"].split()
            if tmp: 
                tmp = tmp[0]
            else:
                tmp = ""
            d.alarm_timeperiod = tmp
        except (AttributeError, NameError, TypeError):
            d.alarm_timeperiod = ""

        try:
            tmp = device.custom_fields["alarm_destination"]["label"]
            d.alarm_destination = common.commastr_to_list(tmp)
        except (AttributeError, NameError, TypeError):
            d.alarm_destination = []

        try:
            d.alarm_interfaces = device.custom_fields.get("alarm_interfaces", False)
            if d.alarm_interfaces is None: d.alarm_interfaces = False
        except (AttributeError, NameError):
            d.alarm_interfaces = False

        try:
            tmp = device.custom_fields["connection_method"]["label"]
            d.connection_method = tmp
        except (TypeError, AttributeError, NameError):
            d.connection_method = ""

        try:
            d.monitor_grafana = device.custom_fields.get("monitor_grafana", False)
            if d.monitor_grafana is None: d.monitor_grafana = False
        except (AttributeError, NameError, KeyError):
            d.monitor_grafana = False

        try:
            d.monitor_icinga = device.custom_fields.get("monitor_icinga", True)
            if d.monitor_icinga is None: d.monitor_icinga = True
        except (AttributeError, NameError):
            d.monitor_icinga = False

        try:
            d.monitor_librenms = device.custom_fields.get("monitor_librenms", True)
            if d.monitor_librenms is None: d.monitor_librenms = True
        except (AttributeError, NameError):
            d.monitor_librenms = False

        try:
            d.backup_oxidized = device.custom_fields.get("backup_oxidized", False)
            if d.backup_oxidized is None: d.backup_oxidized = False
        except (AttributeError, NameError):
            d.backup_oxidized = False

        d.save()

        # ----- Parent -----
        try:
            parents = device.custom_fields.get("parents", "")
            parents = common.commastr_to_list(parents, add_domain=config.default_domain)
        except (AttributeError, NameError):
            parents = None

        if parents:
            for parent in parents:
                p = Parent(
                    device = d,
                    parent = parent,
                    field_src = src,
                )
                p.save()

        # ----- Tag -----
        if device.tags:
            for tag in device.tags:
                t = Tag(
                    device = d,
                    tag = tag,
                    field_src = src,
                )
                t.save()

        # ----- Interfaces, InterfaceTags, addresses -----

        try:
            interfaces = interfaces_name[name]
            if interfaces:
                for ifname,interface in interfaces.items():
                    # print(" ", ifname)
                    ipv4_prefix  =""
                    ipv6_prefix  =""
                    if interface.addresses:
                        # print(" ", ifname, "address:", interface.addresses[0].address)
                        ipv4_prefix = interface.addresses[0].address
                    i = Interface(
                        device = d,
                        name = ifname,
                        role = "",
                        enabled = interface.enabled,
                        ipv4_prefix = ipv4_prefix,
                        ipv6_prefix = ipv6_prefix,
                        field_src = src,
                    )
                    i.save()

                    if interface.tags:
                        for tag in interface.tags:
                            it = InterfaceTag(
                                interface = i,
                                tag = tag,
                                field_src = src,
                            )
                            it.save()
        except KeyError:
            pass   # no interface


def get_netbox_devices(name=None):
    """
    Get one or all devices and virtual machines from netbox
    Include interfaces and ipaddresses
    """

    devices = AttrDict()
    interfaces = AttrDict()
    vminterfaces = AttrDict()
    vmdevices = AttrDict()
    addresses = AttrDict()

    if name:
        if "." in name:
            name = name.split(".", 1)[0]

    print("----- Get NetBox virtual machines -----")
    if name:
        data = netbox.virtualization.virtual_machines.filter(name=name) # Get one device
    else:
        data = netbox.virtualization.virtual_machines.all()             # Get all devices
    print(f"Got {len(data)} virtual machines")

    for d in data:
        vmdevices[d.name] = d

    print("----- Get NetBox virtual machine interfaces -----")
    if 1:
        data = []
        if name:
            try:
#                data = netbox.virtualization.interfaces.filter(virtual_machine_id=d.id)  # Get one interface
                data = netbox.virtualization.interfaces.filter(virtual_machine=name)  # Get one interface
            except pynetbox.RequestError as err:
                print(err.error)
                print(err.req)
        else:
            try:
                data = netbox.virtualization.interfaces.all()                # Get all interfaces
            except pynetbox.RequestError as err:
                print(err.error)
                print(err.req)
        print(f"Got {len(data)} virtual machine interfaces")

        for d in data:
            vminterfaces[d.id] = d
    
    print("----- Get NetBox devices -----")
    if name:
        data = netbox.dcim.devices.filter(name=name)    # Get one device
    else:
        data = netbox.dcim.devices.all()                # Get all devices
    print(f"Got {len(data)} devices")

    for d in data:
        devices[d.name] = d

    print("----- Get NetBox device interfaces -----")
    if name:
        data = netbox.dcim.interfaces.filter(device=name)  # Get one interface
    else:
        data = netbox.dcim.interfaces.all()                # Get all interfaces
    print(f"Got {len(data)} interfaces")

    for d in data:
        interfaces[d.id] = d

    print("----- Get NetBox addresses -----")
    # We fetch all addresses, much faster than fetching per device (one instead of many API calls)
    if name:
        data = netbox.ipam.ip_addresses.filter(device=name)     # Get one address
    else:
        data = netbox.ipam.ip_addresses.all()                   # Get all addresses
    print(f"Got {len(data)} ip-addresses")

    for d in data:
        addresses[d.id] = d

    src = "netbox"
    with transaction.atomic():
        print("----- Deleting old Netbox data from database (in a transaction) -----")
        if len(devices) > 1:
            Device.objects.filter(field_src=src).delete()
        else:
            d = list(devices.values())[0]
            name = full_name(d.name)
            Device.objects.filter(name=name).delete()

        # Parse responses from Netbox, virtual machines
        print("----- Parse and save Netbox virtual machines -----")
        parse_netbox_data(src=src, devices=vmdevices, interfaces=vminterfaces, addresses=addresses, vm=True)

        # Parse responses from Netbox, devices
        print("----- Parse and save Netbox devices -----")
        parse_netbox_data(src=src, devices=devices, interfaces=interfaces, addresses=addresses)


def main(name=None):
    get_netbox_devices(name=name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-N", "--name")
    args = parser.parse_args()

    try:
        main(name=args.name)
    except:
        abutils.send_traceback()    # Error in script, send traceback to developer
