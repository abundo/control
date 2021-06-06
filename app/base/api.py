#!/usr/bin/env python3

import sys
import yaml
import sqlite3
import gzip
import uuid
from typing import List

import json
import pika

from orderedattrdict import AttrDict
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, Http404
from django.forms.models import model_to_dict
from django.views.decorators.csrf import csrf_exempt

from .models import Device, Tag, Parent, Interface, InterfaceTag, Cache, Log_Entry


sys.path.insert(0, "/opt")
import ablib.utils as abutils
import lib.base_common as base_common
from lib.device import Device_Cache


class API_Exception(Exception):
    pass


# ############################################################################
#
#  Logs
#
# ############################################################################

def log(request, id_: int = None, tzoffset=None):
    """
    Return logs with id and higher.
    If id is None, return last 10 rows
    """
    response = []
    if id_:
        result = Log_Entry.objects.order_by("-serialid").filter(id__gt=id_)[:10]
    else:
        result = Log_Entry.objects.order_by("-serialid")[:500]
    for r in result:
        # convert timestamp to iso-8601
        timestamp = r.timestamp
        tmp = model_to_dict(r)
        tmp["timestamp"] = timestamp.isoformat()
        response.insert(0, tmp)
    return JsonResponse({"data": response})


# ############################################################################
#
#  Control sync etc.
#  This sends messages over rabbitmq to the service that performs the action
#
# ############################################################################


def cmd_send(request, cmd: str = None):
    print("cmd", cmd)
    if cmd in base_common.rabbitmq_cmds:
        rabbitmq = base_common.Rabbitmq_Mgr(config.rabbitmq)
        rabbitmq.exchange_cmd_send()
        rabbitmq.send_cmd(cmd, {})
        rabbitmq.close()
        return HttpResponse("Message sent!\n")
    return HttpResponse("Unknown message\n")


# ----------------------------------------------------------------------------
# API
# ----------------------------------------------------------------------------

def home(request):
    return HttpResponse("API!\n")


def devices(request, name: str = None):
    device_cache = Device_Cache(config=config, cache_cls=Cache)
    try:
        devices = device_cache.get_devices(name=name)
        if devices is not None:
            return JsonResponse(devices)
        raise Http404("Database does not contain devices from netbox and becs")
    except Device_Cache.exception as err:
        raise Http404(err)


def devices_refresh_cache(request, name: str = None):
    """
    Refresh all or one device from Netbox to cache
    """
    device_cache = Device_Cache(config=config, cache_cls=Cache)
    try:
        response = dict(errno=0, msg="")
        devices = device_cache.refresh(name=name)
        response = dict(errno=0, msg=f"Device cache updated with {len(devices)} devices")
    except Device_Cache.exception as err:
        response = dict(errno=1, msg=str(err))
    return JsonResponse(response)


@csrf_exempt
def netbox(request):
    """
    Called by netbox webhook.
    Handle changes to devices/interfaces, virtual machines/interfaces
    """

    import tools.netbox.sync_netbox as sync_netbox

    # abutils.pprint(request, "request")
    body = json.loads(request.body)
    # abutils.pretty_print(body, "body")

    # 2.10.0
    # #4711 - Renamed Webhook obj_type to content_types

    update_device_name = None
    event = body["event"]
    model = body["model"]
    data = body["data"]
    name = data["name"]
    print(f"event: {event}")
    print(f"model: {model}")
    print(f"name:  {name}")
    abutils.pprint(data)

    # ----- Device -----
    if event == "created" and model == "device":
        update_device_name = name
        print(f"Device '{update_device_name}' created, insert into Device-API Database")

    elif event == "updated" and model == "device":
        update_device_name = name
        print(f"Device '{update_device_name}' updated, update Device-API Database")

    elif event == "deleted" and model == "device":
        update_device_name = name
        print(f"Device '{update_device_name}' deleted, remove from Device-API Database")

    # ----- Interface -----
    elif event == "created" and model == "interface":
        update_device_name = data["device"]["name"]
        print(f"Device '{update_device_name}' interface '{interface}' created, insert into Device-API Database")

    elif event == "updated" and model == "interface":
        update_device_name = data["device"]["name"]
        print(f"Device '{update_device_name}' interface '{name}' updated, update Device-API database")

    elif event == "deleted" and model == "interface":
        update_device_name = data["device"]["name"]
        print(f"Device {update_device_name} interface {name} deleted, remove from Device-API database")

    # ----- Virtual Machine -----
    if event == "created" and model == "virtualmachine":
        update_device_name = name
        print(f"Virtual Machine '{update_device_name}' created, insert into Device-API database")

    elif event == "updated" and model == "virtualmachine":
        update_device_name = name
        print(f"Virtual Machine '{update_device_name}' updated, update Device-API database")

    elif event == "deleted" and model == "virtualmachine":
        update_device_name = name
        print(f"Virtual Machine '{update_device_name}' deleted, remove from Device-API database")

    # ----- Virtual Machine Interface -----
    elif event == "created" and model == "vminterface":
        update_device_name = data["virtual_machine"]["name"]
        print(f"Virtual Machine '{update_device_name}', interface '{name}' created, insert into Device-API database")

    elif event == "updated" and model == "vminterface":
        update_device_name = data["virtual_machine"]["name"]
        print(f"Virtual Machine '{update_device_name}' interface '{name}' updated, update Device-API database")

    elif event == "deleted" and model == "vminterface":
        update_device_name = data["device"]["name"]
        print(f"Virtual Machine '{update_device_name}' interface '{name}' deleted, remove from Device-API database")
    else:
        print(f"Error: event {event}, unknown model {model}")

    # ----- IP Addresses (on device/virtual machine interfaces -----

    # ----- VLAN -----

    if update_device_name:
        print(f"Refreshing Device-API and cache for name '{update_device_name}'")

        # Fetch fresh data from Netbox
        devices = sync_netbox.get_devices_from_netbox(name=update_device_name, interfaces=True)

        # Store new data in Device-API database
        # sync_netbox_to_db.store_devices_in_db(devices)

        # Update cache for Device-API
        devices_refresh_cache(request, name=update_device_name)

        # Update all systems which may be affected of the change
        for cmd in base_common.rabbitmq_cmds.keys():
            if cmd.startswith("update"):
                cmd_send(request, cmd=cmd)

    response = dict(errno=0, msg="")
    return JsonResponse(response)
