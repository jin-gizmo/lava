#!/usr/bin/env python3

"""
Build a lava DynamoDB table entry.

The output is in YAML format.

"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import OrderedDict
from glob import glob

import jinja2
import yaml
from jinja2.meta import find_undeclared_variables

__author__ = 'Murray Andrews'
__version__ = '1.0.0'

PROG = os.path.splitext(os.path.basename(sys.argv[0]))[0]

RE_VAR = re.compile(r'^\s*#=\s*(?P<name>\w+):?\s+(?P<prompt>.*)')
RE_COMMENT = re.compile(r'^\s*##')
RE_DELETE = re.compile(r'\s*#-')

LAVA_TEMPLATE_PATH = '/usr/local/lib/lava/templates:templates'


# ..............................................................................
# region Utilities
# ..............................................................................


# ------------------------------------------------------------------------------
def prompt_tty(p: str) -> str:
    """
    Prompt for user input from the tty.

    We can't use Python's stupid input() function because that sends prompts to
    stdout (dumb).

    :param p:       The prompt.
    :return:        The user response (with line feed stripped).
    """

    with open('/dev/tty', 'w+') as tty:
        print(p, file=tty, end='')
        tty.flush()
        return tty.readline().rstrip('\n')


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
def find_in_path(filename, path):
    """
    Find a file in a path.

    If an absolute path is provided in filename then it is merely checked for
    existence and the absolute path will be returned if it exists. Otherwise the
    path will be searched for the file and if it exists in the path, the
    absolute path will be returned.

    :param filename:    The name of the file to find.
    :param path:        The path. May be either a string of : separated
                        directories or an iterable of dir names. An empty path
                        ('', [] or None) is treated as current directory only.
    :type filename:     str
    :return:            The absolute path of the file if found otherwise None.
    :rtype:             str

    """

    if not filename:
        raise ValueError('filename must be specified')

    if os.path.isabs(filename):
        return filename if os.path.exists(filename) else None

    if not path:
        path = ['.']
    elif isinstance(path, str):
        path = path.split(':')

    for d in path:
        p = os.path.join(d, filename)
        if os.path.exists(p):
            return os.path.abspath(p)

    return None


# ..............................................................................
# endregion Utilities
# ..............................................................................


# ------------------------------------------------------------------------------
def process_cli_args() -> argparse.Namespace:
    """
    Process the command line arguments.

    :return:    The args namespace.
    """

    argp = argparse.ArgumentParser(
        prog=PROG, description='Build a lava DynamoDB table entry from templates'
    )

    argp.add_argument(
        '-C',
        '--no-comments',
        dest='no_comments',
        action='store_true',
        help='Strip informational comments from the template.',
    )

    argp.add_argument(
        '-j',
        '--json',
        action='store_true',
        help='Produce JSON output instead of YAML. As the JSON'
        ' output will not contain any comments, this is gemerally'
        ' of limited value.',
    )

    argp.add_argument(
        '-p',
        '--param',
        action=StoreNameValuePair,
        metavar='name=value',
        help='Set the value of a parameter to be fed in to the template.'
        ' Multiple parameters can be specified using'
        ' multiple -p/--param arguments.',
    )

    argp.add_argument(
        '-P',
        '--all-params',
        dest='all_params',
        action='store',
        help='Use the specified value for all undefined parameters'
        ' rather than prompting the user for them.',
    )

    argp.add_argument(
        '-t',
        '--template-path',
        action='store',
        dest='template_path',
        default=os.environ.get('LAVA_TEMPLATE_PATH', LAVA_TEMPLATE_PATH),
        help='Path to search for lava templates. If not specified, the'
        ' LAVA_TEMPLATE_PATH environment variable is used if set,'
        ' otherwise a default path is used.',
    )

    argp.add_argument('-v', '--version', action='version', version=__version__)

    argp.add_argument('type', action='store', help='Lava item type (e.g. job).')

    argp.add_argument(
        'sub_type',
        metavar='sub-type',
        nargs='?',
        help='Lava item sub-type (e.g. exe or pkg for job). If'
        ' required but not specified, this will be obtained'
        ' interactively.',
    )

    return argp.parse_args()


# ------------------------------------------------------------------------------
def get_template_names(d: str) -> set[str]:
    """
    Return the set of YAML files in a directory (with yaml suffix removed).

    Does not recurse.

    :param d:       The directory name.
    :return:        The set of basenames with no suffix
    """

    return {
        os.path.splitext(os.path.basename(f))[0] for f in glob(os.path.join(d, '[A-Za-z]*.yaml'))
    }


# ------------------------------------------------------------------------------
def prompt_for_item_subtype(item_type: str, template_dir: str) -> str | None:
    """
    Prompt the user for a sub-type for the given item type.

    Raises an exception if stdin is not a TTY.

    :param item_type:       The lava item type (e.g. job, connection, s3trigger)
    :param template_dir:    The name of the directory containing sub-type
                            templates.
    :return:                The selected template name or None for those item
                            types without sub-types.
    """

    template_names = sorted(get_template_names(template_dir))

    if not os.isatty(sys.stdin.fileno()):
        raise Exception('stdin is not a tty')

    if not template_names:
        # This item type has no sub-types.
        return None

    while True:
        t = prompt_tty(f'{item_type.capitalize()} sub-type: ').strip()

        if t:
            # Look for a match against available templates. A unique
            # matching prefix is ok.

            selection = [s for s in template_names if s.startswith(t)]
            if len(selection) == 1:
                return selection[0]

            if not selection:
                print(f'{t}: No such {item_type}', file=sys.stderr)
            else:
                print(f'{t}: Not unique - matches {", ".join(sorted(selection))}', file=sys.stderr)

        print(
            '\nChoose one of the following (unique prefix is ok):\n\n  {}\n'.format(
                '\n  '.join(template_names)
            ),
            file=sys.stderr,
        )


# ------------------------------------------------------------------------------
def load_templates(
    files: str | list[str], strip_comments: bool = False
) -> tuple[list[str], OrderedDict]:
    """
    Load a bunch of template files into a single entity.

    :param files:   A list of file names.
    :param strip_comments:  If True remove informational comments from the
                            template. These are comments that start with '##'.
                            Default is False.

    :return:        A tuple: (list-of-lines, variables-extracted).
    """

    if isinstance(files, str):
        files = [files]

    lines = []
    variables = OrderedDict()

    for f in files:
        with open(f) as fp:
            ll = fp.readlines()

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

    # ----------------------------------------
    return lines, variables


# ------------------------------------------------------------------------------
def main() -> int:
    """
    Do the business.

    :return:    Status
    """

    args = process_cli_args()

    template_dir = find_in_path(args.type, args.template_path)

    # ----------------------------------------
    # Check that our template directory has templates in it.

    if not template_dir:
        raise Exception(f'Cannot find templates for item of type "{args.type}"')
    if not os.path.isdir(template_dir):
        raise Exception(f'{template_dir} is not a directory')
    if not os.path.isfile(os.path.join(template_dir, '__common__.yaml')):
        raise Exception(f'{template_dir} does not look like a lava template directory')

    # ----------------------------------------
    # Get names of template files

    template_files = [os.path.join(template_dir, '__common__.yaml')]

    if not args.sub_type:
        sub_type = prompt_for_item_subtype(args.type, template_dir)
        if sub_type:
            template_files.append(os.path.join(template_dir, f'{sub_type}.yaml'))
    else:
        t = os.path.join(template_dir, f'{args.sub_type}.yaml')
        if not os.path.isfile(t):
            raise Exception(f'{args.sub_type}: Unknown sub-type for item type "{args.type}"')
        template_files.append(t)

    # ----------------------------------------
    template, vars_needed = load_templates(template_files, strip_comments=args.no_comments)
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

    if args.json:
        t = json.dumps(yaml.safe_load(t), indent=4, sort_keys=True)

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
