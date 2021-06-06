#!/usr/bin/env python3

"""
Service
  Listen to RabbitMQ commands, and perform needed actions
  Listen to RabbitMQ logs, and store in database
  Listen on Netbox Webcalls, and perform neeeded actions

Script is written so it can be used on multiple hosts.
It checks the configuration file in /etc/abcontrol/abcontrol.yaml for the rabbitmq messages it should handle
"""
import os
import sys
import json
import platform
import datetime
import subprocess
import requests
import multiprocessing
from http.server import BaseHTTPRequestHandler, HTTPServer

if sys.prefix == sys.base_prefix:
    print("Error: You must run this script in a python venv")
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
    from django.forms.models import model_to_dict
    # from django.utils.timezone import make_aware

    # Setup django environment
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

    # Setup django
    django.setup()

    import lib.base_common as common

    # Import ORM models 
    # from base.models import Device, Tag, Parent, Interface, InterfaceTag, Cache
    from base.models import Log_Entry
except:
    abutils.send_traceback()    # Error in script, send traceback to developer


rabbitmq = None


def log(msg: str, **kwargs):
    """
    Log a message to stdout and log channel over rabbitmq
    """
    log_entry = Log_Entry(msg=msg)
    data = model_to_dict(log_entry)
    rabbitmq.send_log(**data)


class Capturing:
    """
    Context manager that sends all stdout/stderr text over rabbitmq
    """
    def __enter__(self):
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self
        self.buffer = ""
        return self

    def __exit__(self, *args):
        sys.stdout = self._stdout
        sys.stderr = self._stderr

    def write(self, msg):
        self._stdout.write(msg)
        self.buffer += msg
        while "\n" in self.buffer:
            line, tmp, self.buffer = self.buffer.partition("\n")
            rabbitmq.send_log(line)

    def flush(self):
        """Handle any nonwritten data in the buffer"""
        self.write("\n")


def background_log_worker():
    """
    Listen on rabbitmq messages, and store them in the database
    This is running as a separate process, using a dedicated connection to rabbitmq
    """
    print("Starting worker process, listening on rabbitmq logs and saving entries to database")

    # Connect to rabbitmq
    rabbitmq = common.Rabbitmq_Mgr(config.rabbitmq)
    rabbitmq.exchange_log_receive()
    while True:
        for log_entry_json in rabbitmq.receive_log():
            if "xid" not in log_entry_json:
                timestamp = datetime.datetime.strptime(log_entry_json["timestamp"] + "-+0000", "%Y-%m-%d %H:%M:%S.%f-%z")
                log_entry_json["timestamp"] = timestamp
                log_entry = Log_Entry(**log_entry_json)
                with open("/tmp/a", "w") as f:
                    f.write(str(vars(log_entry)))
                log_entry.save()
            else:
                print("ERROR: abcontrol_worker got something with xid in the message", log_entry_json)


