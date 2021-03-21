#!/usr/bin/env python3

"""
- Get list of devices from "Device-API", with their management IP address
- Go through all device configuration files, and parse out interface addresses
- Write records file for dnsmgr and update DNS
"""

# python standard modules
import os
import sys
import ipaddress

if sys.prefix == sys.base_prefix:
    print("Error: You must run this script in a python virtual environment")
    sys.exit(1)

if "/opt" not in sys.path:
    sys.path.insert(0, "/opt")
try:
    import ablib.utils as abutils
    from ablib.devices import Device_Mgr
    from ablib.oxidized import Oxidized_Mgr
except:
    print("Error: Cannot import ablib.* check PYTHONPATH")
    sys.exit(1)

try:
    # modules installed with pip
    from orderedattrdict import AttrDict

    # modules, installed with pip, django
    import django

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


def ifname_to_dnsname(hostname, ifname):
    hostname = hostname.split(".")[0]
    name = f"{hostname}.{ifname}"
    name = name.replace("/", "-").replace(" ", "")
    return name


class Config_Parser:
    """
    Parse a router/switch config
    Try to handle different vendors syntax; cisco, huawei etc
    Extract all interfaces and their IP addresses
    returns an dict, key is interfacename value is {hostname, type, value}
    """
  
    def parse(self, records, hostname, conf):
        ix = 0
        while ix < len(conf):
            line = conf[ix]
            ix += 1
            if not line.startswith("interface "):
                continue
            ifname = line[10:].lower()

            # Shorten interface name if needed, and replace forward slash
            name = ifname_to_dnsname(hostname, ifname)

            # Loop through all config lines for this interface
            while ix < len(conf):
                line = conf[ix].rstrip()
                ix += 1
                if line == "" or line[0] == "!" or line[0] == "#":
                    break   # end if this interface config
                line = line.strip()
                if line.startswith("ip address "):
                    addr = line[11:].split()[0]
                    try:
                        tmp = ipaddress.IPv4Address(addr)
                        record = AttrDict(hostname=name, type="A", value=addr, host=False)
                        if name not in records:
                            records[name] = record
                    except ipaddress.AddressValueError as e:
                        print(f"Error: host '{name}' , incorrect 'ip address' '{addr}', err '{e}'")

                elif line.startswith("ipv4 address "):
                    addr = line[12:].split()[0]
                    try:
                        tmp = ipaddress.IPv4Address(addr)
                        record = AttrDict(hostname=name, type="A", value=addr, host=False)
                        if name not in records:
                            records[name] = record
                    except ipaddress.AddressValueError:
                        print(f"Error: host '{name}' , incorrect 'ipv4 address' '{addr}', err '{e}'")

                elif line.startswith("ipv6 address "):
                    addr = line[13:].split("/")[0]
                    try:
                        tmp = ipaddress.IPv6Address(addr)
                        record = AttrDict(hostname=name, type="AAAA", value=addr, host=False)
                        if name not in records:
                            records[name] = record
                    except ipaddress.AddressValueError:
                        print(f"Error: host '{name}' , incorrect 'ipv6 address' '{addr}', err '{e}'")
                        print("Error: hostname '%s', ipv6_addr '%s' incorrect" % (name, addr))
                
        return records


def add_devices_api_hosts(devices=None, records=None) -> None:
    """
    Go through all devices from Device-API
    - Create record from hostname and management IP address
    - Adds record to records{}
    """
    print("----- Adding devices API host addresses -----")
    for name, device in devices.items():
        if device["primary_ip4"]:
            n = common.Name(name)
            if n.short in records:
                continue
            addr = device["primary_ip4"]["address"].split("/")[0]    # Remove prefixlen
            record = AttrDict(hostname=n.short, type="A", value=addr, host=True)
            records[name] = record


def add_devices_api_interfaces(devices=None, records=None) -> None:
    """
    Go through all devices and interfaces from Device-API
    - Convert interface name to something that can be put in DNS
    - Adds record to records{}
    """
    print("----- Adding Device-API interface addresses -----")
    for hostname, device in devices.items():
        if "interfaces" in device:
            for ifname, interface in device["interfaces"].items():
                if "prefix4" in interface and interface["prefix4"]:
                    name = ifname_to_dnsname(hostname, ifname)
                    addr = interface["prefix4"][0]["address"].split("/")[0]    # Remove prefixlen
                    record = AttrDict(hostname=name, type="A", value=addr, host=False)
                    if name not in records:
                        records[name] = record
                    else:
                        print("Error, name conflict, name %s already exist" % name)


