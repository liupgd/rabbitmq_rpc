# -*- coding: utf-8 -*-
from __future__ import absolute_import

import importlib
import imp
import logging
import os
import sys
import traceback

import pika

from rabbit_rpc.consumer import Consumer
from rabbit_rpc.credentials import AliyunCredentialsProvider
from rabbit_rpc.server import RPCServer
from .base import BaseCommand

logger = logging.getLogger(__name__)


class Worker(BaseCommand):

    name = 'worker'

    def add_arguments(self, parser):
        parser.add_argument(
            '-Q',
            '--queue',
            default='default',
            help='setup and bind to the specified queue')
        parser.add_argument(
            '--amqp',
            default='amqp://guest:guest@localhost:5672/',
            help='specify the broker url')
        parser.add_argument(
            '--django', help='setup django')
        parser.add_argument(
            '--alicert', help='''
            specify the certification of aliyun amqp in format:

            [access_key]:[access_secret]:[resource_owner_id]
            ''')

    def install_django(self, project_name):
        import django

        os.environ['DJANGO_SETTINGS_MODULE'] = project_name + '.settings'
        django.setup()

    def parse_aliyun_cert(self, raw_cert):
        try:
            access_key, access_secret, resource_owner_id = raw_cert.split(':')
        except ValueError:
            raise ValueError('invalid alicert')

        provider = AliyunCredentialsProvider(
            access_key, access_secret, resource_owner_id)

        return provider.get_username(), provider.get_password()

    def find_consumers(self, related_name='consumers'):
        path = os.getcwd()
        logger.info('Finding consumers...')

        consumers = []
        for dirpath in os.listdir(path):
            if dirpath.startswith('.'):
                continue

            if os.path.isdir(dirpath):
                try:
                    module = find_related_module(dirpath, related_name)
                    if module:
                        for item in dir(module):
                            c = getattr(module, item)
                            if isinstance(c, Consumer):
                                logger.info('[Consumer] %s.%s.%s', dirpath,
                                            related_name, c.name)
                                consumers.append(c)
                except ImportError:
                    pass

        return consumers

    def execute(self, **options):
        sys.path.append(os.getcwd())

        try:
            conn_parameters = pika.URLParameters(options['amqp'])

            if options.get('django'):
                self.install_django(options['django'])

            if options.get('alicert'):
                username, password = self.parse_aliyun_cert(options['alicert'])
                conn_parameters.credentials = pika.PlainCredentials(
                    username, password, erase_on_connect=True)

            consumers = self.find_consumers()
            if not consumers:
                sys.stderr.write('No consumer was detected.\n')
                sys.exit(1)

            server = RPCServer(
                consumers = consumers, conn_parameters=conn_parameters,
                queue_name=options['queue'])
            server.run()
        except KeyboardInterrupt:
            server.stop()
        except Exception:
            traceback.print_exc()
            sys.exit(1)


def find_related_module(package, related_name):
    """Find module in package."""
    try:
        importlib.import_module(package)
    except ImportError:
        package, _, _ = package.rpartition('.')
        if not package:
            raise

    try:
        pkg_path = importlib.import_module(package).__path__
    except AttributeError:
        return

    if not isinstance(pkg_path, list):
        pkg_path = pkg_path._path

    try:
        imp.find_module(related_name, pkg_path)
    except ImportError:
        return

    return importlib.import_module('{0}.{1}'.format(package, related_name))
