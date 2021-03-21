#!/usr/bin/env python3
"""
Custom email notification for Icinga2
Uses the same args as the default one shipped with Icinga
"""

import sys
import platform
import argparse
import urllib.parse
import html

if "/opt" not in sys.path:
    sys.path.insert(0, "/opt")
import ablib.utils as abutils
from ablib.email1 import Email
from ablib.icinga import Icinga

# ----- Start of configuration items -----

CONFIG_FILE = "/etc/abcontrol/abcontrol.yaml"

TABLE = '<TABLE style="border-collapse: collapse;">'
TR = '<TR style="border-top: 1px solid black; vertical-align:top;">'


def TH(s=""):
    return f'<TH style="padding-left: 0.5em; padding-right: 0.5em">{s}</TH>'


def TH_L(s=""):
    return f'<TH style="padding-left: 0.5em; padding-right: 0.5em;text-align:left;">{s}</TH>'


def TH_R(s=""):
    return f'<TH style="padding-left: 0.5em; padding-right: 0.5em;text-align:right;">{s}</TH>'


def TD(s=""):
    return f'<TD style="padding-left: 0.5em; padding-right: 0.5em">{s}</TD>'


def TD_L(s=""):
    return f'<TD style="padding-left: 0.5em; padding-right: 0.5em;text-align:left;">{s}</TD>'


def TD_R(s=""):
    return f'<TD style="padding-left: 0.5em; padding-right: 0.5em;text-align:right;">{s}</TD>'

# ----- End of configuration items -----


# Load configuration
config = abutils.load_config(CONFIG_FILE)

icinga = Icinga(config=config.icinga)

abutils.Name.default_domain = config.default_domain


def add_kv(msg, key, val):
    if val:
        msg.append(TR)
        msg.append(TD(key))
        msg.append(TD())
        tmp = []
        if isinstance(val, list):
            tmp = val
        else:
            for line in val.strip().split("\\r\\n"):
                tmp.append(line)
        msg.append(TD("<br>".join(tmp)))
        msg.append("</tr>")


