#!/usr/bin/env python3

"""
Syncs devices in librenms, based on device-api
    If device is missing in librenms, create it
    If device exist in librenms but not in device-api delete it
    For each device, check and adjust
    - enabled flag
    - parents
    - all interfaces
      -  enabled flags

    note:
    - device-äpi uses "enabled" true/false for devices and interfaces
      librenms uses "Ignore alerts" true/false for devices and interfaces
"""

# python standard modules
import os
import sys
import re

# Assumes PYTHONPATH is set so ablib can be imported
if "/opt" not in sys.path:
    sys.path.insert(0, "/opt")
try:
    import ablib.utils as abutils
    from ablib.devices import Device_Mgr
    from ablib.librenms import Librenms_Mgr
except:
    print("Error: Cannot import ablib.* check PYTHONPATH")
    sys.exit(1)

try:
    # modules installed with pip
    from orderedattrdict import AttrDict

    # modules, django
    import django
    # from django.db import transaction

    # Setup django environment
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

    # Setup django
    django.setup()

    # Import ORM models 
    # from base.models import Device, Tag, Parent, Interface, InterfaceTag, Cache

    import lib.base_common as common

except:
    abutils.send_traceback()    # Error in script, send traceback to developer


roles_enabled_compiled = []
interfaces_disabled_compiled = []


def sync_interfaces(name, librenms_mgr, librenms_device, device):
    # Get interfaces from librenms
    librenms_interfaces = librenms_mgr.get_device_interfaces(name)
    if librenms_interfaces is None:
        print("  Error: No interfaces in Librenms found")
        return
    
    device_interfaces = device.interfaces

    # Default for all ports comes from device api, "alarm_interfaces"
    # If device is from netbox
    #    ignore = netbox custom field "alarm_interfaces"
    #    if interface has tag uplink or tag "librenms_alert_enable", ignore = 0
    #    if interface has tag "librenms_alert_disabled", ignore = 1
    # If device is from BECS
    #    ignore = 0
    #    if interface has role uplink.* then ignore = 1
    for librenms_interface in librenms_interfaces.values():

        if librenms_interface.ifname in device_interfaces:
            librenms_interface_name = librenms_interface.ifname
        elif librenms_interface.ifalias in device_interfaces:
            librenms_interface_name = librenms_interface.ifalias
        elif librenms_interface.ifdescr in device_interfaces:
            librenms_interface_name = librenms_interface.ifdescr
        else:
            librenms_interface_name = None

        if device.alarm_interfaces:  # Default for interfaces in this device
            ignore = 0
        else:
            ignore = 1
        role = ""

        if librenms_interface_name:
            device_interface = device_interfaces[librenms_interface_name]

            if "uplink" in device_interface.tags:
                ignore = 0

            if "librenms_alarm_disable" in device_interface.tags:
                ignore = 1

            if "librenms_alarm_enable" in device_interface.tags:
                ignore = 0

            role = device_interface.get("role")
            if role:
                for role_regex in roles_enabled_compiled:
                    if role_regex.search(role):
                        ignore = 0

            for interface_regex in interfaces_disabled_compiled:
                if interface_regex.search(librenms_interface_name):
                    ignore = 1

        if librenms_interface.ignore != ignore:
            if role:
                role = f"role {role}, "
            print(f"    Name {name}, interface {librenms_interface.ifname}, role {role}, setting ignore to {ignore}")
            d = AttrDict()
            d.ignore = ignore
            librenms_mgr.update_device_interface(port_id=librenms_interface.port_id, data=d)


