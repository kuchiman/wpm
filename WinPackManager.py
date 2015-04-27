import os
import sys
import shutil
import subprocess
import configparser


class Repo():
    """Класс описывает репозиторий и его основные методы
    (общие для всех репозиториев)"""
    def __init__(self, name, repo_dir):
        """Конструктор заполняет свойства класса. Как видно из кода имя файла
        индекса захардкожено"""
        self.NAME = name
        self.REPO_DIR = repo_dir
        self.INDEX = os.path.join('', self.REPO_DIR, 'index.ini')
        if self.repo_check() == 0:
            self.PKGLIST = configparser.ConfigParser()
            self.PKGLIST.read(self.INDEX)

    def __repr__(self):
        return self.NAME

    def __str__(self):
        return self.NAME

    def repo_check(self):
        """Функция проверяет доступность директории с пакетами"""
        if not os.path.isdir(self.REPO_DIR):  # Репозиторий не доступен
            return 1
        elif not os.path.isfile(self.INDEX):  # Отсутствует индекс
            return 2
        else:                                 # Репозиторий доступен
            return 0

    def list(self):
        """Функция возвращает список доступных в репозитории пакетов"""
        PKGS = []
        for pkg_name in self.PKGLIST.sections():
            PKGS.append((pkg_name, self.PKGLIST[pkg_name]['version']))
        return PKGS

    def search(self, pkg_name):
        """Функция ищет пакет в репозитории, если находит возвращает имя
        и версию"""
        if pkg_name in self.PKGLIST:
            return pkg_name, self.PKGLIST[pkg_name]['version']
        return 0


class LocalRepo(Repo):
    """Частный вид репозитория, отличается от остальных тем что может
    изменяться из программы"""
    def repo_check(self):
        """Функция проверяет наличие файла индекса"""
        if not os.path.isdir(self.REPO_DIR):
            os.makedirs(self.REPO_DIR)           # Создана директория
            open(self.INDEX, 'w+').close()   # Создан пустой индекс
        else:
            if not os.path.isfile(self.INDEX):
                open(self.INDEX, 'w+').close()
        return 0

    def list_updated(self, repo):
        """Функция выводит список доступных для обновления пакетов"""
        PKGUP = []
        for pkg_name, pkg_version in repo.list():
            if pkg_name in self.PKGLIST:
                cachepkg_version = self.PKGLIST[pkg_name]['version']
                if cachepkg_version < pkg_version:
                    PKGUP.append(pkg_name, cachepkg_version, pkg_version)
        return PKGUP

    def write_index(self):
        """Запись содержимого локальной переменной в файл индекса"""
        with open(self.INDEX, 'w') as indexfile:
            self.PKGLIST.write(indexfile)

    def change_index(self, action, pkg_name, repo=None):
        """Функция добавляет или удаляет запись о пакете в системной
        переменной(не в файле индекса) Первый аргумент это необходимое действие
        а второй имя пакета. Экземпляр класса Repo является необязательным для
        части операций"""

        if action == 'delete':               # Удаление записи о пакете
            del self.PKGLIST[pkg_name]
        elif action == 'write':              # Добавление записи о пакете
            self.PKGLIST[pkg_name] = {}
            self.PKGLIST[pkg_name]['version'] = repo.PKGLIST[pkg_name]['version']
            self.PKGLIST[pkg_name]['file'] = repo.PKGLIST[pkg_name]['file']
        elif action == 'update':             # Обновление записи о пакете
            self.PKGLIST[pkg_name]['version'] = repo.PKGLIST[pkg_name]['version']
            self.PKGLIST[pkg_name]['file'] = repo.PKGLIST[pkg_name]['file']

    def pkg_download(self, pkg_name, repo):
        """Функция загружает пакет из репозитория в кэш"""
        pkg_version = repo.PKGLIST[pkg_name]['version']
        pkg_file = repo.PKGLIST[pkg_name]['file']
        src = os.path.join('', repo.REPO_DIR, pkg_file)
        name_dir = os.path.join('', self.REPO_DIR, pkg_name)
        dst = os.path.join('', name_dir, pkg_version)

        if not os.path.isdir(name_dir):
            # Если директория для пакета не существует
            os.makedirs(name_dir)
            os.makedirs(dst)
        elif os.path.isdir(name_dir) and not os.path.isdir(dst):
            # Если директория существует но нет директории с номером версии
            print(os.path.isdir(name_dir) and not os.path.isdir(dst))
            os.makedirs(dst)
        else:  # Если путь существует значит там что то лежит, удалить всё
            shutil.rmtree(dst)
            os.makedirs(dst)

        shutil.unpack_archive(src, dst, 'zip')

    def pkg_install(self, pkg_name, repo):
        """Функция устанавливает пакет с указанным именем."""
        if pkg_name in self.PKGLIST:
            cachepkg_version = self.PKGLIST[pkg_name]['version']
        else:
            cachepkg_version = '0'

        if pkg_name in repo.PKGLIST:   # Проверяем есть ли такой в репах
            pkg_version = repo.PKGLIST[pkg_name]['version']
        else:
            return 1

        soft_dir = os.path.join('', self.REPO_DIR, pkg_name, pkg_version)

        # Проверка не установлен ли уже пакет
        if pkg_name in self.PKGLIST:
            if cachepkg_version == pkg_version:
                return 2  # Уже установлен
            elif cachepkg_version < pkg_version:
                self.pkg_download(pkg_name, repo)
                p = subprocess.call(['python',
                    os.path.join('', soft_dir, 'script.py'), 'install'],
                    shell=False, stdout=subprocess.PIPE, cwd=soft_dir)
                self.change_index('update', pkg_name, repo)
                return 3  # Обновлён
        else:
            print("Пакет будет установлен")
            self.pkg_download(pkg_name, repo)
            p = subprocess.call(['python',
                os.path.join('', soft_dir, 'script.py'), 'install'],
                shell=False, stdout=subprocess.PIPE, cwd=soft_dir)
            self.change_index('write', pkg_name, repo)
            return 4  # Установлен

    def pkg_remove(self, pkg_name):
        """Функция удаляет ранее установленный пакет"""
        if pkg_name in self.PKGLIST:             # Проверяем есть ли такой
            pkg_version = self.PKGLIST[pkg_name]['version']
            soft_dir = os.path.join('', self.REPO_DIR, pkg_name, pkg_version)

            subprocess.call(['python', os.path.join('', soft_dir, 'script.py'),
            'remove'], shell=False, stdout=subprocess.PIPE, cwd=soft_dir)
            shutil.rmtree(soft_dir)
            self.change_index('delete', pkg_name)
        else:
            return 1


