#!/usr/bin/env python

# Copyright 2023 Martin Junius
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ChangeLog
# Version 0.0 / 2024-01-24
#       First test version, analyse BMW CARDATA Ladehistorie

import argparse
import json
import csv
from datetime import datetime, timedelta

# The following libs must be installed with pip
from icecream import ic
# Disable debugging
ic.disable()
from pytz import timezone
import pytz

# Local modules
from verbose import verbose, warning, error

global VERSION, AUTHOR, NAME
VERSION = "0.0 / 2024-01-24"
AUTHOR  = "Martin Junius"
NAME    = "bmw-cardata"



class iX1:
    capacity_net = 64.8     # Net capacity battery / kWh
    capacity_gross = 66.5   # Gross capacity battery / kWh



class Options:
    limit = 0



class JSONData:
    """Holds data read from BMW CARDATA .json"""

    def __init__(self):
        self.data = None


    def read_json(self, file):
        with open(file, 'r') as f:
            data = json.load(f)
        self.data = data


    def print_list(self, obj, indent, level):
        for val in obj:
            if type(val) is str:
                print(f"{indent} \"{val}\"")
            elif type(val) in (int, float, bool):
                print(f"{indent} {val}")
            else:
                self.print_obj(val, indent, level)


    def print_keys(self, obj, indent, level):
        for k, val in obj.items():
            if type(val) is str:
                print(f"{indent} {k} = \"{val}\"")
            elif type(val) in (int, float, bool):
                print(f"{indent} {k} = {val}")
            else:
                print(f"{indent} {k} = ...")
                self.print_obj(val, indent+"  ", level+1)
        

    def print_obj(self, obj, indent, level):
        if Options.limit and level > Options.limit:
            return

        if type(obj) is dict:
            print(f"{indent} {{...}}")
            self.print_keys(obj, indent+"  ", level+1)
        elif type(obj) is list:
            print(f"{indent} [...]")
            self.print_list(obj, indent+" .", level+1)
        else:
            print(f"{indent} UNKNOWN", type(obj))


    def process_data(self):
        self.print_obj(self.data, ">", 1)



class Ladehistorie(JSONData):
    """Data handling for BMW CARDATA Ladehistorie"""

    def __init__(self):
        super().__init__()


    def process_item(self, index, obj):
        # Obj is a dict {}
        if type(obj) != dict:
            error("Ladehistorie: item is of type", type(obj))

        # Get attributes
        displayedSoc                    = obj["displayedSoc"]
        displayedStartSoc               = obj["displayedStartSoc"]
        endTime                         = obj["endTime"]
        energyConsumedFromPowerGridKwh  = obj["energyConsumedFromPowerGridKwh"]
        energyIncreaseHvbKwh            = obj["energyIncreaseHvbKwh"]
        isPreconditioningActivated      = obj["isPreconditioningActivated"]
        mileage                         = obj["mileage"]
        mileageUnits                    = obj["mileageUnits"]
        startTime                       = obj["startTime"]
        timeZone                        = obj["timeZone"]
        totalChargingDurationSec        = obj["totalChargingDurationSec"]

        bat1  = displayedStartSoc
        bat2  = displayedSoc
        tz    = timezone(timeZone)
        start = datetime.fromtimestamp(startTime).astimezone(tz).strftime("%Y-%m-%d %H:%M")
        end   = datetime.fromtimestamp(endTime).astimezone(tz).strftime("%Y-%m-%d %H:%M")
        duration = int(totalChargingDurationSec / 60) # min
        km    = str(mileage) + " " + mileageUnits.lower()
        pre      = "" ##NOTUSED: always True???## "(pre-conditoned)" if isPreconditioningActivated else ""
        consumed = energyConsumedFromPowerGridKwh   # Consumed from grid
        increase = energyIncreaseHvbKwh             # Stored in high voltage battery
        loss  = (consumed - increase) / consumed * 100 if consumed > 0 else 0

        print(f"[{index}] Charging session {start} / {duration} min")
        print(f"  {km} {pre}")
        print(f"  {bat1}% -> {bat2}%  {consumed:.2f} grid {increase:.2f} battery kWh, loss {loss:.1f}%")

    
    def process_data(self):
        # Ladehistorie top-level is a list []
        if type(self.data) != list:
            error("Ladehistorie: top-level is of type", type(self.data))
        
        # Process charge history items
        for i, obj in enumerate(self.data):
            ic(obj)
            self.process_item(i, obj)




def main():
    arg = argparse.ArgumentParser(
        prog        = NAME,
        description = "BMW CARDATA analyzer",
        epilog      = "Version " + VERSION + " / " + AUTHOR)
    arg.add_argument("-v", "--verbose", action="store_true", help="verbose messages")
    arg.add_argument("-d", "--debug", action="store_true", help="more debug messages")
    arg.add_argument("-l", "--limit", type=int, help="limit recursion depth")
    arg.add_argument("filename", nargs="+", help="filename")

    args = arg.parse_args()

    if args.verbose:
        verbose.set_prog(NAME)
        verbose.enable()
    if args.debug:
        ic.enable()
    if args.limit:
        Options.limit = args.limit

    ic(args)

    data = Ladehistorie()

    for f in args.filename:
        print(arg.prog+":", "processing JSON file", f)
        data.read_json(f)
        data.process_data()



if __name__ == "__main__":
    main()
