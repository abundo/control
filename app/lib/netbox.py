#!/usr/bin/env python3
"""
Common functions for Netbox
"""

# python standard modules
from typing import List, Dict

# Modules installed with pip
from orderedattrdict import AttrDict
import pynetbox
from django.utils.text import slugify

# Assumes PYTHONPATH is set
import ablib.utils as abutils
import lib.base_common as common


class NetboxException(Exception):
    pass


class NetBox_Cache:
    """
    Fetch devices from netbox.
    Cache result, key is slug name
    """
    def __init__(self, netbox=None, netbox_obj=None):
        self.netbox = netbox
        self.netbox_obj = netbox_obj
        self.items = {}
    
    def get(self, name: str):
        """
        """
        slug = slugify(name.lower())
        try:
            return self.items[slug]
        except KeyError:
            pass

        try:
            item = self.netbox_obj.get(slug=slug)
            self.items[slug] = item     # Store in cache
            return item
        except pynetbox.core.query.RequestError:
            return None


class Netbox:
    """
    """
    exception = NetboxException

    def __init__(self, config):
        self.config = config

        self.devices = AttrDict()
        self.devices_oid = AttrDict()

        self.netbox = pynetbox.api(
            url=self.config.netbox.url,
            token=self.config.netbox.token,
            threading=False,
        )
        
        self.device_manufacturer_mgr = NetBox_Cache(netbox=self.netbox, netbox_obj=self.netbox.dcim.manufacturers)
        self.device_platform_mgr = NetBox_Cache(netbox=self.netbox, netbox_obj=self.netbox.dcim.platforms)
        self.device_role_mgr = NetBox_Cache(netbox=self.netbox, netbox_obj=self.netbox.dcim.device_roles)
        self.site_mgr = NetBox_Cache(netbox=self.netbox, netbox_obj=self.netbox.dcim.sites)
        self.tags_mgr = NetBox_Cache(netbox=self.netbox, netbox_obj=self.netbox.extras.tags)

        self.device_type_mgr = NetBox_Cache(netbox=self.netbox, netbox_obj=self.netbox.dcim.device_types)
        self.interface_templates_mgr = NetBox_Cache(netbox=self.netbox, netbox_obj=self.netbox.dcim.interface_templates)

    def tags_to_dict(self, tags: List) -> AttrDict:
        res = AttrDict()
        for tag in tags:
            res[tag.name] = tag.id
        return res

    def parse_api_data(self, addresses=None, devices=None, interfaces=None, vm: bool = False, filter_tag: str = None) -> AttrDict:
        """
        Go through data from netbox API. Handles both device and virtual-machines
        Return dict with devices, key is device-name, value is data
        """
        devices_out = AttrDict()

        # Build dict to quickly map from device.id to device
        devices_id = {}
        for name, device in devices.items():
            devices_id[device.id] = device
            device.interfaces = AttrDict()   # Key interface-name, value Interface

        # Build dict to quickly map from interface.id to interface
        interfaces_id = {}
        for ifid, interface in interfaces.items():
            interface.addresses = []

            interfaces_id[ifid] = interface
            if vm:
                device_id = interface.virtual_machine.id
            else:
                device_id = interface.device.id
            device = devices_id[device_id]
            device.interfaces[interface.name] = interface

        # Get netbox interface ip-addresses, add to interfaces
        for id_, address in addresses.items():
            if address.assigned_object:
                ifname = address.assigned_object.name
                ifid = address.assigned_object_id
                # print("ifname", ifname, "ifid", ifid)
                interface = interfaces_id.get(ifid, None)
                if interface:
                    interface.addresses.append(address)

        for name, device in devices.items():
            if not name:
                continue  # No name, ignore device
            # Todo, verify name for valid format/characters
            n = common.Name(name)

            # ----- Device -----
            d = AttrDict()
            d.id = device.id
            d.name = n.long
            d.tags = self.tags_to_dict(device.tags)
            
            if filter_tag and filter_tag not in d.tags:
                continue

            try:
                d.manufacturer = device.device_type.manufacturer.name
            except (AttributeError, NameError):
                d.manufacturer = ""

            try:
                d.model = device.device_type.model
            except (AttributeError, NameError):
                d.model = ""

            d.comments = device.comments

            # Try old name, netbox is (slowly) changing device_role -> role
            try:
                d.role = device.device_role.name
            except (AttributeError, NameError):
                try:
                    d.role = device.role.name
                except (AttributeError, NameError):
                    d.role = ""

            try:
                d.site_name = device.site.name
                if d.site_name == "Default":
                    d.site_name = ""
            except (AttributeError, NameError):
                d.site_name = ""
            
            try:
                d.platform = device.platform.name
            except (AttributeError, NameError):
                d.platform = ""

            try:
                d.primary_ip4 = AttrDict(address=device.primary_ip4.address, id=device.primary_ip4.id)
            except (AttributeError, NameError, KeyError, TypeError):
                d.primary_ip4 = ""

            try:
                d.primary_ip6 = AttrDict(address=device.primary_ip6.address, id=device.primary_ip6.id)
            except (AttributeError, NameError, KeyError, TypeError):
                d.primary_ip6 = ""
           
            d.enabled = True
            try:
                label = device.status.label
                if label != "Active":
                    d.enabled = False
            except (AttributeError, NameError):
                pass

            custom_fields = device.custom_fields    # less typing
            try:
                d.location = custom_fields.get("location", None)
                if d.location is None:
                    d.location = ""
            except (AttributeError, NameError, TypeError):
                d.location = ""

            try:
                # We only get the string before the first space
                # Example
                #     sla1 (mon,tue,wed,thu,fri 07-16)
                # results in
                #     sla1
                # tmp = custom_fields["alarm_timeperiod"]["label"].split()
                tmp = custom_fields["alarm_timeperiod"].split()
                if tmp:
                    tmp = tmp[0]
                else:
                    tmp = ""
                d.alarm_timeperiod = tmp
            except (KeyError, AttributeError, NameError, TypeError):
                d.alarm_timeperiod = ""

            try:
                # d.alarm_destination = custom_fields["alarm_destination"]["label"]
                d.alarm_destination = custom_fields["alarm_destination"]
            except (KeyError, AttributeError, NameError, TypeError):
                d.alarm_destination = []

            try:
                d.alarm_interfaces = custom_fields.get("alarm_interfaces", None)
                if d.alarm_interfaces is None:
                    d.alarm_interfaces = False
            except (AttributeError, NameError):
                d.alarm_interfaces = False

            try:
                # tmp = custom_fields["connection_method"]["label"]
                tmp = custom_fields.get("connection_method", "")
                d.connection_method = tmp
            except (TypeError, AttributeError, NameError):
                d.connection_method = ""

            try:
                d.monitor_grafana = custom_fields.get("monitor_grafana", None)
                if d.monitor_grafana is None:
                    d.monitor_grafana = False
            except (AttributeError, NameError, KeyError):
                d.monitor_grafana = False

            try:
                d.monitor_icinga = custom_fields.get("monitor_icinga", None)
                if d.monitor_icinga is None:
                    d.monitor_icinga = True
            except (AttributeError, NameError):
                d.monitor_icinga = False

            try:
                d.monitor_librenms = custom_fields.get("monitor_librenms", None)
                if d.monitor_librenms is None:
                    d.monitor_librenms = True
            except (AttributeError, NameError):
                d.monitor_librenms = False

            try:
                d.backup_oxidized = custom_fields.get("backup_oxidized", None)
                if d.backup_oxidized is None:
                    d.backup_oxidized = False
            except (AttributeError, NameError):
                d.backup_oxidized = False

            try:
                d.becs_oid = custom_fields.get("becs_oid", None)
            except (AttributeError, NameError):
                d.becs_oid = None

            # ----- Parent -----
            try:
                parents = custom_fields.get("parents", "")
                parents = common.commastr_to_list(parents, add_domain=config.default_domain)
            except (AttributeError, NameError):
                parents = []
            d.parents = parents

            # ----- Interfaces, addresses -----
            d.interfaces = AttrDict()
            d.interfaces_oid = AttrDict()
            for ifname, interface in device.interfaces.items():
                # abutils.pprint(interface, "interface")
                prefix4 = []
                prefix6 = []
                for address in interface.addresses:
                    # abutils.pprint(address, "address")
                    addr = AttrDict(
                        address=address.address,
                        id=address.id,
                        becs_oid=address.custom_fields.get("becs_oid", None),
                    )
                    if ":" in address.address:
                        prefix6.append(addr)
                    else:
                        prefix4.append(addr)

                becs_oid = None
                if not vm and interface.label.startswith("becs_oid="):
                    try:
                        becs_oid = int(interface.label[9:])
                    except ValueError:
                        pass
                try:
                    type_value = interface.type.value
                except AttributeError:
                    type_value = ""

                i = AttrDict(
                    id=interface.id,
                    becs_oid=becs_oid,
                    enabled=interface.enabled,
                    name=ifname,
                    prefix4=prefix4,
                    prefix6=prefix6,
                    role="",
                    tags=self.tags_to_dict(interface.tags),
                    type_value=type_value,
                )
                d.interfaces[ifname] = i
                if becs_oid:
                    d.interfaces_oid[becs_oid] = i

            devices_out[n.long] = d

        return devices_out

    def get_virtual_machines(self, n: common.Name) -> AttrDict:
        print("----- Netbox, Get virtual machines -----")
        if n.long:
            data = self.netbox.virtualization.virtual_machines.filter(name=n)
        else:
            data = self.netbox.virtualization.virtual_machines.all()

        vmdevices = AttrDict()
        for d in data:
            name = common.Name(d.name)
            vmdevices[name.long] = d
        print(f"Found {len(vmdevices)} virtual machines")
        return vmdevices

    def get_virtual_machine_interfaces(self, n: common.Name, vmdevices: AttrDict) -> AttrDict:
        print("----- NetBox, get virtual machine interfaces -----")
        interfaces = AttrDict()
        if n.long:
            if len(vmdevices):
                vmdevice = vmdevices[n.long]
                data = self.netbox.virtualization.interfaces.filter(virtual_machine_id=vmdevice.id)
            else:
                data = []
        else:
            data = self.netbox.virtualization.interfaces.filter(exclude="config_context")

        for d in data:
            interfaces[d.id] = d
        print(f"Found {len(interfaces)} virtual machine interfaces")
        return interfaces

    def get_devices_(self, n: common.Name) -> AttrDict:
        print("----- NetBox, get devices -----")
        if n.long:
            data = self.netbox.dcim.devices.filter(name=n)
        else:
            data = self.netbox.dcim.devices.filter(exclude="config_context")

        devices = AttrDict()
        for d in data:
            name = common.Name(d.name)
            devices[name.long] = d
        print(f"Found {len(devices)} devices")
        return devices

    def get_device_interfaces(self, n: common.Name, devices) -> AttrDict:
        print("----- Netbox, get device interfaces -----")
        if n.long:
            device = devices[n.long]
            data = self.netbox.dcim.interfaces.filter(device_id=device.id, exclude="config_context")
        else:
            data = self.netbox.dcim.interfaces.all()

        interfaces = AttrDict()
        for d in data:
            interfaces[d.id] = d
        print(f"Found {len(interfaces)} interfaces")
        return interfaces

    def get_addresses(self, n: common.Name) -> AttrDict:
        print("----- NetBox, get addresses -----")
        if n.long:
            data = self.netbox.ipam.ip_addresses.filter(device=n, exclude="config_context")
        else:
            data = self.netbox.ipam.ip_addresses.all()

        addresses = AttrDict()
        for d in data:
            addresses[d.id] = d
        print(f"Found {len(addresses)} ip-addresses")
        return addresses

    def get_devices(self, name: str = None, refresh: bool = False, filter_tag: str = None):
        """
        Get one or all devices and virtual machines from netbox
        Include interfaces and ipaddresses
        """
        n = common.Name(name)

        # Get all data
        self.devices = AttrDict()
        try:
            vmdevices = self.get_virtual_machines(n)
            vminterfaces = self.get_virtual_machine_interfaces(n, vmdevices)
            devices = self.get_devices_(n)
            interfaces = self.get_device_interfaces(n, devices)
            addresses = self.get_addresses(n)
        except pynetbox.RequestError as err:
            print(err.error)
            print(err.req)
            raise NetboxException(err.error)

        # Parse responses from Netbox, virtual machines
        if len(vmdevices):
            print("----- Netbox, parse virtual machines -----")
            d: AttrDict = self.parse_api_data(
                addresses=addresses,
                devices=vmdevices,
                interfaces=vminterfaces,
                vm=True,
                filter_tag=filter_tag,
            )
            self.devices.update(d)
            print(f"Parsed {len(d)} virtual machines")

        # Parse responses from Netbox, devices
        if len(devices):
            print("----- Netbox, parse devices -----")
            d: AttrDict = self.parse_api_data(
                addresses=addresses,
                devices=devices,
                interfaces=interfaces,
                vm=False,
                filter_tag=filter_tag
            )
            self.devices.update(d)
            print(f"Parsed {len(d)} devices")

        return self.devices

    def get_device(self, name: str = None, refresh: bool = False) -> AttrDict:
        devices = self.get_devices(name=name, refresh=refresh)
        if devices:
            for name, device in devices.items():
                return device
        return None

    def create_device_becs(self, name: str = None, becs_device=None, tags: List = None):
        """
        Create a device in netbox, based on a device in becs
        assumes there is a "device template" for the device in netbox
        todo: if no device template, send error?
        Note: tags must exist in Netbox
        Note: tags must be the slug name
        Returns True if ok
        """
        n = common.Name(name)

        # print(f"Verify that device {n} can be created NetBox")
        if tags is None:
            tags = []
        site_name: str = "Default"
        site = self.site_mgr.get(site_name)
        if not site:
            raise self.exception(f"Error: Cannot find site '{site}' in Netbox")

        device_manufacturer_name: str = becs_device["manufacturer"]
        device_manufacturer = self.device_manufacturer_mgr.get(device_manufacturer_name)
        if not device_manufacturer:
            raise self.exception(f"Error: Cannot find manufacturer '{device_manufacturer_name}' in Netbox")

        device_type_name: str = becs_device["model"]    # ASR6026, ASR8048
        device_type = self.device_type_mgr.get(device_type_name)
        if not device_type:
            raise self.exception(f"Error: Cannot find device_type '{device_type_name}' in Netbox")

        device_role_name: str = "access-nod"
        device_role = self.device_role_mgr.get(device_role_name)
        if not device_role:
            raise self.exception(f"Error: Cannot find device_role '{device_role_name}' in Netbox")

        device_platform_name: str = "ibos"
        device_platform = self.device_platform_mgr.get(device_platform_name)
        if not device_platform:
            raise self.exception(f"  Error: Cannot find device_platform '{device_platform_name}' in Netbox")

        try:
            # Todo: parent
            tags_id = []
            for t in tags:
                tags_id.append(self.tags_mgr.get(t).id)
            p: AttrDict = AttrDict(
                name=n.short,
                device_type=device_type.id,
                device_role=device_role.id,
                site=site.id,
                platform=device_platform.id,
                tags=tags_id,
                enabled=becs_device.enabled,
                custom_fields=dict(
                    becs_oid=becs_device.oid
                ),
            )
            r = self.netbox.dcim.devices.create(p)

        except pynetbox.core.query.RequestError as e:
            raise self.exception(e)

        return r

    def update_device(self, device, changes: Dict):
        """
        Update device
        """
        d = self.netbox.dcim.devices.get(device.id)
        return d.update(changes)

    def delete_device(self, name: str = None, device_id: int = None):
        """
        Delete a device in Netbox
        """
        try:
            if device_id:
                device = self.netbox.dcim.devices.get(device_id)
            else:
                n = common.Name(name)
                device = self.netbox.dcim.devices.get(name=n)
        except pynetbox.core.query.RequestError as e:
            raise self.exception(e)

        if device:
            r = device.delete()
        else:
            r = False
        return r

    def create_interface_becs(self, name: str = None, type_: str = None, becs_interface=None, tags: List = None,
                              device_id: int = None, description: str = ""):
        """
        Create an interface
        """
        if tags is None:
            tags = []

        label: str = f"becs_oid={becs_interface.oid}"
        tags_id: List = []
        abutils.pprint(tags, "----- tags -----")
        for t in tags:
            tags_id.append(self.tags_mgr.get(t).id)
        p: AttrDict = AttrDict(
            device=device_id,
            name=name,
            label=label,
            tags=tags_id,
            type=type_,
            enabled=becs_interface.enabled,
        )
        try:
            r = self.netbox.dcim.interfaces.create(p)
            return r
        except pynetbox.core.query.RequestError as e:
            print(e)
            return False

    def update_interface(self, interface_id: int, changes: Dict):
        """
        Update interface
        """
        try:
            i = self.netbox.dcim.interfaces.get(interface_id)
            return i.update(changes)
        except pynetbox.core.query.RequestError as e:
            raise self.exception(e)

    def delete_interface(self, interface_id: int):
        """
        Delete an interface
        """
        try:
            interface = self.netbox.dcim.interfaces.get(interface_id)
            if interface:
                r = interface.delete()
            else:
                r = False
            return r
        except pynetbox.core.query.RequestError as e:
            raise self.exception(e)

    def create_interface_ipaddress(self, interface=None, address=None, status="active", becs_oid=None):
        """
        Create an ip-address on an interface
        """
        p = dict(
            assigned_object_type="dcim.interface",
            assigned_object_id=interface.id,
            address=address,
            status=status,
            custom_fields=dict(becs_oid=becs_oid),
        )
        try:
            r = self.netbox.ipam.ip_addresses.create(p)
            return r
        except pynetbox.core.query.RequestError:
            return None

    def delete_ipaddress(self, address_id: int = None):
        try:
            obj = self.netbox.ipam.ip_addresses.get(address_id)
            r = obj.delete()
            return r
        except pynetbox.core.query.RequestError:
            return None

    def get_device_type(self, manufacturer=None, model=None):
        device_type = self.netbox.dcim.device_types.get(manufacturer=manufacturer, model=model)
        interfaces = self.netbox.dcim.interface_templates.filter(devicetype_id=device_type.id)
        device_type.interfaces = AttrDict()
        for interface in interfaces:
            del interface._init_cache
            del interface._full_cache
            device_type.interfaces[interface.name] = interface
        return device_type


