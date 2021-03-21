#!/usr/bin/env python3
"""
Common functions for Netbox
"""

# python standard modules
import os
import sys
import json

# Modules installed with pip
from orderedattrdict import AttrDict
from django.utils.text import slugify
from django.db import transaction

# Assumes PYTHONPATH is set
import ablib.utils as abutils
import lib.base_common as common
from lib.netbox import Netbox


class Device_Cache:
    """
    Manage cache of Netbox devices, saved as a JSON string in the database table
    This is used by the device-api, to be able to respond with delay
    """

    exception = Netbox.exception

    def __init__(self, config=None, cache_cls=None):
        self.config = config
        self.cache_cls = cache_cls
        self.devices = AttrDict()   # All devices, key is name, value is device data
        self.netbox = None

    def connect(self):
        if self.netbox:
            return
        self.netbox = Netbox(config=self.config)
        
    def get_devices(self, name: str = None):
        """
        Get one or all devices from cache
        Return None if nothing found
        Todo: check timestamp, if too old, ignore data
        Todo: Low watermark on # of devices, if below generate exception
        """
        if self.devices:
            return self.devices     # Return copy from memory

        if name:
            r = AttrDict()
            n = common.Name(name)
            c = self.cache_cls.objects.filter(name=n.long)
            if not c:
                return r
            data = list(c.values())[0]["data"]
            data = json.loads(data)
            r[data["name"]] = data
            return r
        else:
            c = self.cache_cls.objects.filter(name="")
            if not c:
                return None
            data = list(c.values())[0]["data"]
            data = json.loads(data, object_pairs_hook=AttrDict)
            self.devices = data
            return data

    def get_device(self):
        pass

    def save_devices(self, devices=None):
        """
        Save devices in cache
        """
        # self.connect()
        with transaction.atomic():
            self.cache_cls.objects.all().delete()
            c = self.cache_cls(name="", data=json.dumps(devices))
            c.save()

            for name, device in devices.items():
                c = self.cache_cls(name=name, data=json.dumps(device))
                c.save()

    def save_device(self, name: str = None, device=None):
        """
        Save one device in cache
        This can only be done if all devices already exist in cache
        """
        # self.connect()
        n = common.Name(name)

        # ----- Update cache entry with all devices ------
        # c = self.cache_cls.objects.filter(name="")
        c = self.cache_cls.objects.get(name="")
        if not c:
            raise RuntimeError("Device cache, cannot update a device, all devices must exist in cache")
        devices = json.loads(c.data)
        devices[n.long] = device
        c.data = json.dumps(devices)
        c.save()

        # ----- Update individual cache entry ------
        c = self.cache_cls.objects.filter(name=n.long)
        if not c:
            c = self.cache_cls(name=n.long, data=json.dumps(device))
        else:
            c.data = json.dumps(device)
        c.save()

    def delete_devices(self):
        """
        Delete all devices in cache
        """
        self.devices = AttrDict()
        self.cache_cls.objects.all().delete()

    def delete_device(self, device=None):
        """
        Delete all devices in cache
        """
        raise RuntimeError("Not implemented")

    def refresh(self, name: str = None):
        """
        Read one or all devices from Netnox and refresh cache
        """
        self.connect()
        devices = self.netbox.get_devices(name=name, refresh=True)
        if name:
            n = common.Name(name)
            self.save_device(name=n, device=devices)
        else:
            self.save_devices(devices)
        return devices


if __name__ == "__main__":
    """
    Function test
    """

    # python standard modules
    import argparse

    # modules installed with pip

    # modules, installed with pip, django
    import django

    # Setup django environment, django
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
    django.setup()

    # import ORM models
    from base.models import Cache

    # parser
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=[
        "get-devices", 
        "refresh-device-cache",
        ])
    parser.add_argument("-n", "--name")
    parser.add_argument("--refresh", default=False, action="store_true")
    args = parser.parse_args()

    device_cache = Device_Cache(config=config, cache_cls=Cache)

    if args.cmd == "get-devices":
        devices = device_cache.get_devices(name=args.name)
        abutils.pprint(devices)
        print(f"Got {len(devices)} devices")

    elif args.cmd == "refresh-device-cache":
        devices = device_cache.refresh()
        print(f"Refreshed {len(devices)} devices")

    else:
        print("Internal error, unknown command", args.cmd)
