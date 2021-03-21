import sys
import datetime
import requests

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required


import pynetbox

if "/opt" not in sys.path:
    sys.path.insert(0, "/opt")
import ablib.utils as abutils

try:
    import emmgr.lib.element
except ModuleNotFoundError:
    pass


# Create your views here.

@login_required
def verify(request, name: str = None):
    """
    Work in progress
    """
    # Fetch config

    # We only handle devices in NetBox
    # Fetch info from netbox
    netbox = pynetbox.api(url=config.netbox.url, token=config.netbox.token)
    if "." in name:
        name = name.split(".", 1)[0]
    device = netbox.dcim.devices.get(name=name)
#    abutils.pprint(device, "device")

    # Get interfaces for device
    interfaces = netbox.dcim.interfaces.filter(device=name)
    for interface in interfaces:
        abutils.pprint(interface, "interface")

    # Get configured VLANs on each interface

    # Fetch live VLAN configuration from element

    return render(request, 'device.html', {"name": name, "device": device, "interfaces": interfaces})


def get_config(request, name=None):
    """
    Fetch device configuration (running-config)
    """
    response = dict(data=1)
    return JsonResponse(response)


def set_config(request):
    """
    Update device configuration
    """
    pass
