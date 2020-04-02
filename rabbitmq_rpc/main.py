# -*- coding: utf-8 -*-
import sys


def main():
    from rabbit_rpc.commands import ManageUtility

    manage = ManageUtility(sys.argv)
    manage.execute()


if __name__ == '__main__':
    main()