if __name__ == "__main__":
    """
    Function test
    """
    import argparse
    import builtins

    builtins.config = abutils.yaml_load("/etc/abcontrol/abcontrol.yaml")

    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=[
        "get_devices", 
        "get_device", 
        "create_device",
        "update_device",
        "delete_device",
        "get_device_type",
    ])
    parser.add_argument("-n", "--name")
    parser.add_argument("--manufacturer")
    parser.add_argument("--model")
    parser.add_argument(
        "--refresh",
        default=False, action="store_true"
    )
    args = parser.parse_args()

    netbox = Netbox(config=config)

    if args.cmd == "get_devices":
        if args.name:
            devices = netbox.get_devices(refresh=args.refresh, name=args.name)
            if len(devices):
                for device in devices.values():
                    abutils.pprint(device)
        else:
            devices = netbox.get_devices(refresh=args.refresh)
            if devices:
                print(f"Got {len(devices)} devices")
            else:
                print("No devices")

    elif args.cmd == "get_device":
        device = netbox.get_device(refresh=args.refresh, name=args.name)
        abutils.pprint(device)

    elif args.cmd == "create_device":
        raise RuntimeError("Not implemented")

    elif args.cmd == "update_device":
        raise RuntimeError("Not implemented")

    elif args.cmd == "delete_device":
        raise RuntimeError("Not implemented")

    elif args.cmd == "get_device_type":
        device_type = netbox.get_device_type(manufacturer=args.manufacturer, model=args.model)
        abutils.pprint(device_type)
        for name, interface in device_type.interfaces.items():
            abutils.pprint(interface)

    else:
        print("Internal error, unknown command", args.cmd)
