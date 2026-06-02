#!/usr/bin/env python3

import argparse
import getpass
import time
import traceback

from . import OMMClient2
from .exceptions import EAuth, ENoEnt
from .messages import GetAccount, Ping

# exit handling with argparse is a bit broken even with exit_on_error=False, so we hack this
def error_instead_exit(self, message):
    raise argparse.ArgumentError(None, message)
argparse.ArgumentParser.error = error_instead_exit

def format_child_type(t):
    return "    {}\n{}".format(t.__class__.__name__, "\n".join(["{:<30}    {}".format(key, value) for key, value in t._attrs.items()]))

def format_list(v):
    return "\n\n\n\n".join(format_child_type(d) for d in v)

    return fl

def main():
    connect_parser = argparse.ArgumentParser(prog='ommclient2')
    connect_parser.add_argument("-n", dest="hostname", default="127.0.0.1")
    connect_parser.add_argument("-u", dest="username", default="omm")
    connect_parser.add_argument("-p", dest="password")
    connect_parser.add_argument("--ommsync", dest="ommsync", action='store_true', help="Log in with ommsync mode")
    connect_parser.add_argument("subcommand", nargs="*")
    args = connect_parser.parse_args()

    hostname = args.hostname
    username = args.username
    password = args.password
    ommsync = args.ommsync
    subcommand = args.subcommand

    if not password:
        password = getpass.getpass(prompt="OMM password for {}@{}:".format(username, hostname))

    try:
        c = OMMClient2(hostname, username, password, ommsync=ommsync)
    except EAuth:
        print("Authentication failed")
        exit(1)
    except TimeoutError:
        print("OMM unreachable")
        exit(1)

    parser = argparse.ArgumentParser(prog="ommclient2", add_help=False, exit_on_error=False)
    subparsers = parser.add_subparsers()

    def add_parser(command_name, func, format=None, args={}):
        subp = subparsers.add_parser(command_name, help=func.__doc__.strip().split("\n")[0], description=func.__doc__)
        if format is not None:
            subp.set_defaults(func=func, format=format)
        else:
            subp.set_defaults(func=func)

        for a, t in args.items():
            subp.add_argument(a, type=t)

        return subp

    parser_exit = subparsers.add_parser("exit")
    parser_exit.set_defaults(func=exit)

    parser_get_account = add_parser("attach_user_device", func=c.attach_user_device, format=format_list, args={
        "uid": int,
        "ppn": int,
    })

    parser_get_account = add_parser("create_user", func=c.create_user, format=format_child_type, args={
        "num": str,
    })

    parser_get_account = add_parser("detach_user_device", func=c.detach_user_device, format=format_list, args={
        "uid": int,
        "ppn": int,
    })

    parser_get_account = add_parser("detach_user_device_by_device", func=c.detach_user_device_by_device, format=format_list, args={
        "ppn": int,
    })

    parser_get_account = add_parser("detach_user_device_by_user", func=c.detach_user_device_by_user, format=format_list, args={
        "uid": int,
    })

    parser_get_account = add_parser("encrypt", func=c.encrypt, args={
        "secret": str,
    })

    parser_get_account = add_parser("get_account", func=c.get_account, format=format_child_type, args={
        "id": int,
    })

    parser_get_account = add_parser("get_device", func=c.get_device, format=format_child_type, args={
        "ppn": int,
    })

    parser_get_account = add_parser("get_devices", func=c.get_devices, format=format_list)

    parser_get_account = add_parser("get_publickey", func=c.get_publickey)

    parser_get_account = add_parser("get_user", func=c.get_user, format=format_child_type, args={
        "uid": int,
    })

    parser_get_account = add_parser("get_users", func=c.get_users, format=format_list)

    parser_help = subparsers.add_parser("help")
    parser_help.set_defaults(func=parser.format_help)

    parser_ping = subparsers.add_parser("ping")
    parser_ping.set_defaults(func=lambda *args, **kwargs: "pong" if c.ping(*args, **kwargs) else "error")

    parser_get_account = add_parser("set_user_name", func=c.set_user_name, args={
        "uid": int,
        "name": str,
    })

    parser_get_account = add_parser("set_user_num", func=c.set_user_num, args={
        "uid": int,
        "num": str,
    })

    parser_get_account = add_parser("set_user_relation_dynamic", func=c.set_user_relation_dynamic, args={
        "uid": int,
    })

    parser_get_account = add_parser("set_user_relation_fixed", func=c.set_user_relation_fixed, args={
        "uid": int,
    })

    parser_get_account = add_parser("set_user_sipauth", func=c.set_user_sipauth, args={
        "uid": int,
        "sipAuthId": str,
        "sipPw": str,
    })

    if subcommand:
        try:
            args = parser.parse_args(subcommand)
        except argparse.ArgumentError as e:
            print("argument error:", e.message)
            exit(1)
        v = dict(vars(args))
        v.pop("func")
        format = lambda r: r
        if v.get("format") is not None:
            format = v.get("format")
            v.pop("format")
        try:
            r = args.func(**v)
        except Exception as e:
            print("".join(traceback.format_exception(type(e), e, e.__traceback__)))
            exit(1)
        print(format(r))
        exit()

    print("OMMClient")
    parser.print_help()

    while True:
        i = input("> ").split()
        try:
            args = parser.parse_args(i)
        except argparse.ArgumentError as e:
            print("argument error:", e.message)
            continue

        v = dict(vars(args))
        v.pop("func")
        format = lambda r: r
        if v.get("format") is not None:
            format = v.get("format")
            v.pop("format")
        try:
            r = args.func(**v)
        except Exception as e:
            print("".join(traceback.format_exception(type(e), e, e.__traceback__)))
            continue
        print(format(r))

if __name__ == "__main__":
    main()
