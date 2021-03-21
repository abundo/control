#!/usr/bin/env python3

"""
CLI interface to various functions
All communication is done using rabbitmq
"""

# python standard modules
import os
import sys
import argparse

# ----- Start of configuration items -----

CONFIG_FILE = "/etc/abcontrol/abcontrol.yaml"

# ----- End of configuration items -----

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
    # from orderedattrdict import AttrDict
    # import pika

    # modules, installed with pip, django
    import django
    # from django.db import transaction

    # Setup django environment
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

    # Setup django
    django.setup()

    # Import ORM models
    # from base.models import Device, Tag, Parent, Interface, InterfaceTag, Cache

    import lib.base_common as base_common

except:
    abutils.send_traceback()    # Error in script, send traceback to developer


def send(cmd, args):
    rabbitmq = base_common.Rabbitmq_Mgr(config.rabbitmq)
    rabbitmq.exchange_cmd_receive()
    rabbitmq.exchange_log_receive()

    # Send cmd to listeners
    args = vars(args)
    if "cmd" in args:
        del args["cmd"]
    xid = rabbitmq.send_cmd(cmd, cmd)

    print("Waiting for response, show log while waiting")
    for log_entry in rabbitmq.receive_log():
        if "msgid" in log_entry and log_entry["msgid"] == xid:
            break
        print(log_entry["msg"])

    rabbitmq.close()


def send_json(cmd, data):
    """
    Send cmd over rabbitmq
    data is dict, will be json formatted
    """
    rabbitmq = base_common.Rabbitmq_Mgr(config.rabbitmq)
    rabbitmq.exchange_cmd_receive()
    rabbitmq.exchange_log_receive()

    # Send cmd to listeners
    xid = rabbitmq.send_cmd(cmd, data)

    print("Waiting for response, show log while waiting")
    for log_entry in rabbitmq.receive_log():
        if "msgid" in log_entry and log_entry["msgid"] == xid:
            break
        print(log_entry["msg"])

    rabbitmq.close()
    return log_entry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=[
        "send",
        "sync_all",
        "icinga_process_check_result",
    ])
    parser.add_argument("--msg", choices=base_common.rabbitmq_cmds, default=None)
    parser.add_argument("--host")
    parser.add_argument("--service")
    parser.add_argument("--exit-status")
    parser.add_argument("--plugin-output")
    parser.add_argument("--performance-data")
    parser.add_argument("--check_command")
    parser.add_argument("--check_source")
    parser.add_argument("--execution_start")
    parser.add_argument("--execution_end")
    parser.add_argument("--ttl")

    args = parser.parse_args()

    if args.cmd == "sync_all":
        for c in base_common.rabbitmq_cmds:
            if c not in ["ping", "sync_all"]:
                send(c, args)

    elif args.cmd == "send":
        if not args.msg:
            print("No message specified")
        send(args.msg, args)

    elif args.cmd == "icinga_process_check_result":
        data = {}
        for attr in ["host", "service", "exit_status"]:
            if args[attr]:
                data[attr] = args[attr]
        res = send_json("args.cmd", data)
        print("res", res)

    else:
        print("Error: unknown cmd", args.cmd)


if __name__ == "__main__":
    try:
        main()
    except:
        abutils.send_traceback()  # Error in script, send traceback to developer
