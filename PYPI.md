# Lava

**Lava** is an AWS based distributed scheduler and job runner. It is scalable,
robust and built using native AWS components, wherever possible.

Lava has been used extensively in a large, business critical data warehouse /
data lake environment to run tens of thousands of jobs a day on a 24x7 basis,
with jobs lasting anywhere between a few seconds and 12 hours.

Typical jobs perform tasks such as:

*   AWS environment command, control and maintenance.

*   Data ETL jobs, large and small.

*   Inter-company data exchanges.

Lava was built as a result of terminal frustration with some commercial and open
source options that, too often, proved to be either fragile, or hard to install,
maintain or use in a complex multi-user, multi-environment context.

![AWS](https://img.shields.io/badge/AWS-FF9900?logoColor=black)
![Linux](https://img.shields.io/badge/linux-F4BC00?logo=linux&logoColor=black)
![macOS](https://img.shields.io/badge/macOS-999999?logo=apple)
[![PyPI version](https://img.shields.io/pypi/v/jinlava)](https://pypi.org/project/jinlava/)
[![Python versions](https://img.shields.io/pypi/pyversions/jinlava)](https://pypi.org/project/jinlava/)
![PyPI - Format](https://img.shields.io/pypi/format/jinlava)
[![GitHub License](https://img.shields.io/github/license/jin-gizmo/lava)](https://github.com/jin-gizmo/lava/blob/master/LICENCE.txt)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Genesis

**Lava** was developed at [Origin Energy](https://www.originenergy.com.au)
as part of the *Jindabyne* initiative. While not part of our core IP, it proved
valuable internally, and we're sharing it in the hope it's useful to others.

Kudos to Origin for fostering a culture that empowers its people
to build complex technology solutions in-house.

[![Jin Gizmo Home](https://img.shields.io/badge/Jin_Gizmo_Home-d30000?logo=GitHub&color=d30000)](https://jin-gizmo.github.io)

## Features

**Lava** features include:

*   Provision of an integrated orchestration and execution environment that is
    readily scalable from a desktop installation to a large auto scaling fleet.

*   Jobs can be scheduled, triggered by AWS and external events or initiated by
    other jobs.

*   Ability to connect to a variety of database types, including Postgres, MySQL,
    Oracle, Microsoft SQL Server and Redshift.

*   Enhanced support for some AWS RDS and RDS Aurora databases.

*   Built-in connectors to a handful of useful services, including databases,
    file shares, Microsoft SharePoint, email servers and Slack.

*   Ability to run SQL jobs as well as executable payloads, including docker
    based payloads and native code bundles.

*   Secure management of connection credentials to avoid the need to embed them
    into job payloads.

## Installation and Usage

See the [user guide](https://jin-gizmo.github.io/lava/) for details.
