#!/usr/bin/env python3

"""
Run periodic tasks
"""

# python standard modules

import os
import sys
import datetime
import subprocess
from typing import List

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
    # modules, installed with pip
    import requests

    # modules, installed with pip, django
    import django
    from django.utils import timezone

    # Setup django environment
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

    # Setup django
    django.setup()

    # Import ORM models 
    from base.models import Log_Entry

except:
    abutils.send_traceback()    # Error in script, send traceback to developer


def run_cmd(cmd: str) -> None:
    cmd: List[str] = cmd.split(" ")
    try:
        os.chdir("/opt/abcontrol/app")
        p = subprocess.Popen(["python3", "-u"] + cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        for line in p.stdout:
            line = line.rstrip()
            print(line)
    except:
        abutils.send_traceback()


def main() -> None:
    print("-----sync_becs_to_netbox -----")
    run_cmd("tools/becs/sync_becs_to_netbox.py --refresh-becs --refresh-netbox")

    # Above sync may have changed netbox, so we need to refresh all data again
    print("----- sync_netbox_to_cache -----")
    run_cmd("tools/netbox/netbox_cli.py refresh-device-cache")

    print("Update DNS")
    run_cmd("tools/dns/update_dns.py")

    print("Update Librenms")
    url = f"{config.api.control.url}/cmd/send/update_librenms"
    print(url)
    r = requests.get(url)
    print(r.text)
    # base/abcontrol_cli.py update_librenms

    print("Update Oxidized")
    url = f"{config.api.control.url}/cmd/send/update_oxidized"
    print(url)
    r = requests.get(url)
    print(r.text)
    # base/abcontrol_cli.py update_oxidized

    print("Update Icinga")
    url = f"{config.api.control.url}/cmd/send/update_icinga"
    print(url)
    r = requests.get(url)
    print(r.text)
    # base/abcontrol_cli.py update_icinga

    timestamp = timezone.now() - datetime.timedelta(days=1)
    print("Deleting log entries older than", timestamp)
    result = Log_Entry.objects.filter(timestamp__lt=timestamp).delete()
    print(result)


if __name__ == '__main__':
    try:
        main()
    except:
        abutils.send_traceback()  # Error in script, send traceback to developer
