# -*- coding: utf-8 -*-
from argparse import ArgumentParser
import sys


class BaseCommand(object):

    help = ''

    def __init__(self):
        self.arg_parser = ArgumentParser(prog=self.__class__.__name__)
        self.add_arguments(self.arg_parser)

    def add_arguments(self, parser):
        pass

    def print_help(self):
        self.arg_parser.print_help()

    def run_from_argv(self, *args):
        options = vars(self.arg_parser.parse_args(args))

        try:
            self.execute(**options)
        except Exception as ex:
            sys.stderr.write('%s: %s' % (self.__class__.__name__, ex))
            sys.exit(1)

    def execute(self, **options):
        pass
