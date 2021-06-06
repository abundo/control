#!/usr/bin/env python3
"""
Fetch all devices from BECS
Sync all Netbox devices with BECS devices
  creating, updating and deleting device,interfaces and addresses as necessary

All devices created in Netbox, gets a tag "BECS". This script assumes this tag
exists in Netbox

Todo: Deleted devices are NOT immediately deleted, they get a tentative deletion date. This
avoids loosing information if a device is incorrectly deleted.
"""

# python standard modules
import os
import sys
import gzip
import pickle
import argparse

ignore_interfaces = {
    "ethernet0": 1,
}

BECS_CACHE_FILE = "/var/lib/abcontrol/sync-netbox-becs-cache.json.gz"
NETBOX_CACHE_FILE = "/var/lib/abcontrol/netbox-cache.json.gz"

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
    from orderedattrdict import AttrDict

    # modules, installed with pip, django
    import django

    # Setup django environment
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

    # Setup django
    django.setup()

    # import ORM models
    from base.models import Device, Tag, Parent, Interface, InterfaceTag, Cache

    import lib.base_common as common
    from lib.netbox import Netbox
    from lib.becs import BECS

except:
    abutils.send_traceback()    # Error in script, send traceback to developer


class Errors:
    def __init__(self):
        self.errors = []
    
    def add(self, name: str = "", msg: str = ""):
        """
        """
        print(name, msg)
        self.errors.append(AttrDict(name=name, msg=msg))


errors = Errors()


class Netbox_Device_Cache:
    """
    Manage a local cache of netbox devices
    Mosty used during development, to speed up/avoid unneccessary calls to netbox API
    """
    def __init__(self, filename: str):
        self.filename = filename
        self.devices = AttrDict()
        self.devices_oid = AttrDict()

    def build_oid(self):
        self.devices_oid = AttrDict()
        for device in self.devices.values():
            becs_oid = device.get("becs_oid", None)
            if becs_oid:
                self.devices_oid[becs_oid] = device
            else:
                print(f"Device {device.name} has no becs_oid")
        print()

    def get_devices(self, refresh: bool = False):
        if self.devices and not refresh:
            return self.devices
        print(f"----- Netbox, Load devices from local cache '{self.filename}' -----")
        with gzip.open(self.filename, "rb") as f:
            self.devices = pickle.load(f)
        if len(self.devices) < 2:
            raise RuntimeError("Error: Loaded less than one device from file cache")
        self.build_oid()
        return self.devices, self.devices_oid

    def get_device(self, name: str):
        if not self.devices:
            self.get_devices()
        try:
            return self.devices[name]
        except KeyError:
            return None

    def update_devices(self, devices=None):
        print(f"----- Netbox, store devices in local cache '{self.filename}' -----")
        if devices:
            self.devices = devices
        if len(self.devices) < 2:
            raise RuntimeError("Error: trying to update device file cache with less than 2 entries")
        self.build_oid()
        with gzip.open(NETBOX_CACHE_FILE, "wb") as f:
            pickle.dump(self.devices, f)

    def update_device(self, device):
        """
        Update a single device in the cache
        """
        if not self.devices:
            self.get_devices()
        name = common.Name(device.name)
        self.devices[name.long] = device
        if device.becs_oid:
            self.devices[device.becs_oid] = device
        self.update_devices()

    def delete_device(self, device):
        if not self.devices:
            self.get_devices()
        name = common.Name(device.name)
        del self.devices[name.long]
        self.update_devices()


