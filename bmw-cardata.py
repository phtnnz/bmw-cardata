#!/usr/bin/env python

# Copyright 2024-2025 Martin Junius
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
# Version 0.1 / 2024-02-02
#       Text representation of charging data completed
# Version 0.2 / 2024-05-06
#       Added CSV output
# Version 0.3 / 2024-08-01
#       Use csvoutput module
# Version 0.4 / 2024-11-01
#       Added support for Reifendiagnose -R --reifendiagnose
# Version 0.5 / 2025-01-07
#       Reworked csvoutput, timezone handling
# Version 0.6 / 2025-05-13
#       Fixed missing energyIncreaseHvbKwh in newest BMW CarData

import sys
import argparse
import json
from datetime import datetime
from zoneinfo import ZoneInfo


# The following libs must be installed with pip
# tzdata required on Windows for IANA timezone names!
import tzdata
from icecream import ic
# Disable debugging
ic.disable()

# Local modules
from verbose import verbose, warning, error
from csvoutput import csv_output

VERSION = "0.6 / 2025-05-13"
AUTHOR  = "Martin Junius"
NAME    = "bmw-cardata"



class iX1:
    capacity_net   = 64.8   # Net capacity battery / kWh
    capacity_gross = 66.5   # Gross capacity battery / kWh



class Options:
    limit = 0                       # -l --limit N
    output = "Ladehistorie.csv"     # -o --output NAME
    csv    = False                  # -C --csv



class JSONData:
    """Holds data read from BMW CARDATA .json"""

    def __init__(self):
        self.data = None


    def read_json(self, file):
        with open(file, 'r', encoding="utf-8") as f:
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
        startTime                       = obj.get("startTime")
        endTime                         = obj.get("endTime")
        if not startTime or not endTime:
            # Don't process item, if charging was/is on-going while the report was generated
            return

        displayedSoc                    = obj.get("displayedSoc")
        displayedStartSoc               = obj.get("displayedStartSoc")
        energyConsumedFromPowerGridKwh  = obj.get("energyConsumedFromPowerGridKwh")
        energyIncreaseHvbKwh            = obj.get("energyIncreaseHvbKwh")
        isPreconditioningActivated      = obj.get("isPreconditioningActivated")
        mileage                         = obj.get("mileage")
        mileageUnits                    = obj.get("mileageUnits")
        timeZone                        = obj.get("timeZone")
        totalChargingDurationSec        = obj.get("totalChargingDurationSec")

        location                        = obj["chargingLocation"]["formattedAddress"]
        public                          = "(Public)" if obj["publicChargingPoint"] else ""

        bat1     = displayedStartSoc
        bat2     = displayedSoc
        delta    = iX1.capacity_net * (bat2 - bat1) / 100
        tz       = ZoneInfo(timeZone)
        start    = datetime.fromtimestamp(startTime).astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
        end      = datetime.fromtimestamp(endTime).astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
        duration = int(totalChargingDurationSec / 60 + 0.5) # min
        km       = str(mileage) + " " + mileageUnits.lower()
        pre      = "" ##NOTUSED: always True???## "(pre-conditoned)" if isPreconditioningActivated else ""
        consumed = energyConsumedFromPowerGridKwh   # Consumed from grid
        increase = energyIncreaseHvbKwh or 0        # Stored in high voltage battery,
                                                    # seems to be missing in in CarData from 2025-05+,
        if not increase:                            # in this case replace with value from SoC delta
            increase = delta
        loss     = (consumed - increase) / consumed * 100 if consumed > 0 else 0
        if loss < 0:
            loss = 0
        kW       = energyConsumedFromPowerGridKwh / totalChargingDurationSec * 3600 if totalChargingDurationSec > 0 else 0

        if Options.csv:
            csv_output.add_row([start, end, totalChargingDurationSec, location, public, mileage, bat1, bat2,
                               delta, consumed, increase, loss, kW])
        else:
            print(f"[{index:02d}] Charging session: {start} / {duration} min")
            print(f"     Location: {location} {public}")
            print(f"     Mileage: {km} {pre}")
            print(f"     Battery: {bat1}% -> {bat2}% (~{delta:.2f} kWh)")
            if increase:
                print(f"     Energy: {consumed:.2f} kWh from grid -> {increase:.2f} kWh to battery, loss {loss:.1f}%, {kW:.1f} kW (mean)")
            else:
                print(f"     Energy: {consumed:.2f} kWh from grid, loss {loss:.1f}%, {kW:.1f} kW (mean)")
            print()

    
    def process_data(self):
        # Ladehistorie top-level is a list []
        if type(self.data) != list:
            error("Ladehistorie: top-level is of type", type(self.data))
        
        if Options.csv:
            csv_output.add_fields(["Start date", "End date", "Duration/s", "Location", "Public", "Mileage/km", 
                                      "SoC1/%", "SoC2/%", "Delta/kWh", "Grid/kWh", "Battery/kWh", "Loss/%", "Power/kW"])

        # Process charge history items
        for i, obj in enumerate(self.data):
            ic(i, obj)
            self.process_item(i, obj)

        # Output to CSV file
        if Options.csv:
            verbose(f"writing CSV output to {Options.output}")
            csv_output.write(Options.output)



