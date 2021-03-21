#!/usr/bin/env python3
"""
Class to handle BECS, using BECS ExtAPI

dependencies:
    sudo pip3 install zeep orderedattrdict
"""

import os
import sys
import json
import gzip
import subprocess
from collections import defaultdict

import zeep
from orderedattrdict import AttrDict

sys.path.insert(0, "/opt")
import ablib.utils as abutils

CONFIG_FILE = "/etc/abcontrol/abcontrol.yaml"       # Used during functional test
BECS_CACHE_FILE = "/var/lib/abcontrol/becs-cache.json.gz"


class BECS:

    def __init__(self, config=None):
        self.config = config
        self.client = zeep.Client(
            wsdl=self.config.becs.eapi.url,
            settings=zeep.Settings(strict=False)
        )

        self.obj_cache = {}            # key is oid, value is object
        self.elements_oid = {}         # key is oid, value is object
        self.login()

    def login(self):
        self.session = self.client.service.sessionLogin({
            "username": self.config.becs.eapi.username,
            "password": self.config.becs.eapi.password,
            })
        self._soapheaders = {
            "request": {"sessionid": self.session["sessionid"]},
        }

    def logout(self):
        self.client.service.sessionLogout({}, _soapheaders=self._soapheaders)

    def get_object(self, oid):
        """
        Fetch one object, using a cache
        retuns object, or None if not found
        """
        if oid in self.obj_cache:
            return self.obj_cache[oid]  # From cache

        data = self.client.service.objectFind(
            {
                "queries": [
                    {"queries": {"oid": oid}}
                ] 
            },
            _soapheaders=self._soapheaders
        )
        # print(f"Fetch object {oid} from BECS API")
        # abutils.pprint(data["objects"][0])
        # Insert in cache
        if data["objects"]:
            obj = data["objects"][0]
            self.obj_cache[oid] = obj
            return obj
        return None

    def search_opaque(self, oid: int, name: str):
        """
        Search for first occurence of an opaque name, walking upwards in tree
        Note: does not handle arrays
        If not found, return None
        """
        value = None
        while True:
            obj = self.get_object(oid)
            if obj is None:
                return value

            if "opaque" in obj:
                for opaque in obj["opaque"]:
                    if opaque["name"] == name:
                        if len(opaque["values"]):
                            value = opaque["values"][0]["value"]
                            return value

            if obj["parentoid"]:
                oid = obj["parentoid"]
                if oid != 1:
                    continue
            return None

    def search_parent(self, oid: int):
        """
        Search for parents, going upwards towards the root
        Returns first found parent name or None if none found
        Parents can either be an element-attach, or an opaque named "parents"
        """
        parents = None
        check_element = False   # No match on first element (ourself)
        while True:
            obj = self.get_object(oid)
            if obj is None:
                return parents

            if "opaque" in obj:
                for opaque in obj.opaque:
                    if opaque.name == "parents":
                        if len(opaque.values):
                            parents = opaque.values[0].value
                            return parents

            if check_element and obj["class"] == "element-attach":
                parents = obj.name
                return parents

            if obj.parentoid:
                oid = obj.parentoid
                if oid != 1:
                    continue
            return None

    def object_tree_find(self, oid: int, walkdown: int = 1, classmask=None):
        """
        input:
            obj        object to start searching for childrens
            walkdown   number of levels to search
            classmask  If specified, dict with classes to include
        """
        res = []

        def recurse(oid, walkdown):
            walkdown -= 1
            obj = self.get_object(oid)
            for childoid in obj._childrenoid:
                child = self.get_object(childoid)
                if classmask:
                    if obj["class"] in classmask:
                        res.append(child)
                else:
                    res.append(child)
                if walkdown:
                    recurse(childoid, walkdown)
        
        recurse(oid, walkdown)
        return res

    def save_object_cache(self, data):
        print("----- BECS, store data in local cache -----")
        with gzip.open(BECS_CACHE_FILE, "wt") as f:
            json.dump(data, f)

    def get_elements(self, oid: int = 1, refresh: bool = False):
        """
        Get all devices (element-attach) from BECS
        We use some php code to fetch the data from becs. PHP SOAP/XML is WAY much faster
        """
        if self.elements_oid and not refresh:
            return self.elements_oid

        self.elements_oid = {}        # key is oid, value is object

        if not os.path.exists(BECS_CACHE_FILE):
            refresh = True

        if refresh:
            print("----- BECS, fetching data, using PHP helper script -----")
            r = subprocess.getoutput(f"/opt/abcontrol/app/tools/becs/get_becs_elements.php {oid}")
            data = json.loads(r, object_pairs_hook=AttrDict)

        else:
            print("----- BECS, fetching data, using local cache -----")
            with gzip.open(BECS_CACHE_FILE, "rt") as f:
                data = json.load(f, object_pairs_hook=AttrDict)

        # put all objects we got into the object cache
        print("----- BECS, Insert all objects in object cache -----")
        for obj in data.objects:
            obj._childrenoid = []
            self.obj_cache[obj.oid] = obj

        # On each obj, build list with children, and reference to parent object
        print("----- BECS, Build reference on each object, to parent and children -----")
        for oid, obj in self.obj_cache.items():
            parent = self.obj_cache.get(obj.parentoid, None)
            if parent:
                parent._childrenoid.append(oid)

        # Build up dictionary, to easy get get/handle parent/child relations
        # make sure name is FQDN
        print("----- BECS, build dictionary with elements -----")
        for element in data.objects:
            if element["class"] == "element-attach":
                if element.elementtype == "ibos":
                    element.name = element.name.lower()
                    self.elements_oid[element.oid] = element

        # For each element
        #   find the parent element
        #   find opaque alarm_destination
        #   find opaque alarm_timeperiod
        print("----- BECS, Get parents, alarm_destination etc -----")
        for oid, element in self.elements_oid.items():
            parents = self.search_parent(oid)
            element["_parents"] = parents
            
            element["_alarm_destination"] = self.search_opaque(oid, "alarm_destination")
            element["_alarm_timeperiod"] = self.search_opaque(oid, "alarm_timeperiod")

        if refresh:
            # Store json data in cache
            print("----- BECS, store data in local cache -----")
            with gzip.open(BECS_CACHE_FILE, "wt") as f:
                json.dump(data, f)

        # Save a copy of all objects, for development
        # with open("/var/lib/abcontrol/becs_objects.out", "w") as f:
        #     json.dump(self.obj_cache, f, indent=2)

        return self.elements_oid

    def get_rcparentoid(self, obj):
        rcparentoid = obj.resource.rcparentoid
        if rcparentoid:
            rc_obj = self.get_object(rcparentoid)
            return rc_obj
        return None

    def get_interfaces(self, oid: int = None):
        """
        Get interfaces and their IP addresses for an element-attach
        Returns a list of interface, each interface is an AttrDict
        """
        
        # data = self.object_tree_find(obj, walkdown=2, classmask={"interface":1, "resource-inet":1})
        data = self.object_tree_find(oid, walkdown=2)
        res = AttrDict()  # Key is interace.name

        # Get IP address for each interface
        # todo: flag, use parentprefixlen
        # todo: ip address $interface.ipaddress $interface.prefixlen
        for interface in data:
            if interface["class"] == "interface":
                flags = interface.get("flags", "")
                enabled = flags.find("disable") < 0

                # search for the resource-inet in response
                prefix4 = []
                prefix6 = []
                for oid in interface._childrenoid:
                    obj = self.get_object(oid)
                    if obj["class"] == "resource-inet":
                        # abutils.pprint(obj)
                        prefixlen = obj.resource.prefixlen
                        if "useparentmask" in obj.get("flags", ""):
                            # find resource parent, to get netmask
                            rcobj = self.get_rcparentoid(obj)
                            # abutils.pprint(rcobj, "rcobj")
                            if rcobj:
                                prefixlen = rcobj.resource.prefixlen

                        prefix = f"{obj.resource.address}/{prefixlen}"
                        addr = AttrDict(
                            address=prefix,
                            oid=obj.oid)
                        prefix4.append(addr)

                d = AttrDict()
                d.oid = interface["oid"]
                d.name = interface["name"]
                d.role = interface["role"]
                d.prefix4 = prefix4
                d.prefix6 = prefix6
                d.enabled = enabled
                res[d.name] = d
        return res


if __name__ == "__main__":
    """
    Function test
    """
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=[
        "get_elements",
        "get_oid",
    ])
    parser.add_argument("-n", "--name")
    parser.add_argument("--oid", default=1)
    parser.add_argument(
        "--refresh",
        default=False, action="store_true"
    )
    args = parser.parse_args()

    config = abutils.load_config(CONFIG_FILE)
    becs = BECS(config=config)

    if args.cmd == "get_elements":
        elements = becs.get_elements(oid=args.oid, refresh=args.refresh)
        for oid, element in elements.items():
            print(element.name)
            interfaces = becs.get_interfaces(oid=oid)
            for ifname, interface in interfaces.items():
                if interface.prefix4:
                    print("   ", interface.name, interface.prefix4[0].address)
        print(f"Got {len(elements)} elements")
        becs.save_object_cache()

    elif args.cmd == "get_oid":
        obj = becs.get_object(oid=args.oid)
        abutils.pprint(obj)
    else:
        print("Internal error, unknown command", args.cmd)
