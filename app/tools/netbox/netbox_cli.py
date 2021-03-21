#!/usr/bin/env python3 
"""
Fetch all devices from NetBox

For each device, fetch all interfaces and their ipv4 addresses.
Write this to database, protected by a transaction
Columns in database use (mostly) the netbox names
"""

# python standard modules
import os
import sys
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

    # modules, django
    import django

    # Setup django environment
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

    # Setup django
    django.setup()

    # Import ORM models
    # from base.models import Device, Tag, Parent, Interface, InterfaceTag, Cache
    from base.models import Cache

    import lib.base_common as common
    from lib.netbox import Netbox
    from lib.device import Device_Cache

except:
    abutils.send_traceback()    # Error in script, send traceback to developer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=[
        "get-devices", 
        "refresh-device-cache",
        ])
    parser.add_argument("-n", "--name")
    parser.add_argument("--refresh", default=False, action="store_true")
    args = parser.parse_args()

    if args.cmd == "get-devices":
        device_cache = Device_Cache(config=config, cache_cls=Cache)
        devices = device_cache.get_devices(name=args.name)
        print(f"Got {len(devices)} ")

    elif args.cmd == "refresh-device-cache":
        device_cache = Device_Cache(config=config, cache_cls=Cache)
        devices = device_cache.refresh()
        print(f"Refreshed {len(devices)} devices")

    else:
        print("Internal error, unknown command", args.cmd)


if __name__ == "__main__":
    try:
        main()
    except:
        abutils.send_traceback()    # Error in script, send traceback to developer
