#!/usr/bin/env python3
"""
Custom email notification for Icinga2
Uses the same args as the default one shipped with Icinga

Note: Currently not used
"""

# python standard modules
import sys
import platform
import argparse
import urllib.parse
import html

# ----- Start of configuration items -----

CONFIG_FILE = "/etc/factum/factum.yaml"

TABLE = '<table style="border-collapse: collapse;">'
TR = '<tr style="border-top: 1px solid black; vertical-align:top;">'
TD = '<td style="padding-left: 0.5em; padding-right: 0.5em;">'
TD_R = '<td style="padding-left: 0.5em; padding-right: 0.5em;text-align:right;">'

# ----- End of configuration items -----

if "/opt" not in sys.path:
    sys.path.insert(0, "/opt")
try:
    import ablib.utils as abutils
    from ablib.email1 import Email
    from ablib.icinga import Icinga
except:
    print("Error: Cannot import ablib.* check PYTHONPATH")
    sys.exit(1)

try:
    # modules installed with pip
    from orderedattrdict import AttrDict
    import yaml

    # modules, installed with pip, django
    import django
    from django.db import transaction

    # Setup django environment
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

    # Setup django
    django.setup()

    # Import ORM models 
    from base.models import Device, Tag, Parent, Interface, InterfaceTag, Cache

    import lib.base_common as common
except:
    abutils.send_traceback()    # Error in script, send traceback to developer


icinga = Icinga(config=config.icinga)


def add_kv(msg, key, val):
    if val:
        msg.append(TR)
        msg.append(TD + "%s</td>" % key)
        msg.append(TD)
        if isinstance(val, list):
            for line in val:
                msg.append(line + '<br>')
        else:
            for line in val.strip().split("\\r\\n"):
                msg.append(line + '<br>')
        msg.append("</td>")
        msg.append("</tr>")