class WPM():

    def __init__(self):
        self.localrepo, self.repos = self.read_config()

    def read_config(self):
        """Функция читает конфиг и инициализирует переменные"""
        repos = []

        CONF = os.path.join('', os.path.dirname(sys.argv[0]), 'config.ini')
        if not os.path.isfile(CONF):
            print('Отсутствует конфигурационный файл!!')
            raise SystemExit(1)

        config = configparser.ConfigParser()
        config.read(CONF)

        if 'REPOSITORY' in config:
            for name in config['REPOSITORY']:
                repos.append(Repo(name, config['REPOSITORY'][name]))
        else:
            print('Не указан адрес репозитория!!')
            raise SystemExit(1)

        if 'CACHE' in config and 'dir' in config['CACHE']:
            localrepo = LocalRepo('local', config['CACHE']['dir'])
        else:
            print('Конфигурационный файл повреждён!! Не указан адрес кэша')
            raise SystemExit(1)

        return localrepo, repos

    def list(self):
        print("-" * 80)
        print("\tДоступны следующие пакеты.")
        print("-" * 80)
        for repo in self.repos:
            print(repo.NAME)
            print("-" * 80)
            print("\tПакет\t\t\tДоступная версия")
            for pkg in repo.list():
                print("\t" + pkg[0] + "\t\t\t" + pkg[1])
            print("-" * 80)

    def list_installed(self):
        print("-" * 80)
        print("\tУстановлены следующие пакеты.")
        print("-" * 80)
        print(self.localrepo.NAME)
        print("-" * 80)
        print("\tПакет\t\t\tТекущая версия")
        for pkg in self.localrepo.list():
            print("\t" + pkg[0] + "\t\t\t" + pkg[1])
        print("-" * 80)

    def list_update(self):
        print("-" * 80)
        print("\tДоступны следующие обновления.")
        print("-" * 80)
        for repo in self.repos:
            print(repo.NAME)
            print("-" * 80)
            print("\tПакет\t\t\tТекущая версия\t\t\tДоступная версия")
            for pkg in self.localrepo.list_updated(repo):
                print("\t" + pkg[0] + "\t\t\t" + pkg[1] + "\t\t\t" + pkg[2])
            print("-" * 80)

    def remove(self, pkgs):
        for pkg in pkgs:
            if self.localrepo.pkg_remove(pkg):
                print("Пакет " + pkg + " не найден!!")

        self.localrepo.write_index()

    def install(self, pkgs):
        for pkg in pkgs:
            pkg_in = []

            for r in self.repos:
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
                self.localrepo.pkg_install(pkg, pkg_in[0])

        self.localrepo.write_index()