import os
import sys
import shutil
import subprocess
import configparser


class Repo(configparser.ConfigParser):
    """Класс описывает репозиторий и его основные методы
    (общие для всех репозиториев)"""

    def __init__(self, name, repo_dir):
        """Конструктор заполняет свойства класса. Как видно из кода имя файла
        индекса захардкожено"""
        super(Repo, self).__init__()
        self.NAME = name
        self.REPO_DIR = repo_dir
        self.read(os.path.join('', self.REPO_DIR, 'index.ini'))

    def list(self):
        """Функция возвращает список доступных в репозитории пакетов"""
        return [[name, self[name]['version']] for name in self.sections()]

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
            return []


class LocalRepo(Repo):
    """Частный вид репозитория, отличается от остальных тем что может
    изменяться из программы"""
    def __init__(self, name, repo_dir):
        super(LocalRepo, self).__init__(name, repo_dir )
        self.INDEX = os.path.join('', self.REPO_DIR, 'index.ini')
        try:
            self.read(self.INDEX)
        except NameError:
            try:
                os.makedirs(self.REPO_DIR)  # Создана директория
            except FileExistsError:
                pass
            open(self.INDEX, 'w+').close()  # Создан пустой индекс
            self.read(self.INDEX)

    def list_update(self, repo):
        """Функция выводит список доступных для обновления пакетов"""
        return [[name, self[name]['version'], version]
            for name, version in repo.list()
            if name in self
            if self[name]['version'] < version]

    def write_index(self):
        """Запись содержимого локальной переменной в файл индекса"""
        with open(self.INDEX, 'w') as indexfile:
            self.write(indexfile)

    def change_index(self, action, pkg_name, repo=None):
        """Функция добавляет или удаляет запись о пакете в системной
        переменной(не в файле индекса) Первый аргумент это необходимое действие
        а второй имя пакета. Экземпляр класса Repo является необязательным для
        части операций"""
        try:
            CACHE_PKG = self[pkg_name]
        except KeyError:
            self[pkg_name] = {}
            CACHE_PKG = self[pkg_name]

        if action == 'delete':               # Удаление записи о пакете
            del CACHE_PKG
        else:                     # Добавление записи о пакете или обновление
            PKG = repo[pkg_name]
            CACHE_PKG['version'] = PKG['version']

            if 'file' in PKG:
                CACHE_PKG['file'] = PKG['file']
            elif action == 'update' and 'file' in CACHE_PKG:
                del CACHE_PKG['file']

            if 'dependences' in PKG:
                CACHE_PKG['dependences'] = PKG['dependences']
            elif action == 'update' and 'dependences' in CACHE_PKG:
                del CACHE_PKG['dependences']

    def pkg_download(self, pkg_name, repo):
        """Функция загружает пакет из репозитория в кэш"""
        pkg_version = repo[pkg_name]['version']
        pkg_file = repo[pkg_name]['file']
        src = os.path.join('', repo.REPO_DIR, pkg_file)
        dst = os.path.join('', self.REPO_DIR, pkg_name, pkg_version)

        try:
            os.makedirs(dst)
        except FileExistsError:
            shutil.rmtree(dst)
            os.makedirs(dst)

        shutil.unpack_archive(src, dst, 'zip')

    def run_script(self, soft_dir, action):
        """Запуск скрипта с набором ключей"""
        p = subprocess.call(['python',
            os.path.join('', soft_dir, 'script.py'), action],
            shell=False, stdout=subprocess.PIPE, cwd=soft_dir)

    def pkg_install(self, pkg_name, repo):
        """Функция устанавливает пакет с указанным именем."""
        pkg_version = repo.search(pkg_name)
        if not pkg_version:
            return 1

        soft_dir = os.path.join('', self.REPO_DIR, pkg_name, pkg_version)

        cachepkg_version = self.search(pkg_name)
        if cachepkg_version:  # Если пакет уже установлен
            if cachepkg_version < pkg_version:
                self.pkg_download(pkg_name, repo)
                self.run_script(soft_dir, 'install')
                self.change_index('update', pkg_name, repo)
                return 3  # Обновлён
            return 2  # Уже установлен
        else:
            if 'file' in repo[pkg_name]:
                self.pkg_download(pkg_name, repo)
                self.run_script(soft_dir, 'install')
            self.change_index('write', pkg_name, repo)
            return 4  # Установлен

    def pkg_remove(self, pkg_name):
        """Функция удаляет ранее установленный пакет"""
        pkg_version = self.search(pkg_name)
        if pkg_version:              # Проверяем есть ли такой
            if 'file' in self[pkg_name]:
                soft_dir = os.path.join('', self.REPO_DIR, pkg_name, pkg_version)
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

    def __init__(self):
        self.localrepo, self.repos = self.read_config()

    def read_config(self):
        """Функция читает конфиг и инициализирует переменные"""
        repos = []

        CONF = os.path.join('', os.path.dirname(sys.argv[0]), 'config.ini')
        config = configparser.ConfigParser()
        try:
            config.read(CONF)
        except NameError as e:
            print("Отсутствует конфигурационный файл!!")
            print(e)
            sys.exit()

        try:
            for name in config['REPOSITORY']:
                try:
                    repos.append(Repo(name, config['REPOSITORY'][name]))
                except KeyError as e:
                    print("Отсутствует индекс репозитория " + self.NAME)
                    print(e)
                    sys.exit()
        except KeyError as e:
            print('Не указан адрес репозитория!!')
            print(e)
            sys.exit()

        try:
            localrepo = LocalRepo('local', config['CACHE']['dir'])
        except KeyError as e:
            print("Конфигурационный файл повреждён!! Не указан адрес кэша")
            print(e)
            sys.exit()

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
            for pkg in self.localrepo.list_update(repo):
                print("\t" + pkg[0] + "\t\t\t" + pkg[1] + "\t\t\t" + pkg[2])
            print("-" * 80)

    def check_pkg(self, pkg):
        """Функция проверяет есть ли пакет с таким именем и если есть то в
        скольких репозиториях. На данный момент наличие пакета в нескольких
        репозиториях рассматривается как ошибка"""
        pkg_in = []
        for r in self.repos:
            if r.search(pkg):
                pkg_in.append(r)
        if len(pkg_in) == 0:
            raise PackNameErr(pkg)
        elif len(pkg_in) > 1:
            raise MultiRepoCollision(pkg, pkg_in)
        return pkg_in[0]

    #def list_dependences(self, pkgs):
        #for pkg in pkgs:
            #for r in self.repos:
                #if r.search(pkg):

    def resolv_level_dependences(self, pkgs):
        """Если разложить зависимости в виде дерева вниз, то эта функция
        позволяет определить зависимости пакетов на один уровень вниз. Поиск
        ведётся рекурсивно"""
        result = []
        for pkg in pkgs:
            try:
                repo = self.check_pkg(pkg)
                result.extend(repo.list_dependences(pkg))
            except PackNameErr as e:
                print("Пакет с именем " + e.pkg_name + " не существует.")
                sys.exit()
            except MultiRepoCollision as e:
                print("Пакет с именем " + e.pkg_name +
                    " присутствует сразу в нескольких репозиториях")
                print(e.repos)
                sys.exit()
        return result

    def resolv_dependences(self, pkgs):
        """Функция использяю предыдущую функцию поиска зависимостей на уровне,
        проходит вниз по дереву зависимостей, до тех пор пока все зависимости
        не будут найдены"""
        result = []
        result.append(pkgs)
        dep = self.resolv_level_dependences(pkgs)
        while len(dep) > 0:
            result.append(dep)
            dep = self.resolv_level_dependences(dep)
        return list(set([d for i in result for d in i]))

    def remove(self, pkgs):
        """Функция удаляет пакеты переданные в кажестве аргумента"""
        dep = self.resolv_dependences(pkgs)
        for pkg in dep:
            if self.localrepo.pkg_remove(pkg):
                print("Пакет " + pkg + " не найден!!")
        self.localrepo.write_index()

    def install(self, pkgs):
        """Функция устанавливает пакеты переданные в качестве списка"""
        dep = self.resolv_dependences(pkgs)
        for pkg in dep:
            repo = self.check_pkg(pkg)
            if pkg in self.localrepo:
                print("Пакет " + pkg + " уже установлен")
            else:
                print("Пакет " + pkg + " устанавливается")
                self.localrepo.pkg_install(pkg, repo)
        self.localrepo.write_index()