def main():
    now = abutils.now()

    # Save CMD line, for debug/troubleshooting
    with open('/tmp/mail_notification.log', 'a', encoding='utf-8') as f:
        for arg in sys.argv:
            if arg and arg[0] == "-":
                f.write(f"{arg} ")
            else:
                f.write(f"'{arg}' ")

        f.write('\n')
        f.write("arguments:\n")
        for ix in range(len(sys.argv)):
            f.write("  %2d %s\n" % (ix, sys.argv[ix]))
        f.write("\n")
    
    # Check if this is a host or service notification
    host = True
    for ix in range(len(sys.argv)):
        if sys.argv[ix] == "--SERVICE":
            sys.argv.pop(ix)
            host = False
            break
    service = not host

    parser = argparse.ArgumentParser()

    # Required paramets
    parser.add_argument('-d', '--LONGDATETIME', required=True)
    parser.add_argument('-l', '--HOSTNAME', required=True)
    parser.add_argument('-n', '--HOSTDISPLAYNAME', required=True)
    parser.add_argument('-r', '--USEREMAIL', required=True)
    parser.add_argument('-t', '--NOTIFICATIONTYPE', required=True)

    # Optional parameters:
    parser.add_argument('-4', '--HOSTADDRESS')
    parser.add_argument('-6', '--HOSTADDRESS6', default="")
    parser.add_argument('-b', '--NOTIFICATIONAUTHORNAME')
    parser.add_argument('-c', '--NOTIFICATIONCOMMENT')
    parser.add_argument('-i', '--ICINGAWEB2URL')
    parser.add_argument('-f', '--MAILFROM', default=config.notify.email.sender)
    parser.add_argument('-v', '--SYSLOG')
    parser.add_argument('--ICINGA2HOST', default=platform.node())

    # Host parameters
    if host:
        parser.add_argument('-o', '--HOSTOUTPUT', required=True)
        parser.add_argument('-s', '--HOSTSTATE', required=True)

    # Service parameters
    if service:
        parser.add_argument('-e', '--SERVICENAME', required=True)
        parser.add_argument('-o', '--SERVICEOUTPUT', required=True)
        parser.add_argument('-s', '--SERVICESTATE', required=True)
        parser.add_argument('-u', '--SERVICEDISPLAYNAME', required=True)

    # Extra optional args
    # parser.add_argument('--pe')

    parser.add_argument("--pe_comments")
    parser.add_argument("--pe_location")
    parser.add_argument("--pe_manufacturer")
    parser.add_argument("--pe_model")
    parser.add_argument("--pe_parents")
    parser.add_argument("--pe_platform")
    parser.add_argument("--pe_role")
    parser.add_argument("--pe_site_name")

    args = parser.parse_args()

    # Build the message's subject
    displayname = abutils.Name(args.HOSTDISPLAYNAME)
    if host:
        subject = f"{args.NOTIFICATIONTYPE}, Host '{displayname.short}' is in state '{args.HOSTSTATE}' !"
    else:
        subject = f"{args.NOTIFICATIONTYPE}, Host '{displayname.short}', Service '{args.SERVICEDISPLAYNAME}' is in state '{args.SERVICESTATE}' !"

    # Build the notification message
    msg = []
    msg.append("<html>")
    msg.append("  <head>")
    msg.append('    <meta content="text/html; charset=utf-8">')
    msg.append("  </head>")
    msg.append("<body>")
    if host:
        msg.append(f"{args.NOTIFICATIONTYPE}, Host <strong>{displayname.short}</strong> is in state <strong>{ args.HOSTSTATE}</strong><br>")
    else:
        msg.append(f"{args.NOTIFICATIONTYPE}, Host <strong>{displayname.short}</strong>, Service <strong>{args.SERVICEDISPLAYNAME}</strong> is in state <strong>{args.SERVICESTATE}</strong><br>")
    msg.append("<br>")

    msg.append(TABLE)

    # Section Alarm
    add_kv(msg, "<strong>Alarm:</strong>", "&nbsp;")
    if host:
        add_kv(msg, "Info", html.escape(args.HOSTOUTPUT))
    else:
        add_kv(msg, "Info", html.escape(args.SERVICEOUTPUT))
    longdatetime = args.LONGDATETIME.split()
    longdatetime = " ".join(longdatetime[:-1])  # remove timezone
    add_kv(msg, "When", longdatetime)
    add_kv(msg, "Notification comment by", args.NOTIFICATIONAUTHORNAME)
    add_kv(msg, "Notification comment", args.NOTIFICATIONCOMMENT)

    # Section Hardware
    if host:
        name = abutils.Name(args.HOSTNAME)
        add_kv(msg, "<strong>Hardware:</strong>", "&nbsp;")
        add_kv(msg, "Host", name.short)
        if args.pe_location:
            add_kv(msg, "Location", args.pe_location)
        if args.pe_site_name:
            add_kv(msg, "Site name", args.pe_site_name)
        if args.pe_parents:
            parents = []
            for parent in args.pe_parents.split(","):
                n = abutils.Name(parent.strip())
                parents.append(n.short)
            add_kv(msg, "Parents", parents)
        if args.pe_role:
            add_kv(msg, "Role", args.pe_role)
        if args.pe_manufacturer:
            add_kv(msg, "Manufacturer", args.pe_manufacturer)
        if args.pe_model:
            add_kv(msg, "Model", args.pe_model)
        add_kv(msg, "IPv4", args.HOSTADDRESS)
        add_kv(msg, "IPv6", args.HOSTADDRESS6)

    # Section Other
    if host:
        add_kv(msg, "<strong>Other:</strong>", "&nbsp;")
        if args.pe_comments:
            tmp = ""
            for comment in args.pe_comments.split('\n'):
                tmp += "%s<br>\n" % html.escape(comment)
            add_kv(msg, "Comments", tmp)
        if args.pe_platform:
            add_kv(msg, "Platform", args.pe_platform)

    if args.ICINGAWEB2URL:
        hostname = urllib.parse.quote(args.HOSTNAME)
        if host:
            val = f'<a href="{args.ICINGAWEB2URL}/monitoring/host/show?host={hostname}">Open host in Icinga</a>'
        else:
            servicename = urllib.parse.quote(args.SERVICENAME)
            val = f'<a href="{args.ICINGAWEB2URL,}/monitoring/list/services?service_problem=1#!/monitoring/service/show?host={hostname}&service={servicename}%s">Open service in Icinga</a>'
        add_kv(msg, 'Link', val)

    msg.append("</table>")

    # Check all hosts not UP, and not acknowledged
    if 1:
        msg.append("<br><strong>Hosts - not Acknowledged</strong><br>")
        try:
            state_down = icinga.get_hosts_down()
            if state_down:
                msg.append("Number of hosts: %d<br>" % len(state_down))
                msg.append("Approximately number of customers down: %d<br>" % (20 * len(state_down)))
                msg.append(TABLE)
                msg.append(TR)
                msg.append(TH_L("Host"))
                msg.append(TH("Time"))
                msg.append(TH("Changed"))
                msg.append(TH_L("Location"))
                msg.append(TH_L("Role"))
                msg.append(TH_L("Manufacturer"))
                msg.append(TH_L("Model"))
                msg.append(TH_L("Notes"))
                msg.append("</tr>")
                for state in state_down:
                    name = abutils.Name(state.name)
                    msg.append(TR)
                    msg.append(TD(name))
                    tmp = now - state.last_hard_state_changed
                    msg.append(TD_R(tmp))

                    msg.append(TD(state.last_hard_state_changed))
                    msg.append(TD(state.pe_location))
                    msg.append(TD(state.pe_role))
                    msg.append(TD(state.pe_manufacturer))
                    msg.append(TD(state.pe_model))
                    msg.append(TD(state.notes))
                    msg.append("</tr>")
                msg.append("</table>")
            else:
                msg.append("None")
        except icinga.Exception as err:
            msg.append("Error getting list of down hosts. Err: %s" % err)

    # Get all services down (not acknowledged) where host is up
    if 1:
        msg.append("<br><strong>Services - not Acknowledged</strong><br>")
        try:
            state_down = icinga.get_services_down()
            if state_down:
                msg.append("Number of services: %d<br>" % len(state_down))
                msg.append(TABLE)
                msg.append(TR)
                msg.append(TH_L("Host"))
                msg.append(TH_L("Service"))
                msg.append(TH("Time"))
                msg.append(TH("Changed"))
                msg.append(TH_L("Output"))
                msg.append(TH_L("Comments"))
                msg.append("</tr>")
                for state in state_down:
                    name = abutils.Name(state.host_name)
                    msg.append(TR)
                    msg.append(TD(name.short))
                    msg.append(TD(state.name))
                    changed = now - state.last_hard_state_changed
                    msg.append(TD_R(changed))
                    msg.append(TD(state.output))
                    msg.append(TD(state.last_hard_state_changed))
                    msg.append(TD(state.notes))
                    msg.append("</tr>")
                msg.append("</table>")
            else:
                msg.append("None")

        except icinga.Exception as err:
            msg.append("Error getting list of down hosts. Err: %s" % err)

    msg.append("</body>")

    # Todo: Check whether verbose mode was enabled and log to syslog.
    if args.SYSLOG == "true":
        pass
        # logger "$PROG sends $SUBJECT => $USEREMAIL"

    # Send the email
    msg_str = "\n".join(msg)
    email = Email()
    if 1:
        email.send(recipient=args.USEREMAIL,
                   sender=args.MAILFROM,
                   subject=subject,
                   msg=msg_str)
    if 0:
        # During development
        email.send(recipient="anders@abundo.se",
                   sender=args.MAILFROM,
                   subject=subject,
                   msg=msg_str)


if __name__ == '__main__':
    try:
        main()
    except:
        # Error in script, send traceback to developer
        abutils.send_traceback()
