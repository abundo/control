#!/usr/bin/env python3 
"""
Common functionality for abcontrol
"""

import os
import json
import uuid
import platform
import datetime

import pika
from orderedattrdict import AttrDict
from django.utils import timezone


rabbitmq_cmds = {
    "sync_becs_to_netbox": 1,
    "sync_netbox_to_device_api": 1,
    "update_librenms": 1,
    "update_oxidized": 1,
    "update_icinga": 1,
    "update_dns": 1,
    "ping": 1,
    "icinga_process_check_result": 1,
    "sync_all": 1,
}


class Name:
    """
    Handle device name

    .full  is always name, fully qualified
    .short is always name without default domain

    Example, if default domain is .example.com:

    the name
        device1.example.com
    becomes
        short: device1
        full: device1.example.com 

    the name
        device2.example.net
    becomes
        short: device1.example.net
        full: device1.example.net

    the name
        device3
    becomes
        short: device3
        full: device1.example.com

    """
    def __init__(self, name: str):
        if name is None:
            self.long = ""
            self.full = ""
            self.short = ""
        elif "." in name:
            self.long = name
            self.full = name
            if name.endswith(config.default_domain):
                name = name[:-len(config.default_domain) - 1]
            self.short = name
        else:
            self.long = f"{name}.{config.default_domain}"
            self.full = self.long
            self.short = name

    def __str__(self):
        return self.short


def commastr_to_list(hostnames, add_domain=None):
    """
    Return a list of names from a comma separated string
    If add_domain is True, add default domain name if no . (dot) in hostname
    """
    if hostnames:
        tmp = []
        for hostname in hostnames.split(","):
            hostname = hostname.strip()
            if add_domain and "." not in hostname:
                hostname += "." + add_domain
            tmp.append(hostname)
        return tmp
    return []


def commastr_to_dict(config, names: str, add_domain=None):
    """
    Return a list of names from a comma separated string
    If add_domain is True, add add_domain if no . (dot) in name
    """
    if names:
        tmp = {}
        for name in names.split(","):
            name = name.strip()
            if add_domain and "." not in name:
                name += "." + add_domain
            tmp.append(name)
        return tmp
    return {}


class Rabbitmq_Mgr:
    """
    Handle rabbitmq, connections, exchanges, send/receive cmd, send/receive log
    """
    def __init__(self, config):
        self.config = config
        self.hostname = platform.node()
        self.pid = os.getpid()
        self.open()

    def open(self):
        # Open connection to rabbitmq
        credentials = pika.PlainCredentials(self.config.username, self.config.password)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.config.hostname, credentials=credentials))
        self.channel = self.connection.channel()

    def close(self):
        self.channel.cancel()
        self.channel.close()
        self.connection.close()

    def exchange_cmd_send(self):
        # Exchange for commands to listeners
        self.channel.exchange_declare(exchange="abcontrol", exchange_type="topic")

    def exchange_cmd_receive(self):
        # exchange for receiving commands to me
        self.channel.exchange_declare(exchange="abcontrol", exchange_type="topic")
        result = self.channel.queue_declare("", exclusive=True)
        self.cmd_queue_name = result.method.queue
        self.channel.queue_bind(exchange="abcontrol", queue=self.cmd_queue_name, routing_key="#")

    def exchange_log_receive(self):
        # Exchange for listening on logs
        self.channel.exchange_declare(exchange='logs', exchange_type='fanout')
        result = self.channel.queue_declare(queue="", exclusive=True)
        self.log_queue_name = result.method.queue
        self.channel.queue_bind(exchange="logs", queue=self.log_queue_name)

    def exchange_log_send(self):
        # exchange for sending logs
        self.channel.exchange_declare(exchange='logs', exchange_type='fanout')

    def send_cmd(self, cmd, data):
        # Send cmd to listeners
        # Return xid
        xid = str(uuid.uuid4())
        data = dict(
            cmd=cmd,
            xid=xid,
            data=data,
        )
        self.channel.basic_publish(exchange="abcontrol", routing_key="cmd", body=json.dumps(data))
        return xid

    def receive_cmd(self):
        """
        Receive cmd messages
        Works as a generator, this is blocking
        """
        for method_frame, properties, body in self.channel.consume(self.cmd_queue_name):
            data = json.loads(body)
            yield data

    def send_log(self, msg=None, facility=None, severity=None, hostname=None, appname=None, procid=None, msgid=None, **kwargs):
        """
        Log a message to stdout and log channel over rabbitmq
        """
        if not msg:
            return   # don't send empty rows
        if hostname is None:
            hostname = self.hostname
        if appname is None:
            appname = ""
        if procid is None:
            procid = self.pid
        if msgid is None:
            msgid = ""
        if len(msg) > 250:
            msg = msg[:250] + "..."
        log_entry = dict(
            timestamp=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f"),
            facility=facility,
            severity=severity,
            hostname=self.hostname,
            appname=appname,
            procid=self.pid,
            msgid=msgid,
            msg=msg,
        )
        self.channel.basic_publish(exchange='logs', routing_key='', body=json.dumps(log_entry))

    def receive_log(self):
        """
        Receive log messages
        Works as a generator, this is blocking
        """
        for method_frame, properties, body in self.channel.consume(self.log_queue_name):
            data = json.loads(body)
            yield data
