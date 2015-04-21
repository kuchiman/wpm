"""Версия 0.1"""
import os
import sys
import argparse
import configparser
from WinPackManager import Repo, LocalRepo


def read_config():
    """Функция читает конфиг и инициализирует переменные"""
    repos = []

    CONF = os.path.join('', os.path.dirname(sys.argv[0]) , 'config.ini')
    if not os.path.isfile(CONF):
        print('Отсутствует конфигурационный файл!!')
        raise SystemExit(1)

    config = configparser.ConfigParser()
    config.read(CONF)

    if 'REPOSITORY' in config:
        for name in config['REPOSITORY']:
            repos.append(Repo(name, config['REPOSITORY'][name]))
    else:
        print('Конфигурационный файл повреждён!! Не указан адрес репозитория')
        raise SystemExit(1)

    if 'CACHE' in config and 'dir' in config['CACHE']:
        localrepo = LocalRepo('local', config['CACHE']['dir'])
    else:
        print('Конфигурационный файл повреждён!! Не указан адрес кэша')
        raise SystemExit(1)

    return localrepo, repos


def show_config(repo):
    """Функция выводит переменные"""
    print("Имя репозитория " + repo.NAME)
    print("Адрес репозитория " + repo.REPO_DIR)
    print("Индекс репозитория " + repo.INDEX)
    print("Доступные пакеты")
    print(repo.list())


def pkgs_list(repos):
    print("-" * 80)
    print("\tДоступны следующие пакеты.")
    print("-" * 80)
    for repo in repos:
        print(repo.NAME)
        print("-" * 80)
        print("\tПакет\t\t\tДоступная версия")
        for pkg in repo.list():
            print("\t" + pkg[0] + "\t\t\t" + pkg[1])
        print("-" * 80)


def pkgs_list_installed(localrepo):
    print("-" * 80)
    print("\tУстановлены следующие пакеты.")
    print("-" * 80)
    print(localrepo.NAME)
    print("-" * 80)
    print("\tПакет\t\t\tТекущая версия")
    for pkg in localrepo.list():
        print("\t" + pkg[0] + "\t\t\t" + pkg[1])
    print("-" * 80)


def pkgs_list_updated(localrepo, repos):
    print("-" * 80)
    print("\tДоступны следующие обновления.")
    print("-" * 80)
    for repo in repos:
        print(repo.NAME)
        print("-" * 80)
        print("\tПакет\t\t\tТекущая версия\t\t\tДоступная версия")
        for pkg in localrepo.list_updated(repo):
            print("\t" + pkg[0] + "\t\t\t" + pkg[1] + "\t\t\t" + pkg[2])
        print("-" * 80)


def pkgs_remove(localrepo, pkgs):
    for pkg in pkgs:
        if localrepo.pkg_remove(pkg):
            print("Пакет " + pkg + " не найден!!")

    localrepo.write_index()


def pkgs_install(localrepo, repos, pkgs):
    for pkg in pkgs:
        pkg_in = []

        for r in repos:
            if r.search(pkg):
                pkg_in.append(r)

        if len(pkg_in) > 1:
            print("Пакет писутствует в нескольких репозиториях!!")
            for i in pkg_in:
                print(i.NAME + "\t\t" + pkg + "\t\t" + i.search(pkg)[1])
        elif len(pkg_in) == 0:
            print("Пакет " + pkg + " не найден")
        else:
            print("Пакет " + pkg + " устанавливается")
            localrepo.pkg_install(pkg, pkg_in[0])

    localrepo.write_index()


def createParser():
    """Функция строит парсер для разбора параметров запуска"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    list_parser = subparsers.add_parser('list')
    list_parser.add_argument('what',
        choices=['installed', 'updated'], nargs='?')

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
    localrepo, repos = read_config()

    if namespace.command == "list":
        if namespace.what is None:
            pkgs_list(repos)
        elif namespace.what == 'installed':
            pkgs_list_installed(localrepo)
        elif namespace.what == 'updated':
            pkgs_list_updated(localrepo, repos)
    elif namespace.command == "show":
        if namespace.what is None:
            show_config(localrepo)
    elif namespace.command == "install":
        pkgs_install(localrepo, repos, namespace.packages)
    elif namespace.command == "remove":
        pkgs_remove(localrepo, namespace.packages)