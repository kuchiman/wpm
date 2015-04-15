import os
import shutil
import subprocess
import configparser


class Repo():
    NAME = ''
    REPO_DIR = ''
    INDEX = ''
    PKGLIST = configparser.ConfigParser()

    def __init__(self, name, repo_dir):
        super(Repo, self).__init__()
        self.REPO_DIR = repo_dir
        self.NAME = name
        self.INDEX = os.path.join('', self.REPO_DIR, 'index.ini')
        if self.repo_check() == 0:
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
        if pkg_name in self.PKGLIST:
            return pkg_name, self.PKGLIST[pkg_name]['version']
        return 0


class LocalRepo(Repo):
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
                    PKGUP.append(pkg_name, cachepkg_version,
                        pkg_version)
        return PKGUP

    def write_index(self):
        """Запись локального файла индекса"""
        with open(self.INDEX, 'w') as indexfile:
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
            soft_dir = os.path.join('', self.REPO_DIR, pkg_name, pkg_version)

            subprocess.call(['python', os.path.join('', soft_dir, 'script.py'),
            'remove'], shell=False, stdout=subprocess.PIPE, cwd=soft_dir)
            shutil.rmtree(soft_dir)
            self.change_index('delete', pkg_name)
        else:
            return 1