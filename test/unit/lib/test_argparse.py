"""Test argparse utils."""

from argparse import ArgumentParser

import pytest  # noqa

from lava.lib.argparse import *


# ------------------------------------------------------------------------------
def test_store_name_value_pair(capsys):

    argp = ArgumentParser(add_help=False)
    argp.add_argument('--single', action=StoreNameValuePair)
    argp.add_argument('--multi', action=StoreNameValuePair, nargs='+')

    # Good args
    args = argp.parse_args(['--single', 's1=v1', '--single', 's2=v2', '--multi', 'm1=v3', 'm2=v4'])
    assert args.single == {'s1': 'v1', 's2': 'v2'}
    assert args.multi == {'m1': 'v3', 'm2': 'v4'}

    # Bad args
    with pytest.raises(SystemExit):
        argp.parse_args(['--single', 'bad'])
    assert 'error: argument --single' in capsys.readouterr().err


# ------------------------------------------------------------------------------
def test_argparser_no_exit_status_nonzero(capsys):
    argp = ArgparserNoExit(prog='test', add_help=False)
    argp.add_argument('-f', '--flag', action='store_true', help='A flag.')

    with pytest.raises(ArgparserExitError, match='unrecognized arguments: --unknown-arg'):
        argp.parse_args(['--unknown-arg'])
    out, err = capsys.readouterr()
    assert 'unrecognized arguments: --unknown-arg' in out


# ------------------------------------------------------------------------------
def test_argparser_no_exit_status_zero(capsys):
    argp = ArgparserNoExit(prog='test')
    argp.add_argument('-f', '--flag', action='store_true', help='A flag.')

    # The -h will force an exit but because only parse known args -- no error
    argp.parse_known_args(['-h', '--unknown-arg'])
    out, err = capsys.readouterr()
    assert 'options:' in out
    assert '-h, --help' in out
    assert '-f, --flag' in out