class Becs:
    """
    Manage devices from BECS
    Maps from BECS elements to devices in NetBox style
    """
    def __init__(self, config=None):
        self.config = config

        self.devices = AttrDict()
        self.devices_oid = AttrDict()
        self.becs = BECS(config=self.config)

    def build_devices_oid(self) -> None:
        self.devices_oid = AttrDict()
        for device in self.devices.values():
            self.devices_oid[device.oid] = device

    def get_devices(self, name=None, refresh=False):
        """
        Get one or all devices from becs
        Note: All devices are always fetched from BECS, even if only one device is
              asked for. This due to finding out parents etc in the becs tree
        """
        name = common.Name(name)
        if not os.path.exists(BECS_CACHE_FILE):
            refresh = True
        if not refresh:
            print("----- BECS, Get data using local cache-----")
            with gzip.open(BECS_CACHE_FILE, "rb") as f:
                self.devices = pickle.load(f)
            self.build_devices_oid()
            return self.devices, self.devices_oid

        self.devices = AttrDict()
        self.devices_oid = AttrDict()

        elements = self.becs.get_elements(refresh=refresh)
        for oid, element in elements.items():
            n = common.Name(element.name)
            flags = element.get("flags", "")
            # todo
            # if flags is None:
            #     enabled = True   # Default
            # else:
            #     enabled = flags.find("disable") < 0
            enabled = True

            model = ""
            if "parameters" in element:
                for p in element.parameters:
                    if p.name == "model":
                        try:
                            model = list(p.values())[1][0].value
                        except KeyError:
                            pass
                        break

            # ASR5k does not support SSH
            if model.startswith("ASR5"):
                connection_method = "telnet"
            else:
                connection_method = "ssh"

            # Get interfaces and their IP addresses for this element-attach
            interfaces = self.becs.get_interfaces(oid)

            parents = element._parents
            if parents is None:
                parents = ""
            device = AttrDict(
                oid=oid,
                name=n.long,
                manufacturer="Waystream",
                model=model,
                comments="",
                role=element.role,
                site_name="",
                platform=element.elementtype,
                enabled=enabled,
                alarm_timeperiod=element._alarm_timeperiod,
                alarm_destination=element._alarm_destination,
                alarm_interfaces=False,
                connection_method=connection_method,
                monitor_grafana=False,
                monitor_icinga=True,
                monitor_librenms=True,
                backup_oxidized=False,
                parents=common.commastr_to_list(parents, add_domain=config.default_domain),
                interfaces=AttrDict(),
                interfaces_oid=AttrDict(),
            )

            for ifname, interface in interfaces.items():
                prefix4 = interface.get("prefix4", None)
                prefix6 = interface.get("prefix6", None)
                i = AttrDict(
                    oid=interface.oid,
                    name=ifname,
                    role=interface.role,
                    prefix4=prefix4,
                    prefix6=prefix6,
                    enabled=interface.enabled,
                )
                device.interfaces[ifname] = i
                device.interfaces_oid[interface.oid] = i

            self.devices[n.long] = device

        self.build_devices_oid()
        print("----- BECS, store data in local cache -----")
        with gzip.open(BECS_CACHE_FILE, "wb") as f:
            pickle.dump(self.devices, f)

        return self.devices, self.devices_oid