class Reifendiagnose(JSONData):
    """Data handling for BMW CARDATA Reifendiagnose"""

    def __init__(self):
        super().__init__()


    def process_item(self, obj):
        # Obj is a dict {}
        if type(obj) != dict:
            error("Reifendiagnose: item is of type", type(obj))

        # Get tyres
        for tyre in [ "frontLeft", "frontRight", "rearLeft", "rearRight" ]:
            obj1     = obj[tyre]
            dim      = obj1["dimension"]["value"]
            date     = obj1["mountingDate"]["value"]
            part     = obj1["partNumber"]["value"]
            runflat  = obj1["runFlat"]["value"]
            season   = obj1["season"]["value"]
            tread    = obj1["tread"]["value"]
            proddate = obj1["tyreProductionDate"]["value"]
            wear     = obj1["tyreWear"].get("value") or "n/a"

            print(f"  {tyre.capitalize():<10s}  {tread}, {dim} ({season}), {part}, {date}, {wear}")


    
    def process_data(self):
        # Reifendiagnose top-level is a dict []
        if type(self.data) != dict:
            error("Reifendiagnose: top-level is of type", type(self.data))
        
        # Dig deeper ... ;-)
        obj = self.data["passengerCar"]
        mounted   = obj["mountedTyres"]
        unmounted = obj["unmountedTyres"]
        print("Mounted tyres:")
        self.process_item(mounted)
        print("Unmounted tyres:")
        self.process_item(unmounted)




def main():
    arg = argparse.ArgumentParser(
        prog        = NAME,
        description = "BMW CARDATA analyzer",
        epilog      = "Version " + VERSION + " / " + AUTHOR)
    arg.add_argument("-v", "--verbose", action="store_true", help="verbose messages")
    arg.add_argument("-d", "--debug", action="store_true", help="more debug messages")
    arg.add_argument("-l", "--limit", type=int, help="limit recursion depth")
    arg.add_argument("-L", "--ladehistorie", action="store_true", help="process Ladehistorie data")
    arg.add_argument("-R", "--reifendiagnose", action="store_true", help="process Reifendiagnose data")
    arg.add_argument("-C", "--csv", action="store_true", help="CSV output")
    arg.add_argument("-o", "--output", help="output file")
    arg.add_argument("filename", nargs="+", help="JSON data file")

    args = arg.parse_args()

    if args.debug:
        ic.enable()
        ic(sys.version_info)
        ic(args)
    if args.verbose:
        verbose.set_prog(NAME)
        verbose.enable()
    if args.limit:
        Options.limit = args.limit
    if args.csv:
        Options.csv = True
    if args.output:
        Options.output = args.output


    data = JSONData()
    if args.ladehistorie:
        data = Ladehistorie()
    if args.reifendiagnose:
        data = Reifendiagnose()

    for f in args.filename:
        verbose("processing JSON file", f)
        data.read_json(f)
        data.process_data()



if __name__ == "__main__":
    main()
