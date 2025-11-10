#!/usr/bin/env python3

"""DAG generator for lava jobs."""

import argparse
import json
import os
import sys
from functools import partial
from graphlib import CycleError, TopologicalSorter  # noqa

import yaml  # noqa: I100, I202
from lava.lib.dag import (  # noqa I201
    DEFAULT_TABLE,
    load_dag_from_csv,
    load_dag_from_lava_conn,
    load_dag_from_sqlite3,
    load_dag_from_xlsx,
)

__author__ = 'Murray Andrews'

PROG = os.path.splitext(os.path.basename(sys.argv[0]))[0]


# ------------------------------------------------------------------------------
class YamlDumper(yaml.SafeDumper):
    """Custom YAML dumper to indent lists."""

    # ------------------------------------------------------------------------------
    def increase_indent(self, flow=False, indentless=False):
        """
        See https://stackoverflow.com/questions/25108581/python-yaml-dump-bad-indentation.

        :param flow:        See the (terrible) PyYaml doco.
        :param indentless:  See the (terrible) PyYaml doco.
        :return:            See the (terrible) PyYaml doco.
        """
        return super().increase_indent(flow, False)


# ------------------------------------------------------------------------------
def process_cli_args() -> argparse.Namespace:
    """
    Process the command line arguments.

    :return:    The args namespace.
    """

    argp = argparse.ArgumentParser(
        prog=PROG,
        description='Generate a DAG specification for lava dag jobs from a dependency matrix.',
    )

    argp.add_argument(
        '-c',
        '--compact',
        action='store_true',
        help='Use a more compact form for singleton and empty dependencies.',
    )

    argp.add_argument(
        '-g',
        '--group',
        action='store',
        help=(
            'Select only the specified group of source entries.'
            ' For CSV files, this is ignored.'
            ' For Excel files, this specifies the worksheet name and defaults to the'
            ' first worksheet.'
            ' For sqlite3 files, this is used as a filter value on the "job_group" column'
            ' of the source table and defaults to selecting all entries.'
        ),
    )

    argp.add_argument(
        '-o',
        '--order',
        action='store_true',
        help=(
            'If specified, just print one possible ordering of the jobs'
            ' instead of the DAG specification.'
        ),
    )

    argp.add_argument(
        '-p',
        '--prefix',
        action='store',
        default='',
        help='Prepend the specified prefix to all job IDs.',
    )

    argp.add_argument(
        '-r',
        '--realm',
        action='store',
        default=os.environ.get('LAVA_REALM'),
        help='Lava realm. Required if the DAG source is specified as a lava connection'
        ' ID. Defaults to the value of the LAVA_REALM environment variable.',
    )

    argp.add_argument(
        '-w',
        '--wrap',
        metavar='KEY',
        action='store',
        help='Wrap the DAG specification in the specified map key.',
    )

    argp.add_argument(
        '--table',
        action='store',
        metavar='[SCHEMA.]TABLE',
        default=DEFAULT_TABLE,
        help=f'Table name for database sources. Default is {DEFAULT_TABLE}.',
    )

    argp.add_argument(
        '-y', '--yaml', action='store_true', help='Generate YAML output instead of JSON.'
    )

    argp.add_argument(
        'source',
        action='store',
        help=(
            'Source data for the DAG dependency matrix. CSV, Excel XLSX'
            ' files and sqlite3 files are supported. The filename suffix is used to'
            ' determine file type. If the value is not a recognised file type, it is'
            ' assumed to be a lava database connection ID. In this case the lava realm'
            ' must be specified via -r, --realm or the LAVA_REALM environment variable.'
            ' For CSV and Excel, the first column contains successor job names and the'
            ' first row contains predecessor job names. Any non-empty value in the'
            ' intersection of row and column indicates a dependency.'
            ' For database sources, a table with three columns (job_group, job, depends_on)'
            ' is required. The "job" and "depends_on" columns each contain a single job'
            ' name. The "depends_on" column may contain a NULL indicating the "job" must'
            ' be included but has no dependency. There can be multiple rows containing the'
            ' same "job".'
        ),
    )

    return argp.parse_args()


# ---------------------------------------------------------------------------------------
def main() -> int:
    """
    Do the business.

    :return:    status
    """

    args = process_cli_args()

    dumper = (
        partial(yaml.dump, stream=sys.stdout, default_flow_style=False, indent=2, Dumper=YamlDumper)
        if args.yaml
        else partial(json.dump, fp=sys.stdout, indent=4, sort_keys=True)
    )

    # Load the dependency matrix
    if args.source.endswith('.csv'):
        dag = load_dag_from_csv(args.source)
    elif args.source.endswith('.xlsx'):
        dag = load_dag_from_xlsx(args.source, worksheet=args.group)
    elif args.source.endswith(('.sqlite', '.sqlite3')):
        dag = load_dag_from_sqlite3(args.source, group=args.group, table=args.table)
    else:
        if not args.realm:
            raise Exception('Realm must be specified for lava connections')
        dag = load_dag_from_lava_conn(args.source, args.realm, group=args.group, table=args.table)

    if not dag:
        raise ValueError('DAG is empty')

    # Check for cycles
    ts = TopologicalSorter(dag)
    try:
        ts.prepare()
    except CycleError as e:
        raise ValueError(f'{e.args[0].capitalize()}: {", ".join(e.args[1])}')

    if args.order:
        batch_num = 0
        while ts.is_active():
            batch_num += 1
            print(f'Batch {batch_num}')
            batch = ts.get_ready()
            for job in batch:
                if job:
                    print(f'  - {args.prefix}{job}')
                ts.done(job)
        return 0

    # Convert sets back to lists
    all_dependencies = set.union(*dag.values())
    dag = {k: sorted(v) for k, v in dag.items()}

    if args.compact:
        compact = {}
        for job, dep in dag.items():
            if job in all_dependencies and not dep:
                # Don't need this one is job is run anyway
                continue
            if not dep:
                compact[job] = None
            elif len(dep) == 1:
                compact[job] = dep[0]
            else:
                compact[job] = dep
        dag = compact

    if args.prefix:
        dag = {
            f'{args.prefix}{job}': (
                [f'{args.prefix}{d}' for d in dep] if dep else f'{args.prefix}{dep}' if dep else dep
            )
            for job, dep in dag.items()
        }

    if args.wrap:
        dag = {args.wrap: dag}

    dumper(dag)
    if not args.yaml:
        print(file=sys.stdout)
    return 0


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    # Uncomment for debugging
    # exit(main())  # noqa: ERA001
    try:
        exit(main())
    except Exception as ex:
        print(f'{PROG}: {ex}', file=sys.stderr)
        exit(1)
    except KeyboardInterrupt:
        print('Interrupt', file=sys.stderr)
        exit(2)
