# -*- coding: utf-8 -*-

ERROR_FLAG = 'error'
NO_ERROR = 0
HAS_ERROR = 1


class RemoteFunctionError(Exception):
    pass


class RemoteCallTimeout(Exception):
    pass
