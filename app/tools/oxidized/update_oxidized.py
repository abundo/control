#!/usr/bin/env python3

"""
Build list of devices in oxidized, from device-api
Restart oxidized if configuration has changed
"""

# python standard modules
import os
import sys
from collections import Counter

if sys.prefix == sys.base_prefix:
    print("Error: You must run this script in a python virtual environment")
    sys.exit(1)

if "/opt" not in sys.path:
    sys.path.insert(0, "/opt")
try:
    import ablib.utils as abutils
    from ablib.devices import Device_Mgr
    from ablib.oxidized import Oxidized_Mgr
except:
    print("Error: Cannot import ablib.* check PYTHONPATH")
    sys.exit(1)

try:
    # modules installed with pip
    from orderedattrdict import AttrDict

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

except:
    abutils.send_traceback()    # Error in script, send traceback to developer


def main():
    oxidized_mgr = Oxidized_Mgr(config=config.oxidized)
    
    print("----- Get devices from device-api -----")
    device_mgr = Device_Mgr(config=config.device)
    tmp_devices = device_mgr.get_devices()

    print("----- Filter devices that do not need backup -----")
    count = Counter(
        ignored_not_enabled=0,
        ignored_backup_oxidized=0,
        ignored_name=0,
        ignored_manufacturer=0,
        ignored_model=0,
        ignored_source=0,
        ignored_platform=0,
    )
    devices = {}  # Key is name
    for name, device in tmp_devices.items():
        if not device.enabled:
            count["ignored_not_enabled"] += 1
            continue

        if not device.backup_oxidized:
            count["ignored_backup_oxidized"] += 1
            continue

        if name in config.oxidized_sync.ignore_names:
            count["ignore_name"] += 1
            continue

        if device.manufacturer in config.oxidized_sync.ignore_manufacturers:
            count["ignore_manufacturer"] += 1
            continue

        if device.model in config.oxidized_sync.ignore_models:
            count["ignore_model"] += 1
            continue

        # Get all keys that exist in both dict
        shared_keys = set(device.tags).intersection(config.oxidized_sync.ignore_device_tags)
        if shared_keys:
            count["ignore_src"] += 1
            continue

        if device.platform in config.oxidized_sync.ignore_platforms:
            count["ignore_platformc"] += 1
            continue
    
        if not device.primary_ip4:
            continue

        devices[name] = device

    print("Devices    : %5d devices" % len(devices))
    print("Persistent : %5d devices" % len(config.oxidized_sync.persistent_devices))
    print("Total      : %5d devices" % (len(devices) + len(config.oxidized_sync.persistent_devices)))
    print()
    
    t = config.oxidized.router_db
    changed = False
    count = oxidized_mgr.save_devices(t.tmp,
                                      devices,
                                      ignore_models=config.oxidized_sync.ignore_models)
    print("Wrote %d devices to oxidized" % (count))

    changed = abutils.install_conf_file(src=t.tmp,
                                        dst=t.dst,
                                        changed=changed)
    if changed:
        print("----- configuration changed, reloading oxidized")
        oxidized_mgr.reload()
    else:
        print("----- configuration unchanged")


if __name__ == '__main__':
    try:
        main()
    except:
        abutils.send_traceback()  # Error in script, send traceback to developer
