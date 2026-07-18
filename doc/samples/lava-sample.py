#!/usr/bin/env python3

"""
Build a lava DynamoDB table entry.

The output is in YAML format.

!!! warning
    This is a VERY bespoke utility for the single specific purpose of building
    the sample entries for the lava user guide. Don't try to use it for anything
    else.

"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path

import jinja2
from jinja2.meta import find_undeclared_variables

__author__ = 'Murray Andrews'
__version__ = '2.0.0'

PROG = os.path.splitext(os.path.basename(sys.argv[0]))[0]

RE_VAR = re.compile(r'^\s*#=\s*(?P<name>\w+):?\s+(?P<prompt>.*)')
RE_COMMENT = re.compile(r'^\s*##')
RE_DELETE = re.compile(r'\s*#-')


# ------------------------------------------------------------------------------
def prompt_tty(p: str) -> str:
    """
    Prompt for user input from the tty.

    We can't use Python's stupid input() function because that sends prompts to
    stdout (dumb).

    :param p:       The prompt.
    :return:        The user response (with line feed stripped).
    """

    with open('/dev/tty', 'r') as tty_in, open('/dev/tty', 'a') as tty_out:
        print(p, file=tty_out, end='')
        tty_out.flush()
        return tty_in.readline().rstrip('\n')


# ------------------------------------------------------------------------------
class StoreNameValuePair(argparse.Action):
    """
    Used with argparse to store values from options of the form ``--option name=value``.

    The destination (self.dest) will be created as a dict {name: value}. This
    allows multiple name-value pairs to be set for the same option.

    Usage is:

        argparser.add_argument('-x', metavar='key=value', action=StoreNameValuePair)

    or
        argparser.add_argument('-x', metavar='key=value ...', action=StoreNameValuePair,
                               nargs='+')

    """

    # --------------------------------------------------------------------------
    def __call__(self, parser, namespace, values, option_string=None):
        """Handle name=value option."""

        if not hasattr(namespace, self.dest) or not getattr(namespace, self.dest):
            setattr(namespace, self.dest, {})
        argdict = getattr(namespace, self.dest)

        if not isinstance(values, list):
            values = [values]
        for val in values:
            try:
                n, v = val.split('=', 1)
            except ValueError:
                raise argparse.ArgumentError(self, f'{val}: Bad parameter specification')
            argdict[n] = v


# ------------------------------------------------------------------------------
def process_cli_args() -> argparse.Namespace:
    """Process the command line arguments."""

    argp = argparse.ArgumentParser(
        prog=PROG, description='Build a lava DynamoDB table entry from components'
    )

    argp.add_argument(
        '-C',
        '--no-comments',
        dest='no_comments',
        action='store_true',
        help='Strip informational comments from the sample.',
    )

    argp.add_argument(
        '-p',
        '--param',
        action=StoreNameValuePair,
        metavar='name=value',
        help=(
            'Set the value of a parameter to be fed in to the sample. Multiple'
            ' parameters can be specified using multiple -p/--param arguments.'
        ),
    )

    argp.add_argument(
        '-P',
        '--all-params',
        dest='all_params',
        action='store',
        help='Use the specified value for undefined parameters rather than prompting for them.',
    )

    argp.add_argument(
        dest='sample_file',
        metavar='file.yaml',
        action='store',
        help='YAML file containing lava item sample.',
    )

    return argp.parse_args()


# ------------------------------------------------------------------------------
def load_samples(files: list[Path], strip_comments: bool = False) -> tuple[list[str], OrderedDict]:
    """
    Load a bunch of template files into a single entity.

    :param files:   A list of file names.
    :param strip_comments:  If True remove informational comments from the
                            template. These are comments that start with '##'.
                            Default is False.

    :return:        A tuple: (list-of-lines, variables-extracted).
    """

    lines = []
    variables = OrderedDict()

    for f in files:
        ll = f.read_text().splitlines()

        # Extract lines starting #= as they represent variables needed to complete
        # the template. They are in the form: `#= varname: prompt`

        template_lines = []

        for line in ll:
            line = line.rstrip('\n')
            if RE_DELETE.search(line) or (strip_comments and RE_COMMENT.search(line)):
                continue

            m = RE_VAR.search(line)
            if m:
                variables[m.group('name')] = m.group('prompt')
            else:
                lines.append(line)

        lines.extend(template_lines)

    # ----------------------------------------
    # Extract the undeclared vars from the template and make sure there
    # is a parameter definition for each of them.

    env = jinja2.Environment(autoescape=jinja2.select_autoescape())
    p = env.parse('\n'.join(lines))
    vars_in_use = find_undeclared_variables(p)
    vars_declared = set(variables)

    not_used = vars_declared - vars_in_use
    if not_used:
        raise Exception(
            f'The following template vars are declared but not used: {", ".join(not_used)}'
        )
    not_declared = vars_in_use - vars_declared
    if not_declared:
        raise Exception(
            f'The following template vars are used but not declared: {", ".join(not_declared)}'
        )

    return lines, variables


# ------------------------------------------------------------------------------
def main() -> int:
    """
    Do the business.

    :return:    Status
    """

    args = process_cli_args()

    # ----------------------------------------
    # Get names of template files

    sample_file = Path(args.sample_file)

    common_component = sample_file.parent / '__common__.yaml'
    sample_components = [common_component] if common_component.exists() else []
    sample_components.append(sample_file)

    # ----------------------------------------
    template, vars_needed = load_samples(sample_components, strip_comments=args.no_comments)
    variables = {}

    for name, prompt in vars_needed.items():
        try:
            variables[name] = args.param[name]
        except (TypeError, KeyError):
            if args.all_params:
                variables[name] = args.all_params
            else:
                variables[name] = prompt_tty(f'{prompt}: ').strip()

    t = jinja2.Template('\n'.join(template)).render(**variables)

    print(t)

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
