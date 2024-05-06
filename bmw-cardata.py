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
# Version 0.1 / 2024-02-02
#       Text representation of charging data completed
# Version 0.2 / 2024-05-06
#       Added CSV output

import sys
import argparse
import json
import csv
import locale
from datetime import datetime

# The following libs must be installed with pip
from icecream import ic
# Disable debugging
ic.disable()
from pytz import timezone

# Local modules
from verbose import verbose, warning, error

VERSION = "0.1 / 2024-02-02"
AUTHOR  = "Martin Junius"
NAME    = "bmw-cardata"



class iX1:
    capacity_net   = 64.8   # Net capacity battery / kWh
    capacity_gross = 66.5   # Gross capacity battery / kWh



class Options:
    limit = 0                       # -l --limit N
    output = "Ladehistorie.csv"     # -o --output NAME
    csv    = False                  # -C --csv



class CSVOutput:
    csv_cache = []
    fields = None

    def add_csv_row(obj):
        CSVOutput.csv_cache.append(obj)

    def add_csv_fields(fields):
        CSVOutput.fields = fields

    def write_csv(file):
        with open(file, 'w', newline='', encoding="utf-8") as f:
            ##FIXME: check  locale.RADIXCHAR
            if locale.localeconv()['decimal_point'] == ",":
                # Use ; as the separator and quote all fields for easy import in "German" Excel
                writer = csv.writer(f, dialect="excel", delimiter=";", quoting=csv.QUOTE_ALL)
            else:
                writer = csv.writer(f, dialect="excel")
            if CSVOutput.fields:
                writer.writerow(CSVOutput.fields)
            writer.writerows(CSVOutput.csv_cache)



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



def val(val):
    return locale.format_string("%.3f", val)

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

        location                        = obj["chargingLocation"]["formattedAddress"]
        public                          = "(Public)" if obj["publicChargingPoint"] else ""

        bat1     = displayedStartSoc
        bat2     = displayedSoc
        tz       = timezone(timeZone)
        start    = datetime.fromtimestamp(startTime).astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
        end      = datetime.fromtimestamp(endTime).astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
        duration = int(totalChargingDurationSec / 60 + 0.5) # min
        km       = str(mileage) + " " + mileageUnits.lower()
        pre      = "" ##NOTUSED: always True???## "(pre-conditoned)" if isPreconditioningActivated else ""
        consumed = energyConsumedFromPowerGridKwh   # Consumed from grid
        increase = energyIncreaseHvbKwh             # Stored in high voltage battery
        loss     = (consumed - increase) / consumed * 100 if consumed > 0 else 0
        delta    = iX1.capacity_net * (bat2 - bat1) / 100

        if Options.csv:
            CSVOutput.add_csv_row([start, totalChargingDurationSec, location, public, mileage, bat1, bat2,
                                    val(delta), val(consumed), val(increase), val(loss)])
        else:
            print(f"[{index:02d}] Charging session: {start} / {duration} min")
            print(f"     Location: {location} {public}")
            print(f"     Mileage: {km} {pre}")
            print(f"     Battery: {bat1}% -> {bat2}% (~{delta:.2f} kWh)")
            print(f"     Energy: {consumed:.2f} kWh from grid -> {increase:.2f} kWh to battery, loss {loss:.1f}%")
            print()

    
    def process_data(self):
        # Ladehistorie top-level is a list []
        if type(self.data) != list:
            error("Ladehistorie: top-level is of type", type(self.data))
        
        if Options.csv:
            CSVOutput.add_csv_fields(["Start date", "Duration/s", "Location", "Public", "Mileage/km", 
                                      "SoC1/%", "SoC2/%", "Delta/kWh", "Grid/kWh", "Battery/kWh", "Loss/%"])

        # Process charge history items
        for i, obj in enumerate(self.data):
            ic(i, obj)
            self.process_item(i, obj)

        # Output to CSV file
        if Options.csv:
            verbose(f"writing CSV output to {Options.output}")
            CSVOutput.write_csv(Options.output)




def main():
    arg = argparse.ArgumentParser(
        prog        = NAME,
        description = "BMW CARDATA analyzer",
        epilog      = "Version " + VERSION + " / " + AUTHOR)
    arg.add_argument("-v", "--verbose", action="store_true", help="verbose messages")
    arg.add_argument("-d", "--debug", action="store_true", help="more debug messages")
    arg.add_argument("-l", "--limit", type=int, help="limit recursion depth")
    arg.add_argument("-L", "--ladehistorie", action="store_true", help="process Ladehistorie data")
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
    if args.debug:
        ic.enable()
        ic(args)
    if args.limit:
        Options.limit = args.limit
    if args.csv:
        Options.csv = True
    if args.output:
        Options.output = args.output


    data = Ladehistorie() if args.ladehistorie else JSONData()

    # set default locale
    locale.setlocale(locale.LC_ALL, "")

    for f in args.filename:
        verbose("processing JSON file", f)
        data.read_json(f)
        data.process_data()



if __name__ == "__main__":
    main()
