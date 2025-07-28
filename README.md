# BMW CarData

Python scripts for analyzing MyBMW CarData

Copyright 2024 Martin Junius

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


## About

This is my personal playground for working with the BMW CarData, Ladehistorie (charging history) and Reifendiagnose (tyre diagnostics).

As of lately (approx. June 2025) the BMW CarData archive doesn't contain the Ladehistorie data anymore, which make this script less useful. I complained to BMW ConnectDrive support, but to no avail. :-(


## bmw-cardata
```
usage: bmw-cardata [-h] [-v] [-d] [-l LIMIT] [-L] [-R] [-C] [-o OUTPUT] filename [filename ...]

BMW CARDATA analyzer

positional arguments:
  filename              JSON data file

options:
  -h, --help            show this help message and exit
  -v, --verbose         verbose messages
  -d, --debug           more debug messages
  -l LIMIT, --limit LIMIT
                        limit recursion depth
  -L, --ladehistorie    process Ladehistorie data
  -R, --reifendiagnose  process Reifendiagnose data
  -C, --csv             CSV output
  -o OUTPUT, --output OUTPUT
                        output file

Version 0.4 / 2024-11-01 / Martin Junius
```