def main():
    # Compile regex for faster search
    for role in config.librenms_sync.roles_enabled:
        roles_enabled_compiled.append(re.compile(role))

    for interface in config.librenms_sync.interfaces_disabled:
        interfaces_disabled_compiled.append(re.compile(interface))

    librenms_mgr = Librenms_Mgr(config=config)
    librenms_devices = librenms_mgr.get_devices()
    
    device_mgr = Device_Mgr(config=config.api.device)
    devices = device_mgr.get_devices()

    create_in_librenms = []
    delete_in_librenms = []

    print("-" * 79)
    print("Device count")
    print("  Device-API:")
    print("    Devices    : %5d devices" % len(devices))
    print("    Persistent : %5d devices" % len(config.librenms_sync.persistent_devices))
    print("    Total      : %5d devices" % (len(devices) + len(config.librenms_sync.persistent_devices)))
    print()
    print("  Librenms:")
    print("    Devices    : %5d devices" % len(librenms_devices))
    print()
    
    print("-" * 79)
    print("Update /etc/hosts file")
    device_mgr.write_etc_hosts()
    print()

    #
    # Compare Devices-API with devices in Librenms
    #
    
    print("-" * 79)
    print("Checking")
    
    print("  Devices that exist in device-api but not in Librenms (action: create in librenms):")
    for name, device in devices.items():
        if not device.enabled:
            continue
        if not device.monitor_librenms:
            continue
        if name not in librenms_devices:
            print("   ", name)
            create_in_librenms.append(name)

    if len(create_in_librenms) < 1:
        print("    None")

    print("  Devices that exist in Librenms but not in Device-API. (action: delete from librenms)")
    for name, device in librenms_devices.items():
        if name in config.librenms_sync.persistent_devices:
            continue
        device = devices.get(name, None)
        if device is None:
            # Does not exist in Device-API, delete
            delete_in_librenms.append(name)
            continue
        if not device.enabled:
            # Not enabled in device-api, delete
            delete_in_librenms.append(name)
            continue
        if not device.monitor_librenms:
            # Not monitoring in Librenms
            delete_in_librenms.append(name)
            continue

    if len(delete_in_librenms) < 1:
        print("    None")
        
    #
    # Add/delete devices
    #
    
    print()
    print("-" * 79)
    print("Adjust devices in Librenms")
    print("  Creating devices in Librenms")
    if len(create_in_librenms):
        for name in create_in_librenms:
            print("   ", name)
            librenms_mgr.create_device(name=name, force_add=1)
    else:
        print("    None")
    
    print("  Deleting devices in Librenms")
    if len(delete_in_librenms):
        for name in delete_in_librenms:
            print("   ", name)
            librenms_mgr.delete_device(name=name)
    else:
        print("    None")

    #
    # Update status on devices and ports in Librenms
    #
    print("  Updating devices in Librenms")
    if create_in_librenms or delete_in_librenms:
        # devices has been added/deleted, reload list of devices in librenms
        librenms_mgr.clear_cache()
        librenms_devices = librenms_mgr.get_devices()

    for name, librenms_device in librenms_devices.items():
        device = devices.get(name, None)
        if device is None:
            print(f"    Ignoring {name}, not in device-api")
            continue
        update_data = AttrDict()
            
        librenms_enabled = librenms_device.ignore == 0
        enabled = device.enabled
        if librenms_enabled != enabled:
            if enabled:
                update_data.ignore = 0
            else:
                update_data.ignore = 1
            print(f"    Name {name}, setting ignore to {update_data.ignore}")
        
        # Update location
        if device.location:
            if librenms_device.location != device.location:
                print(f"    Location, change from '{librenms_device.hostname}' to '{device.location}'")
                librenms_mgr.set_device_location(librenms_device.device_id, location=device.location)
                update_data.override_sysLocation = 1

        if len(update_data):
            librenms_mgr.update_device(name, update_data)

        # update parents
        parents = sorted(device.parents)
        librenms_parents = librenms_device.dependency_parent_hostname
        if librenms_parents:
            librenms_parents = sorted(librenms_parents.split(","))
        else:
            librenms_parents = []
        if parents != librenms_parents:
            print(f"    Name {name}, setting parents to {parents}")
            librenms_mgr.set_device_parent(device_id=librenms_device.device_id, parent=parents)

        sync_interfaces(name, librenms_mgr, librenms_device, device)
    print("    Done")
    

if __name__ == '__main__':
    try:
        main()
    except:
        abutils.send_traceback()  # Error in script, send traceback to developer
