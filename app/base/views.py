import datetime
import requests

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

import ablib.utils as abutils

# Create your views here.


def home(request):
    # Load file with links
    links = abutils.load_config("/etc/abcontrol/index.yaml")
    return render(request, 'base/index.html', {"links": links})


@login_required
def sync(request):
    return render(request, 'base/sync.html')


def dhcpd_leases(request):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    r = requests.get(config.api.dhcp_clients.url)   # Todo settings, or use rabbitmq procedure call

    return render(request, 'base/dhcpd_leases.html', {"leases": r.text, "timestamp": timestamp})


@login_required
def report_bbe(request):
    return render(request, 'base/report_bbe.html')
