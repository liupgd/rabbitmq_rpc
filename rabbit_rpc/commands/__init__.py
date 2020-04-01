# -*- coding: utf-8 -*-
from argparse import ArgumentParser
import sys


def get_commands():
    from .worker import Worker
    return {Worker.name: Worker()}


class ManageUtility(object):

    def __init__(self, argv=None):
        self.argv = argv

    def fetch_command(self, subcommand):
        commands = get_commands()
        try:
            return commands[subcommand]
        except KeyError:
            pass

    def execute(self):
        parser = ArgumentParser()
        parser.add_argument('worker', help='start a server worker')
        # parser.add_argument('call', help='send remote call')

        try:
            subcommand = self.argv[1]
            command = self.fetch_command(subcommand)
            if not command:
                parser.print_help()
                sys.stderr.write('Unkown subcommand: %s\n' % subcommand)
                sys.exit(1)
        except IndexError:
            parser.print_help()
            sys.exit()

        try:
            command = self.fetch_command(subcommand)
            command.run_from_argv(*self.argv[2:])
        except KeyboardInterrupt:
            pass