def background_netbox_webhook_worker():
    """
    Listen on netbox webhook calls, and perform the correct action
    This is running as a separate process, using a dedicated connection to rabbitmq
    """
    print("Starting abcontrol_worker process, listening on netbox webhook calls")
    rabbitmq = common.Rabbitmq_Mgr(config.rabbitmq)
    rabbitmq.exchange_cmd_send()

    addr: str = "0.0.0.0"    # Listen on 127.0.0.1?
    port: int = 7777

    class NetboxServer(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            print(self)

    server = HTTPServer((addr, port), NetboxServer)
    server.serve_forever()


def ping(data):
    """
    Return a response, we are alive!
    """
    handles: str = ", ".join(config.roles.keys())
    log(f"Ping response: from {platform.node()}. handles {handles}")
    rabbitmq.send_log("Done", msgid=data["xid"])


def run_cmd(data=None, name: str = None, directory=None, cmd: str = None):
    log(f"Running {name}")
    try:
        with Capturing():
            os.chdir("/opt/abcontrol/app")
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            for line in p.stdout:
                line = line.rstrip()
                print(line)
        print("Done")
        rabbitmq.send_log("Done", msgid=data["xid"])
    except:
        print("Error")
        rabbitmq.send_log("Error", msgid=data["xid"])
        abutils.send_traceback()


def sync_becs_to_netbox(data):
    if "becs" not in config.roles:
        return
    run_cmd(data=data,
            name="sync_becs_to_netbox",
            cmd=["/opt/abcontrol/bin/python3", "-u", "tools/becs/sync_becs_to_netbox.py", "--refresh-becs", "--refresh-netbox"]
    )


def sync_netbox_to_device_api(data):
    if "abcontrol" not in config.roles:
        return
    run_cmd(data=data,
            name="sync_netbox_to_device_api",
            # cmd=["/opt/abcontrol/bin/python3", "-u", "app/tools/netbox/sync_netbox_to_device_api.py", "--refresh-netbox"]
            cmd=["/opt/abcontrol/bin/python3", "-u", "lib/device.py", "refresh-device-cache"]
    )


def update_dns(data):
    if "dns" not in config.roles:
        return
    run_cmd(data=data,
            name="update_dns()",
            cmd=["/opt/abcontrol/bin/python3", "-u", "tools/dns/update_dns.py"]
    )


def update_librenms(data):
    if "librenms" not in config.roles:
        return
    run_cmd(data=data,
            name="update_librenms()",
            cmd=["/opt/abcontrol/bin/python3", "-u", "tools/librenms/update_librenms.py"]
    )


def update_oxidized(data):
    if "oxidized" not in config.roles:
        return
    run_cmd(data=data,
            name="update_oxidized()",
            cmd=["/opt/abcontrol/bin/python3", "-u", "tools/oxidized/update_oxidized.py"]
    )
    

def update_icinga(data):
    if "icinga" not in config.roles:
        return
    run_cmd(data=data,
            name="update_icinga()",
            cmd=["/opt/abcontrol/bin/python3", "-u", "tools/icinga/update_icinga.py"]
    )


def icinga_process_check_result(data):
    if "icinga" not in config.roles:
        return

    try:
        jdata = json.loads(data)
    except json.JSONDecodeError(msg, doc, pos):
        pass

    req_url = "https://localhost:5665/v1/actions/process-check-result"
    headers = {
        'Accept': 'application/json',
    }
    res = {}
    hostname = jdata.get("hostname")
    service = jdata.get("service")
    if service:
        res["type"] = "Service"
        res["filter"] = f"host.name=={hostname} && service.name={service}"
    else:
        res["type"] = "Host"
        res["filter"] = f"host.name=={hostname}"

    for attr in [
        "exit_status", "plugin_output", "performance_data", "check_command",
        "check_source", "execution_start", "execution_end", "ttl"
        ]:
        if attr in jdata:
            res[attr] = jdata[attr]

    resp = requests.post(
        req_url,
        headers=headers,
        auth=(config.icinga.api.username, config.icinga.api.password),
        data=json.dumps(res),
        verify=False
    )

    if (resp.status_code == 200):
        print("Result: " + json.dumps(resp.json(), indent=4, sort_keys=True))
    else:
        print(resp.text)


def main():
    global rabbitmq

    if "save_log" in config.msg_handler.handle:
        proc_log = multiprocessing.Process(target=background_log_worker)
        proc_log.start()

    if "netbox_webhook_listener" in config.msg_handler.handle:
        proc_netbox = multiprocessing.Process(target=background_netbox_webhook_worker)
        proc_netbox.start()

    rabbitmq = common.Rabbitmq_Mgr(config.rabbitmq)
    rabbitmq.exchange_cmd_receive()
    print("Waiting for commands from Rabbitmq")

    for data in rabbitmq.receive_cmd():
        cmd = data.get("cmd", None)
        print(f"Received command '{cmd}'")

        if cmd == "ping":
            ping(data)
        elif cmd == "sync_becs_to_netbox":
            sync_becs_to_netbox(data)
        elif cmd == "sync_netbox_to_device_api":
            sync_netbox_to_device_api(data)
        elif cmd == "update_dns":
            update_dns(data)
        elif cmd == "update_librenms":
            update_librenms(data)
        elif cmd == "update_icinga":
            update_icinga(data)
        elif cmd == "update_oxidized":
            update_oxidized(data)
        elif cmd == "icinga_process_check_result":
            icinga_process_check_result(data)
        else:
            print("Unknown cmd", cmd)

    rabbitmq.close()


if __name__ == "__main__":
    try:
        main()
    except:
        # Error in script, send traceback to developer
        abutils.send_traceback()