class Sync:

    def __init__(self):
        self.netbox = None
        self.becs = None
        self.devices = AttrDict()
        self.devices_oid = AttrDict()
        self.becs_devices = AttrDict()
        self.becs_devices_oid = AttrDict()
        self.cache = Netbox_Device_Cache(NETBOX_CACHE_FILE)
        self.device_type_cache = AttrDict()

    def iter_devices(self):
        for oid, device in self.devices_oid.items():
            becs_device = self.becs.devices_oid.get(oid, None)
            yield oid, device, becs_device

    def refresh_device(self, device=None):
        """
        Refresh the in-memory copy of a device
        Used when netbox has been modifed
        """
        print(f"Refresh in-memory copy of device '{device.name}' from Netbox")
        tmp_device = self.netbox.get_device(name=device.name, refresh=True)
        try:
            if tmp_device:
                self.devices[tmp_device.name] = device
                self.devices_oid[tmp_device.becs_oid] = device
                self.cache.update_device(tmp_device)
            else:
                del self.devices[device.name]
                del self.devices_oid[device.becs_oid]
                self.cache.delete_device(device)
        except KeyError:
            pass

    def save_device_updates(self, device=None, device_update=None, custom_fields=None):
        """
        """
        if device_update or custom_fields:
            if custom_fields:
                if device_update is None:
                    device_update = AttrDict()
                device_update.custom_fields = custom_fields
            print(f"Updating device {device.name}")
            abutils.pprint(device_update, "----- device_update ----")
            r = self.netbox.update_device(device, device_update)
            return r
        return None
    
    def get_device_type(self, model):
        device_type = self.device_type_cache.get(model)
        if device_type is None:
            device_type = self.netbox.get_device_type(
                manufacturer="waystream",   # slug
                model=model,
            )
            if device_type:
                self.device_type_cache[model] = device_type
            else:
                return None
        return device_type

    def sync_devices(self, devices=None, becs_devices=None):
        """
        Sync devices
        Create and/or deletet elements in Netbox based on BECS
        """
        devices_delete = []
        devices_set_oid = []

        # Calculate
        #  Devices that should be deleted in netbox (does not exist in BECS)
        #  Devices in netbox with missing becs_oid (device exist in BECS with same name)
        for device in self.devices.values():
            if device.becs_oid:
                if device.becs_oid not in self.becs_devices_oid:
                    devices_delete.append(device)
            else:
                becs_device = self.becs_devices.get(device.name, None)
                if becs_device:
                    devices_set_oid.append(AttrDict(device=device, becs_oid=becs_device.oid))
                else:
                    devices_delete.append(device)

        # Delete devices in netbox that does not exist in BECS
        for device in devices_delete:
            print("Deleting device in Netbox:", device.name)
            try:
                r = self.netbox.delete_device(device_id=device.id)
                if r:
                    self.refresh_device(device=device)
            except self.netbox.exception as err:
                errors.add(f"Deleting device '{device.name}' in Netbox", err)

        # Create devices missing in netbox
        for becs_device in self.becs_devices.values():
            if becs_device.oid not in self.devices_oid:
                # becs device does not exist in netbox, check if name exist
                if becs_device.name in self.devices:
                    # device exist, but has no OID
                    devices_set_oid.append(AttrDict(device=device, becs_oid=becs_device.oid))
                else:
                    print("Creating device in Netbox:", becs_device.name)
                    try:
                        device = self.netbox.create_device_becs(
                            name=becs_device.name,
                            becs_device=becs_device,
                            tags=["becs"]
                        )
                        if device is not None:
                            self.refresh_device(device=device)
                    except self.netbox.exception as err:
                        errors.add(f"Creating device '{device.name}' in Netbox", err)

        # Set becs_oid on devices that lacks it
        for d in devices_set_oid:
            device = d.device
            becs_oid = d.becs_oid
            print(f"Setting becs_oid on device {device.name} to {becs_oid}")
            device_update = AttrDict()
            custom_fields = AttrDict(becs_oid=becs_oid)
            r = self.save_device_updates(device=device, device_update=device_update, custom_fields=custom_fields)
            if r:
                self.refresh_device(device=device)
            else:
                print("  Error updating", r)

        # for oid in device_create:
        #     becs_device = self.devices_oid[oid]
        #     print("Creating device in Netbox:", becs_device.name)
        #     try:
        #         device = self.netbox.create_device_becs(
        #             name=becs_device.name,
        #             becs_device=becs_device,
        #             tags=["becs"]
        #         )
        #         if device is not None:
        #             self.refresh_device(device=device)
        #     except self.netbox.exception as err:
        #         errors.add(f"Creating device '{device.name}' in Netbox", err)

    def sync_device_settings(self, device=None, becs_device=None):
        """
        Sync settings on element in becs with settings on device in Netbox
        """
        device_update = AttrDict()
        custom_fields = AttrDict()
        device_type = self.get_device_type(becs_device.model)

        if device.enabled != becs_device.enabled:
            device_update.enabled = becs_device.enabled

        if device.parents != becs_device.parents:
            custom_fields.parents = ",".join(becs_device.parents)

        # use device_template values if None

        if not device.alarm_destination:
            custom_fields.alarm_destination = device_type.custom_fields["alarm_destination"]

        if device.alarm_interfaces is None:
            custom_fields.alarm_interfaces = device_type.custom_fields["alarm_interfaces"]

        if not device.alarm_timeperiod:
            custom_fields.alarm_timeperiod = device_type.custom_fields["alarm_timeperiod"]

