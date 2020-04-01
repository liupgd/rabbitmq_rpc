# -*- coding: utf-8 -*-
import logging
import sys

from .client import RPCClient
from .server import RPCServer
from .consumer import consumer, Consumer
from .credentials import AliyunCredentialsProvider

LOG_FORMAT = (
    '%(levelname)s %(asctime)s %(name)s %(funcName)s %(lineno)s: %(message)s')
logging.basicConfig(level=logging.ERROR, format=LOG_FORMAT)

__all__ = [
    'consumer', 'Consumer', 'RPCClient', 'RPCServer',
    'AliyunCredentialsProvider'
]


def main():
    from rabbit_rpc.commands import ManageUtility
    manage = ManageUtility(sys.argv)
    manage.execute()

if __name__ == '__main__':
    main()