def main():
    now = abutils.now()

    # Save CMD line, for debug/troubleshooting
    with open('/tmp/mail_notification.log', 'a', encoding='utf-8') as f:
        for arg in sys.argv:
            if arg and arg[0] == "-":
                f.write("%s " % arg)
            else:
                f.write("'%s' " % arg)

        f.write('\n')
        f.write("arguments:\n")
        for ix in range(len(sys.argv)):
            f.write("  %2d %s\n" % (ix, sys.argv[ix]))
        f.write("\n")
    
    # Check name on script, to see if this is a host or service notification
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
    parser.add_argument("--pe_manufacturer")
    parser.add_argument("--pe_model")
    parser.add_argument("--pe_role")
    parser.add_argument("--pe_platform")
    parser.add_argument("--pe_comments")
    parser.add_argument("--pe_site_name")
    parser.add_argument("--pe_parents")
    parser.add_argument("--pe_location")

    args = parser.parse_args()

    ## Build the message's subject
    if host:
        subject = "%s, Host '%s' is in state '%s' !" % (args.NOTIFICATIONTYPE, args.HOSTDISPLAYNAME, args.HOSTSTATE)
    else:
        subject = "%s, Host '%s', Service '%s' is in state '%s' !" % (args.NOTIFICATIONTYPE, args.HOSTDISPLAYNAME, args.SERVICEDISPLAYNAME, args.SERVICESTATE)

    ## Build the notification message
    msg = []
    msg.append("<html>")
    msg.append("  <head>")
    msg.append('    <meta content="text/html; charset=utf-8">')
    msg.append("  </head>")
    msg.append("<body>")
    if host:
        msg.append("%s, Host '%s' is in state <strong>'%s'</strong><br>" % (args.NOTIFICATIONTYPE, args.HOSTDISPLAYNAME, args.HOSTSTATE))
    else:
        msg.append("%s, Host '%s', Service '%s' is in state <strong>'%s'</strong><br>" % (args.NOTIFICATIONTYPE, args.HOSTDISPLAYNAME, args.SERVICEDISPLAYNAME, args.SERVICESTATE))
    msg.append("<br>")

    msg.append(TABLE)

    # Section Alarm
    add_kv(msg, "<strong>Alarm:</strong>", "&nbsp;")
    if host:
        add_kv(msg, "Info", html.escape(args.HOSTOUTPUT))
    else:
        add_kv(msg, "Info", html.escape(args.SERVICEOUTPUT))
    tmp = args.LONGDATETIME.split()
    tmp = " ".join(tmp[:-1])  # remove timezone
    add_kv(msg, "When", tmp)
    if args.pe_location:
        add_kv(msg, "Location", args.pe_location)
    add_kv(msg, "Notification comment by", args.NOTIFICATIONAUTHORNAME)
    add_kv(msg, "Notification comment", args.NOTIFICATIONCOMMENT)

    # Section Hardware
    if host:
        add_kv(msg, "<strong>Hardware:</strong>", "&nbsp;")
        add_kv(msg, "Host", args.HOSTNAME)
        if args.pe_site_name:
            add_kv(msg, "Site name", args.pe_site_name)
        if args.pe_parents:
            add_kv(msg, "Parents", args.pe_parents)
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
            hostname = urllib.parse.quote(args.HOSTNAME)
            val = '<a href="%s/monitoring/host/show?host=%s">Open host in Icinga</a>' % (args.ICINGAWEB2URL, hostname)
        else:
            servicename = urllib.parse.quote(args.SERVICENAME)
            val = '<a href="%s/monitoring/list/services?service_problem=1#!/monitoring/service/show?host=%s&service=%s">Open service in Icinga</a>' % (args.ICINGAWEB2URL, hostname, servicename)
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
                msg.append("  <th>Host</th>")
                msg.append("  <th>Time</th>")
                msg.append("  <th>Changed</th>")
                msg.append("  <th>Location</th>")
                msg.append("  <th>Role</th>")
                msg.append("  <th>Manufacturer</th>")
                msg.append("  <th>Model</th>")
                msg.append("  <th>Notes</th>")
                msg.append("</tr>")
                for state in state_down:
                    msg.append(TR)
                    msg.append("%s%s</td>" % (TD, state.name))
                    tmp = now - state.last_hard_state_changed
                    msg.append("%s%s</td>" % (TD_R, tmp))

                    msg.append("%s%s</td>" % (TD, state.last_hard_state_changed))
                    msg.append("%s%s</td>" % (TD, state.pe_location))
                    msg.append("%s%s</td>" % (TD, state.pe_role))
                    msg.append("%s%s</td>" % (TD, state.pe_manufacturer))
                    msg.append("%s%s</td>" % (TD, state.pe_model))
                    msg.append("%s%s</td>" % (TD, state.notes))
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
                msg.append("  <th>Host</th>")
                msg.append("  <th>Service</th>")
                msg.append("  <th>Time</th>")
                msg.append("  <th>Changed</th>")
                msg.append("  <th>Output</th>")
                msg.append("  <th>Comments</th>")
                msg.append("</tr>")
                for state in state_down:
                    # abutils.pprint(state, "state")
                    msg.append(TR)
                    msg.append("%s%s</td>" % (TD, state.host_name))
                    msg.append("%s%s</td>" % (TD, state.name))
                    tmp = now - state.last_hard_state_changed
                    msg.append("%s%s</td>" % (TD_R, tmp))
                    msg.append("%s%s</td>" % (TD, state.output))
                    msg.append("%s%s</td>" % (TD, state.last_hard_state_changed))
                    msg.append("%s%s</td>" % (TD, state.notes))
                    msg.append("</tr>")
                msg.append("</table>")
            else:
                msg.append("None")

        except icinga.Exception as err:
            msg.append("Error getting list of down hosts. Err: %s" % err)

    msg.append("</body>")

    ## Check whether verbose mode was enabled and log to syslog.
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
