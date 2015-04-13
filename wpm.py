import os
import sys
import argparse
import shutil
import subprocess
import configparser

REPO_DIR = ''                                 # Адрес сетевого репозитория
CACHE_DIR = ''                                # Адрес локального кэша

INDEX = ''                                    # Адрес индекса репозитория
CACHEINDEX = ''                               # Адрес локального индекса

PKGLIST = configparser.ConfigParser()         # Список доступных пакетов
CACHEPKGLIST = configparser.ConfigParser()    # Список установленных пакетов


class Repo():
    REPO_DIR = ''
    INDEX = ''
    PKGLIST = configparser.ConfigParser()

    def __init__(self, repo_dir):
        super(Repo, self).__init__()
        self.REPO_DIR = repo_dir
        self.INDEX = os.path.join('', REPO_DIR, 'index.ini')
        if self.repo_check() == 0:
            self.PKGLIST.read(INDEX)

    def repo_check(self):
        """Функция проверяет доступность директории с пакетами"""
        if not os.path.isdir(REPO_DIR):  # Репозиторий не доступен
            return 1
        elif not os.path.isfile(INDEX):  # Отсутствует индекс
            return 2
        else:  # Репозиторий доступен
            return 0

    def list(self):
        """Функция возвращает список доступных в репозитории пакетов"""
        PKGS = []
        for pkg_name in self.PKGLIST.sections():
            PKGS.append(pkg_name, self.PKGLIST[pkg_name]['version'])
        return PKGS


class LocalRepo(Repo):

    def __init__(self):
        super(LocalRepo, self).__init__()

    def repo_check(self):
        """Функция проверяет наличие файла индекса"""
        if not os.path.isdir(CACHE_DIR):
            os.makedirs(CACHE_DIR)          # Создана директория
            open(CACHEINDEX, 'w+').close()   # Создан пустой индекс
        else:
            if not os.path.isfile(CACHEINDEX):
                open(CACHEINDEX, 'w+').close()
        return 0

    def list_updated(self, repo):
        """Функция выводит список доступных для обновления пакетов"""
        PKGUP = []

        for pkg_name, pkg_version in repo.list():
            if pkg_name in self.PKGLIST:
                cachepkg_version = self.PKGLIST[pkg_name]['version']
                if cachepkg_version < pkg_version:
                    PKGUP.append(pkg_name, cachepkg_version,
                        pkg_version, repo.REPO_DIR)
        return PKGUP

    def write_index(self):
        """Запись локального файла индекса"""
        with open(INDEX, 'w') as indexfile:
            self.PKGLIST.write(indexfile)

    def change_index(self, action, pkg_name, repo=None):
        """Функция добавляет или удаляет запись о пакете в системной
        переменной(не в файле индекса) Первый аргумент это необходимое действие
        а второй запись о пакете вида ("имя", "версия")"""

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
        if pkg_name in self.PKGLIST:                  # Проверяем есть ли такой
            pkg_version = self.PKGLIST[pkg_name]['version']
        else:
            return 1

        soft_dir = os.path.join('', self.REPO_DIR, pkg_name, pkg_version)

        subprocess.call(['python', os.path.join('', soft_dir, 'script.py'),
            'remove'], shell=False, stdout=subprocess.PIPE, cwd=soft_dir)
        shutil.rmtree(soft_dir)
        self.change_index('delete', pkg_name)




def read_config():
    """Функция читает конфиг и инициализирует глобальные переменные"""

    global REPO_DIR, CACHE_DIR, INDEX, CACHEINDEX, PKGLIST, CACHEPKGLIST

    if not os.path.isfile('config.ini'):
        print('Отсутствует конфигурационный файл!!')
        raise SystemExit(1)

    config = configparser.ConfigParser()
    config.read('config.ini')

    if 'REPOSITORY' in config and 'dir' in config['REPOSITORY']:
        REPO_DIR = config['REPOSITORY']['dir']
    else:
        print('Конфигурационный файл повреждён!! Не указан адрес репозитория')
        raise SystemExit(1)

    if 'CACHE' in config and 'dir' in config['CACHE']:
        CACHE_DIR = config['CACHE']['dir']
    else:
        print('Конфигурационный файл повреждён!! Не указан адрес кэша')
        raise SystemExit(1)

    INDEX = os.path.join('', REPO_DIR, 'index.ini')
    CACHEINDEX = os.path.join('', CACHE_DIR, 'index.ini')

    repo_check()
    cache_check()

    PKGLIST.read(INDEX)
    CACHEPKGLIST.read(CACHEINDEX)


def show_config():
    """Функция выводит глобальные переменные"""
    print("Адрес репозитория " + REPO_DIR)
    print("Адрес кэша" + CACHE_DIR)
    print("Индекс репозитория" + INDEX)
    print("Индекс кэша" + CACHEINDEX)
    #print("Доступные пакеты" + PKGLIST.sectons())
    #print("Установленные пакеты" + CACHEPKGLIST.sectons())
    print("Доступные пакеты")
    print(PKGLIST.sections())
    print("Установленные пакеты")
    print(CACHEPKGLIST.sections())


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

    read_config()

    if namespace.command == "list":
        if namespace.what is None:
            pkgs_list()
        elif namespace.what == 'installed':
            pkgs_list_installed()
        elif namespace.what == 'updated':
            pkgs_list_updated()
    elif namespace.command == "show":
        if namespace.what is None:
            show_config()
    elif namespace.command == "install":
        pkgs_install(namespace.packages)
    elif namespace.command == "remove":
        pkgs_remove(namespace.packages)