#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import subprocess
import configparser
from functools import reduce


class Repo(configparser.ConfigParser):
    """Класс описывает репозиторий и его основные методы
    (общие для всех репозиториев)"""

    def __init__(self, name, repo_dir):
        """Конструктор заполняет свойства класса. Как видно из кода имя файла
        индекса захардкожено"""
        super(Repo, self).__init__()
        self.NAME = name
        self.REPO_DIR = repo_dir
        self.read_file(open(os.path.join('', self.REPO_DIR, 'index.ini')))

    def list(self):
        """Функция возвращает список доступных в репозитории пакетов"""
        return ([name, self[name]['version']] for name in self.sections())

    def search(self, pkg_name):
        """Функция ищет пакет в репозитории, если находит возвращает версию"""
        try:
            return self[pkg_name]['version']
        except KeyError:
            return None

    def list_dependences(self, pkg_name):
        """Функция возвращает список зависимостей если они есть"""
        try:
            return self[pkg_name]['dependences'].replace(' ', '').split(",")
        except KeyError:
            return ()


class LocalRepo(Repo):
    """Частный вид репозитория, отличается от остальных тем что может
    изменяться из программы"""

    def __init__(self, repo_dir):
        """Конструктор локального репозиория. Имя задано в коде."""
        self.INDEX = os.path.join('', repo_dir, 'index.ini')
        try:
            super(LocalRepo, self).__init__('local', repo_dir)
        except FileNotFoundError:
            try:
                os.makedirs(self.REPO_DIR)  # Создана директория
            except FileExistsError:
                pass
            open(self.INDEX, 'w+').close()  # Создан пустой индекс
            super(LocalRepo, self).__init__('local', repo_dir)

    def list_update(self, repo):
        """Функция выводит список доступных для обновления пакетов"""
        return ([name, self[name]['version'], version]
            for name, version in repo.list()
            if name in self
            if self[name]['version'] < version)

    def write_index(self):
        """Запись содержимого локальной переменной в файл индекса"""
        with open(self.INDEX, 'w') as indexfile:
            self.write(indexfile)

    def change_index(self, action, pkg_name, repo=None):
        """Функция добавляет или удаляет запись о пакете в системной
        переменной(не в файле индекса) Первый аргумент это необходимое действие
        а второй имя пакета. Экземпляр класса Repo является необязательным для
        части операций"""

        if action == 'delete':               # Удаление записи о пакете
            del self[pkg_name]
        else:                     # Добавление записи о пакете или обновление
            try:
                CACHE_PKG = self[pkg_name]
            except KeyError:
                self[pkg_name] = {}
                CACHE_PKG = self[pkg_name]
            PKG = repo[pkg_name]

            CACHE_PKG['version'] = PKG['version']

            if 'file' in PKG:
                CACHE_PKG['file'] = PKG['file']
            elif action == 'update' and 'file' in CACHE_PKG:
                del self[pkg_name]['file']

            if 'dependences' in PKG:
                CACHE_PKG['dependences'] = PKG['dependences']
            elif action == 'update' and 'dependences' in CACHE_PKG:
                del self[pkg_name]['dependences']

    def pkg_download(self, pkg_name, repo):
        """Функция загружает пакет из репозитория в кэш"""
        pkg_file = repo[pkg_name]['file']
        pkg_version = repo[pkg_name]['version']
        src = os.path.join('', repo.REPO_DIR, pkg_file)
        dst = os.path.join('', self.REPO_DIR, pkg_name, pkg_version)

        try:
            os.makedirs(dst)
        except FileExistsError:
            shutil.rmtree(dst)
            os.makedirs(dst)

        shutil.unpack_archive(src, dst, 'zip')

    def run_script(self, soft_dir, action):
        """Запуск скрипта установки с набором ключей"""
        p = subprocess.call(['python',
            os.path.join('', soft_dir, 'script.py'),
            os.path.dirname(sys.argv[0]), action],
            shell=False, stdout=subprocess.PIPE, cwd=soft_dir)

    def pkg_install(self, pkg_name, repo):
        """Функция устанавливает пакет с указанным именем."""
        pkg_version = repo.search(pkg_name)
        if not pkg_version:
            return 1  # Нет такого пакета

        soft_dir = os.path.join('', self.REPO_DIR, pkg_name, pkg_version)

        def install():
            try:
                self.pkg_download(pkg_name, repo)
                self.run_script(soft_dir, 'install')
            except KeyError:
                pass

        cachepkg_version = self.search(pkg_name)
        if cachepkg_version:  # Если пакет уже установлен
            if cachepkg_version < pkg_version:
                install()
                self.change_index('update', pkg_name, repo)
                return 3  # Обновлён
            return 2  # Уже установлен
        else:
            install()
            self.change_index('write', pkg_name, repo)
            return 4  # Установлен

    def pkg_remove(self, pkg_name):
        """Функция удаляет ранее установленный пакет"""
        pkg_version = self.search(pkg_name)
        if pkg_version:              # Проверяем есть ли такой
            if 'file' in self[pkg_name]:
                soft_dir = os.path.join('', self.REPO_DIR, pkg_name,
                    pkg_version)
                try:
                    self.run_script(soft_dir, 'remove')
                except NotADirectoryError:
                    print("Кэшь повреждён!!")
                    sys.exit()
                except FileNotFoundError:
                    print("Кэшь повреждён!!")
                    sys.exit()
                shutil.rmtree(soft_dir)
            self.change_index('delete', pkg_name)
        else:
            return 1