#        if device.backup_oxidized is None:
        if device.backup_oxidized != device_type.custom_fields["backup_oxidized"]:
            custom_fields.backup_oxidized = device_type.custom_fields["backup_oxidized"]

        if not device.connection_method:
            custom_fields.connection_method = device_type.custom_fields["connection_method"]

        if device.monitor_grafana is None:
            custom_fields.monitor_grafana = device_type.custom_fields["monitor_grafana"]

        if device.monitor_icinga is None:
            custom_fields.monitor_icinga = device_type.custom_fields["monitor_icinga"]

        if device.monitor_librenms is None:
            custom_fields.monitor_librenms = device_type.custom_fields["monitor_librenms"]

        if device.model != becs_device.model:
            # todo check if model is ok
            print(f"Device '{device.name}', changing model from '{device.model}' to '{becs_device.model}'")
            if device_type:
                device_update.device_type = device_type.id

        r = self.save_device_updates(device=device, device_update=device_update, custom_fields=custom_fields)
        if r:
            self.refresh_device(device=device)

    def sync_device_interfaces(self, device=None, becs_device=None):
        """
        sync interfaces
        Create/rename/delete interfaces in Netbox based on whats in BECS
        """
        update = False

        delete = set(device.interfaces_oid) - set(becs_device.interfaces_oid)

        for oid in delete:
            interface = device.interfaces_oid[oid]
            print(f"Netbox device '{device.name}', delete interface '{interface.name}'")
            try:
                r = self.netbox.delete_interface(interface.id)
                if r:
                    update = True
            except self.netbox.exception as e:
                errors.add(f"Error: Netbox device '{device.name}', delete interface '{interface.name}", e)

        if update:
            self.refresh_device(device=device)

        create = set(becs_device.interfaces_oid) - set(device.interfaces_oid)
        update = False
        for oid in create:
            # BECS interface does not exist in netbox,
            becs_interface = becs_device.interfaces_oid[oid]

            if becs_interface.name in device.interfaces:
                # Interface exist but no oid, write OID
                # todo, remove when done
                print(f"Netbox device '{becs_device.name}', update interface '{becs_interface.name}' with becs_oid")
                interface = device.interfaces[becs_interface.name]
                interface_update = AttrDict()
                interface_update.label = f"becs_oid={becs_interface.oid}"
                try:
                    r = self.netbox.update_interface(interface.id, interface_update)
                    if r:
                        update = True
                except self.netbox.exception as e:
                    errors.add(f"Error: Netbox device '{becs_device.name}', update interface '{becs_interface.name}' with becs_oid", e)

            else:
                print(f"Netbox device '{becs_device.name}', create interface '{becs_interface.name}'")

                # BECS does not know what interface.type an interface should have
                # Lookup device_type in Netbox and copy from that
                device_type = self.get_device_type(becs_device.model)
                type_ = None
                if device_type:
                    device_type_interface = device_type.interfaces.get(becs_interface.name, None)
                    if device_type_interface:
                        type_ = device_type_interface.type.value
                if type_ is None:
                    if "ethernet" in becs_interface.name.lower():
                        type_ = "1000base-t"
                    else:
                        type_ = "virtual"
                r = self.netbox.create_interface_becs(
                    device_id=device.id,
                    name=becs_interface.name,
                    type_=type_,
                    becs_interface=becs_interface,
                )
                if r:
                    update = True
            
        if update:
            self.refresh_device(device=device)

        return update

    def sync_device_interfaces_settings(self, device=None, becs_device=None) -> None:
        """
        If interface name is renamed, it is important to do this in the correct order.
        renaming fastethernet1->gigabitethernet1 does not work, if gigabitethernet1 already exist
        """
        update = False
        device_type = self.get_device_type(becs_device.model)

        interface_updates = {}    # Key is old interface name
        for oid, interface in device.interfaces_oid.items():
            interface_update = AttrDict()
            if oid in becs_device.interfaces_oid:
                becs_interface = becs_device.interfaces_oid[oid]

                if interface.name != becs_interface.name:
                    # Interface has been renamed
                    interface_update.name = becs_interface.name

                # Check that the interface type is ok
                device_type_interface = device_type.interfaces.get(becs_interface.name, None)
                if device_type_interface and device_type_interface.type.value:
                    if interface.type_value != device_type_interface.type.value:
                        # interface has wrong type
                        interface_update.type = device_type_interface.type.value

            if interface_update:
                interface_update.id = interface.id
                interface_updates[interface.name] = interface_update

        if interface_updates:
            # Update interfaces in correct order, to hande interface name rename collisions
            while interface_updates:
                for ifname, update in interface_updates.items():
                    if "name" in update and ifname != update.name:
                        # name change, make sure new name does not exist - it would cause a collision
                        if update.name in interface_updates:
                            continue    # We update this interface later
                    interface_id = update.pop("id")
                    print("Updating interface", ifname, interface_id)
                    abutils.pprint(update)

                    r = self.netbox.update_interface(interface_id, update)
                    if not r:
                        print(f"Could not update device {device.name}, interface {ifname} with {update}")
                    del interface_updates[ifname]
                    break

            self.refresh_device(device=device)  # Update in-memroy copy

    def sync_interface_addresses_delete(self, device=None, becs_device=None) -> None:
        """
        Remove unwanted adresses from interfaces
        """
        # print("----- Sync interface addresses -----")
        update = False
        for oid, interface in device.interfaces_oid.items():
            becs_interface = becs_device.interfaces_oid.get(oid, None)
            if not becs_interface:
                print(f"Error? Netbox device '{device.name}', interface {interface.name}, oid {oid} missing in becs")
                continue

            if interface.prefix4:
                interface_prefix4 = interface.prefix4[0]
            else:
                interface_prefix4 = None

            if len(becs_interface.prefix4):
                becs_interface_prefix4 = becs_interface.prefix4[0]
            else:
                becs_interface_prefix4 = None

            device_update = AttrDict()
            delete = False
            if interface_prefix4 and not becs_interface_prefix4:
                delete = True
            if interface_prefix4 and becs_interface_prefix4:
                if interface_prefix4.becs_oid != becs_interface_prefix4.oid:
                    delete = True   # Incorrect OID

            if delete:
                print(f"Netbox '{device.name}', interface '{interface.name}', "
                      "delete address '{interface_prefix4.address}'")
                r = self.netbox.delete_ipaddress(address_id=interface_prefix4.id)
                update = True

                if interface.name == "loopback0":
                    if device.primary_ip4:
                        print(f"Netbox '{device.name}', interface '{interface.name}', "
                              "address '{interface_prefix4.address}', delete from primary_ip4")
                        device_update.primary_ip4 = None

        if update:
            self.refresh_device(device=device)
   
    def sync_interface_addresses_create(self, device=None, becs_device=None) -> None:
        """
        Add missing addresses on interfaces
        """
        # print("----- Sync interface addresses -----")
        update = False
        for oid, interface in device.interfaces_oid.items():
            becs_interface = becs_device.interfaces_oid.get(oid, None)
            if not becs_interface:
                print(f"Error? Netbox device '{device.name}', interface {interface.name}, oid {oid} missing in becs")
                continue

            if interface.prefix4:
                interface_prefix4 = interface.prefix4[0]
            else:
                interface_prefix4 = None

            if len(becs_interface.prefix4):
                becs_interface_prefix4 = becs_interface.prefix4[0]
            else:
                becs_interface_prefix4 = None

            device_update = AttrDict()
            if interface_prefix4 and becs_interface_prefix4:
                # Exist in Netbox and BECS
                if interface_prefix4.address != becs_interface_prefix4.address:
                    # update, handle as delete + create
                    print(f"Netbox '{device.name}', interface '{interface.name}', "
                          f"update address from '{interface_prefix4.address}' -> '{becs_interface_prefix4.address}'")
                    r = self.netbox.delete_ipaddress(address_id=interface_prefix4.id)
                    r = self.netbox.create_interface_ipaddress(
                        interface=interface,
                        address=becs_interface_prefix4.address,
                        becs_oid=becs_interface_prefix4.oid,
                    )
                    interface_prefix4 = r
                    update = True

            if not interface_prefix4 and becs_interface_prefix4:
                # Exist in BECS, not in Netbox
                print(f"Netbox '{device.name}', interface '{interface.name}', "
                      f"create address '{becs_interface_prefix4.address}'")
                r = self.netbox.create_interface_ipaddress(
                    interface=interface,
                    address=becs_interface_prefix4.address,
                    becs_oid=becs_interface_prefix4.oid,
                )
                interface_prefix4 = r
                if r:
                    update = True

            if interface.name == "loopback0":
                # Make sure we have a primary_ip4 on the device
                if not device.primary_ip4:
                    # Device has no primary_ip4
                    if interface_prefix4:
                        print(f"  Netbox '{device.name}', interface '{interface.name}', address '{interface_prefix4.address}', set as primary_ip4")
                        device_update.primary_ip4 = interface_prefix4.id
                else:
                    # Device has an primary_ip4
                    if device.primary_ip4.id != interface_prefix4.id:
                        print(f"  Netbox '{device.name}', interface '{interface.name}', address '{interface_prefix4.address}', update primary_ip4")
                        device_update.primary_ip4 = interface_prefix4.id

            if device_update:
                update = True
                r = self.save_device_updates(device=device, device_update=device_update)
        if update:
            self.refresh_device(device=device)

    def sync(self, name: str = None, refresh_becs: bool = False, refresh_netbox: bool = False) -> None:
        n = common.Name(name)
        self.netbox = Netbox(config=config)
        self.becs = Becs(config=config)

        # ------------------------------------------------------
        # Fetch all devices from becs and netbox
        # Find out which needs to be created/deleted in NetBox
        # ------------------------------------------------------

        print("----- Start sync -----")

        # Get all Netbox devices
        if refresh_netbox:
            self.devices = self.netbox.get_devices(name=name, refresh=args.refresh_netbox, filter_tag="becs")
            if not name:
                self.cache.update_devices(self.devices)
            self.devices = self.cache.devices
            self.devices_oid = self.cache.devices_oid
        else:
            if name:
                device = self.cache.get_device(n.full)
                if device:
                    self.devices = AttrDict()
                    self.devices[n.full] = device
                else:
                    raise RuntimeError(f"Error: unknown device '{name}', cannot sync")
            else:
                self.devices, self.devices_oid = self.cache.get_devices()

        # Get all BECS devices
        self.becs_devices, self.becs_devices_oid = self.becs.get_devices(refresh=refresh_becs)

        print(f"Got {len(self.devices)} devices from Netbox")
        print(f"Got {len(self.becs_devices)} devices from BECS")

        # Make sure all BECS elements exists as Netbox devices
        print("----- Sync devices -----")
        self.sync_devices()

        # Make sure all BECS elements and Netbox devices has the same settings
        print("----- Sync device settings -----")
        for becs_oid, device, becs_device in self.iter_devices():
            if becs_device:
                self.sync_device_settings(device=device, becs_device=becs_device)

        # Make sure all interfaces in becs exist in netbox
        print("----- Sync device interfaces -----")
        for becs_oid, device, becs_device in self.iter_devices():
            if becs_device:
                self.sync_device_interfaces(device=device, becs_device=becs_device)

        # Make sure all BECS interfaces and Netbox Interfaces has the same settings
        print("----- Sync device interface settings -----")
        for becs_oid, device, becs_device in self.iter_devices():
            if becs_device:
                self.sync_device_interfaces_settings(device=device, becs_device=becs_device)

        # Make sure all addresses in becs exist in netbox
        print("----- Sync device interface addresses, delete -----")
        for oid, device, becs_device in self.iter_devices():
            if becs_device:
                self.sync_interface_addresses_delete(device=device, becs_device=becs_device)

        print("----- Sync device interface addresses, create -----")
        for oid, device, becs_device in self.iter_devices():
            if becs_device:
                self.sync_interface_addresses_create(device=device, becs_device=becs_device)


if __name__ == "__main__":
    """
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name")
    parser.add_argument("--refresh-becs", default=False, action="store_true")
    parser.add_argument("--refresh-netbox", default=False, action="store_true")
    args = parser.parse_args()

    try:
        sync = Sync()
        sync.sync(
            name=args.name,
            refresh_becs=args.refresh_becs,
            refresh_netbox=args.refresh_netbox,
        )
        print("----- Done -----")
        if len(errors.errors):
            for err in errors.errors:
                print(f"{err.name} - {err.msg}")
        else:
            print("No errors")

    except:
        abutils.send_traceback()    # Error in script, send traceback to developer