def parse_device_config(oxidized_mgr=None, devices=None, records=None) -> None:
    """
    Go through all devices from Device-API
    - fetch last running-configuration file
    - parse each config file for interface addresses
    - Convert interface name to something that can be put in DNS
    - Adds record to records{}
    """
    print("----- Parsing all devices configuration, searching for interface IP addresses -----")
    parser = Config_Parser()
    for hostname, device in devices.items():
        if "backup_oxidized" in device and device["backup_oxidized"] == False:
            # print("  Ignoring backup_oxidized' is False, hostname '%s'" % hostname)
            continue
        if "platform" in device and device["platform"] in config.sync_dns.ignore_platforms:
            # print("  Ignoring platform '%s', hostname '%s'" % (device["platform"], hostname))
            continue
        if "model" in device and device["model"] in config.sync_dns.ignore_models:
            # print("  Ignoring model '%s', hostname '%s'" % (device["model"], hostname))
            continue

        device_conf = oxidized_mgr.get_device_config(hostname)
        if device_conf is not None:
            tmp_records = parser.parse(records, hostname, device_conf.split("\n"))
        else:
            print("Warning: Missing configuration backup for %s" % hostname)


def write_dnsmgr_records(devices, records) -> None:
    """
    Write a DnsMgr records file, and ask DnsMgr to update nameserver
    """
    print("----- Writing dnsmgr records -----")
    addr4 = {}

    with open(config.sync_dns.dest_record_file, "w") as f:
        f.write(";\n")
        f.write("; Autogenerated from devices management address\n")
        f.write(";\n")
        f.write("$DOMAIN %s\n" % config.default_domain)

        # Write forward entries, hostname
        f.write(";\n")
        f.write("; Forward entries, hostname\n")
        f.write(";\n")
        f.write("\n")
        f.write("$FORWARD 1\n")
        f.write("$REVERSE 1\n")
        f.write("\n")
        for record in records.values():
            if record.host:
                addr4[record.value] = 1
                f.write("%-40s  %-4s   %s\n" % (record.hostname, record.type, record.value))

        # Write forward entries, names that should not have reverse DNS
        # typically loopbacks, which already have hostname entry
        f.write(";\n")
        f.write("; Forward entries, interfaces\n")
        f.write(";\n")
        f.write("\n")
        f.write("$FORWARD 1\n")
        f.write("$REVERSE 0\n")
        f.write("\n")
        for record in records.values():
            if not record.host:
                if record.value in addr4:
                    f.write("%-40s  %-4s   %s\n" % (record.hostname, record.type, record.value))

        # Write reverse entries
        f.write(";\n")
        f.write("; Reverse entries, interfaces\n")
        f.write(";\n")
        f.write("\n")
        f.write("$FORWARD 1\n")
        f.write("$REVERSE 1\n")
        f.write("\n")
        f.write(";\n")
        for record in records.values():
            if not record.host:
                if record.value not in addr4:
                    f.write("%-40s  %-4s   %s\n" % (record.hostname, record.type, record.value))

    print("----- Request dnsmgr to update DNS/bind -----")
    os.system("/opt/dnsmgr/dnsmgr.py update --loglevel warning")


def main() -> None:
    # Use systems ca certificates
    # os.environ["REQUESTS_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"

    records = AttrDict()

    oxidized_mgr = Oxidized_Mgr(config=config.oxidized)

    print("----- Get devices from Device-API -----")
    device_mgr = Device_Mgr(config=config.device)
    devices = device_mgr.get_devices()
    
    add_devices_api_hosts(devices=devices, records=records)
    add_devices_api_interfaces(devices=devices, records=records)
    parse_device_config(oxidized_mgr=oxidized_mgr, devices=devices, records=records)
    write_dnsmgr_records(devices, records)


if __name__ == "__main__":
    try:
        main()
    except:
        # Error in script, send traceback to developer
        abutils.send_traceback()
