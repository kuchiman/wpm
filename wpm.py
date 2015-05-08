import sys
import argparse
from WinPackManager import WPM
#  dependence branch


wpm = WPM()


def createParser():
    """Функция строит парсер для разбора параметров запуска"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    list_parser = subparsers.add_parser('list')
    list_parser.add_argument('what',
        choices=['installed', 'update'], nargs='?')

    install_parser = subparsers.add_parser('install')
    install_parser.add_argument('packages', nargs='+')

    remove_parser = subparsers.add_parser('remove')
    remove_parser.add_argument('packages', nargs='+')

    show_parser = subparsers.add_parser('show')
    show_parser.add_argument('what',
        choices=['config'], nargs='?')

    return parser


if __name__ == "__main__":
    parser = createParser()
    namespace = parser.parse_args(sys.argv[1:])

    if namespace.command == "list":
        if namespace.what is None:
            wpm.list()
        elif namespace.what == 'installed':
            wpm.list_installed()
        elif namespace.what == 'update':
            wpm.list_update()
    elif namespace.command == "show":
        if namespace.what is None:
            #show_config(localrepo)
            pass
    elif namespace.command == "install":
        wpm.install(namespace.packages)
    elif namespace.command == "remove":
        wpm.remove(namespace.packages)