class WpmErr(Exception):
    pass


class PackNameErr(WpmErr):

    def __init__(self, pkg_name):
        self.pkg_name = pkg_name


class MultiRepoCollision(WpmErr):

    def __init__(self, pkg_name, repos):
        self.pkg_name = pkg_name
        self.repos = repos


class WPM():
    """Класс описывает пакетный менеджер"""

    def __init__(self):
        self.localrepo, self.repos = self.read_config()

    def read_config(self):
        """Функция читает конфиг и инициализирует переменные"""
        repos = []

        CONF = os.path.join('', os.path.dirname(sys.argv[0]), 'config.ini')
        config = configparser.ConfigParser()
        try:
            config.read_file(open(CONF))
        except FileNotFoundError as e:
            print("Отсутствует конфигурационный файл!!\n%s" % e)
            sys.exit()

        try:
            for name in config['REPOSITORY']:
                try:
                    repos.append(Repo(name, config['REPOSITORY'][name]))
                except KeyError as e:
                    print("Отсутствует индекс репозитория %s\n%s"
                        % (self.NAME, e))
                    sys.exit()
                except FileNotFoundError as e:
                    print("Отсутствует файл индекса %s\n%s" % (self.NAME, e))
                    sys.exit()
        except KeyError as e:
            print('Не указан адрес репозитория!!\n%s' % e)
            sys.exit()

        try:
            localrepo = LocalRepo(config['CACHE']['dir'])
        except KeyError as e:
            print("Конфигурационный файл повреждён!! Не указан адрес кэша\n%s"
                % e)
            sys.exit()

        return localrepo, repos

    def table_print(self, title='', columns='', nextt=False):
        """Функция форматирует вывод в виде таблички"""

        space = lambda s, m: (s,
            " " * (m - len(s))) if len(s) <= m else (s[:m - 1], '')
        listmerge = lambda s: reduce(lambda d, el: d.extend(el) or d, s, [])
        maximum = shutil.get_terminal_size((80, 20))[0] - 1

        def cwidth(cn):
            "Функция вычисляет ширину каждого из столбцов"
            free = maximum - cn - 1
            tmp = int(free / cn)
            width = [tmp for n in range(cn)]
            if free % cn != 0:
                width[0] += free % cn
            return width

        if not nextt:
            print("-" * maximum)
        if title:
            print("|%s%s|" % space(title, maximum - 2))
            print("-" * maximum)
        if columns:
            sp = cwidth(len(columns[0]))
            for c in columns:
                print(("|%s%s" * len(columns[0]) + "|") %
                    tuple(listmerge(
                        [space(c[i], sp[i]) for i in range(len(c))])))
            print("-" * maximum)

    def list(self):
        self.table_print(title="Доступны следующие пакеты")
        for repo in self.repos:
            self.table_print(title=repo.NAME,
                columns=(('Пакет', 'Доступная версия'),), nextt=True)
            self.table_print(columns=tuple(repo.list()), nextt=True)

    def list_installed(self):
        self.table_print(title="Установлены следующие пакеты",
            columns=(("Пакет", "Текущая версия"),))
        self.table_print(columns=tuple(self.localrepo.list()), nextt=True)

    def list_update(self):
        self.table_print(title="Доступны следующие обновления.")
        for repo in self.repos:
            self.table_print(repo.NAME,
                columns=(("Пакет", "Текущая версия", "Доступная версия"),),
                nextt=True)
            self.table_print(title=repo.NAME,
                columns=tuple(self.localrepo.list_update(repo)),
                nextt=True)

    def check_pkg(self, pkg):
        """Функция проверяет есть ли пакет с таким именем и если есть то в
        скольких репозиториях. На данный момент наличие пакета в нескольких
        репозиториях рассматривается как ошибка"""
        pkg_in = [r for r in self.repos if r.search(pkg)]
        if len(pkg_in) == 0:
            raise PackNameErr(pkg)
        elif len(pkg_in) > 1:
            raise MultiRepoCollision(pkg, pkg_in)
        return pkg_in[0]

    def resolv_level_dependences(self, pkgs):
        """Если разложить зависимости в виде дерева вниз, то эта функция
        позволяет определить зависимости пакетов на один уровень вниз. Поиск
        ведётся рекурсивно"""
        listmerge = lambda s: reduce(lambda d, el: d.extend(el) or d, s, [])
        try:
            result = [self.check_pkg(pkg).list_dependences(pkg)
                for pkg in pkgs if self.check_pkg(pkg)]
        except PackNameErr as e:
            print("Пакет с именем %s не существует." % e.pkg_name)
            sys.exit()
        except MultiRepoCollision as e:
            print("Пакет с именем %s присутствует сразу в нескольких \
                репозиториях\n%s" % (e.pkg_name, e.repos))
            sys.exit()
        return listmerge(result)

    def resolv_dependences(self, pkgs):
        """Функция используяю предыдущую функцию поиска зависимостей на уровне,
        проходит вниз по дереву зависимостей, до тех пор пока все зависимости
        не будут найдены"""
        result = [].append(pkgs)
        dep = self.resolv_level_dependences(pkgs)
        while len(dep) > 0:
            result.append(dep)
            dep = self.resolv_level_dependences(dep)
        return list(set([d for i in result for d in i]))

    def remove(self, pkgs):
        """Функция удаляет пакеты переданные в кажестве аргумента"""
        for pkg in self.resolv_dependences(pkgs):
            if self.localrepo.pkg_remove(pkg):
                print("Пакет %s не найден!!" % pkg)
        self.localrepo.write_index()

    def install(self, pkgs):
        """Функция устанавливает пакеты переданные в качестве списка"""
        for pkg in self.resolv_dependences(pkgs):
            repo = self.check_pkg(pkg)
            res = self.localrepo.pkg_install(pkg, repo)
            if res == 1:
                print("Пакета %s не существует" % pkg)
            elif res == 2:
                print("Пакет %s уже установлен" % pkg)
            elif res == 3:
                print("Пакет %s обновлён" % pkg)
            elif res == 4:
                print("Пакет %s установлен" % pkg)
        self.localrepo.write_index()
