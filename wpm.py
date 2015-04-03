import os, sys, re, argparse, shutil, subprocess, configparser

REPO_DIR = ''                                 # Адрес сетевого репозитория
CACHE_DIR = ''                                # Адрес локального кэша

INDEX = ''                                    # Адрес индекса репозитория
CACHEINDEX = ''                               # Адрес локального индекса

PKGLIST = configparser.ConfigParser()         # Список доступных пакетов
CACHEPKGLIST = configparser.ConfigParser()    # Список установленных пакетов


def repo_check():
    """Функция проверяет доступность директории с пакетами"""
    if not os.path.isdir(REPO_DIR):
        print(REPO_DIR + 'Репозиторий не доступен!!')
        raise SystemExit(1)
    elif not os.path.isfile(INDEX):
        print('Отсутствует индекс!!')
        raise SystemExit(1)
    else:
        print('Репозиторий доступен...')


def cache_check():
    """Функция проверяет наличие файла индекса"""
    if not os.path.isdir(CACHE_DIR):
        os.makedirs(CACHE_DIR)          # Создана директория
        open(CACHEINDEX, 'a').close()   # Создан пустой индекс
        print('Кэш создан...')
    else:
        if not os.path.isfile(CACHEINDEX):
            open(CACHEINDEX, 'a').close()
            print("Создан индекс...")
    print('Кэш доступен...')


def read_config():
    """Функция читает конфиг и инициализирует глобальные переменные"""

    global REPO_DIR, CACHE_DIR, INDEX, CACHEINDEX, PKGLIST, CACHEPKGLIST

    if not os.path.isfile('config.ini'):
        print('Отсутствует конфигурационный файл!!')
        raise SystemExit(1)

    config = configparser.ConfigParser()
    config.read('config.ini')

    if config.has_section('REPOSITORY') and config.has_option('REPOSITORY', 'dir'):
        REPO_DIR = config.get('REPOSITORY', 'dir')
    else:
        print('Конфигурационный файл повреждён!! Не указан адрес репозитория')
        raise SystemExit(1)

    if config.has_section('CACHE') and config.has_option('CACHE', 'dir'):
        CACHE_DIR = config.get('CACHE', 'dir')
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
    print("Доступные пакеты" + type(PKGLIST))
    print("Установленные пакеты" + type(CACHEPKGLIST))


def change_index(action, pkg_name):
    """Функция добавляет или удаляет запись о пакете в системной
    переменной(не в файле индекса) Первый аргумент это необходимое действие
    а второй запись о пакете вида ("имя", "версия")"""
    global CACHEPKGLIST

    if action == 'delete':  # Удаление записи о пакете
        CACHEPKGLIST.remove_section(pkg_name)
    elif action == 'write':              # Добавление записи о пакете
        CACHEPKGLIST.add_section(pkg_name)
        CACHEPKGLIST.set(pkg_name, 'version',
            PKGLIST.get(pkg_name, 'version'))
        CACHEPKGLIST.set(pkg_name, 'file', PKGLIST.get(pkg_name, 'file'))
    elif action == 'update':             # Обновление записи о пакете
        CACHEPKGLIST.set(pkg_name, 'version',
            PKGLIST.get(pkg_name, 'version'))
        CACHEPKGLIST.set(pkg_name, 'file', PKGLIST.get(pkg_name, 'file'))


def write_index():
    """Запись локального файла индекса"""
    with open(CACHEINDEX, 'wb') as indexfile:
        CACHEPKGLIST.write(indexfile)


def pkgs_list():
    """Функция выводит список доступных в репозитории пакетов"""
    print("\n\nИмя       \t\t\t| Версия")
    for pkg_name in PKGLIST.sections():
        print(pkg_name + "\t\t\t| " + PKGLIST.get(pkg_name, 'version'))


def pkgs_list_installed():
    """Функция выводит список установленных пакетов"""
    print("\n\nИмя       \t\t\t| Версия")
    for pkg_name in CACHEPKGLIST.sections():
        print(pkg_name + "\t\t\t| " + CACHEPKGLIST.get(pkg_name, 'version'))


def pkgs_list_updated():
    """Функция выводит список установленных пакетов"""
    print("\n\nИмя       \t\t\t| Установлено   \t| Доступно     \t")
    for pkg_name in CACHEPKGLIST.sections():
        if PKGLIST.has_section(pkg_name):
            cachepkg_version = CACHEPKGLIST.get(pkg_name, 'version')
            pkg_version = PKGLIST.get(pkg_name, 'version')
            if cachepkg_version < pkg_version:
                print(pkg_name + "\t\t\t| " +
                    cachepkg_version + "\t| " + pkg_version)


def pkg_download(pkg_name):
    """Функция загружает пакет из репозитория в кэш"""
    pkg_version = PKGLIST.get(pkg_name, 'version')
    pkg_file = PKGLIST.get(pkg_name, 'file')
    src = os.path.join('', REPO_DIR, pkg_file)
    name_dir = os.path.join('', CACHE_DIR, pkg_name)
    dst = os.path.join('', name_dir, pkg_version)

    if not os.path.isdir(name_dir):  # Если директория для пакета не существует
        os.makedirs(name_dir)
        os.makedirs(dst)
    elif os.path.isdir(name_dir) and not os.path.isdir(dst):  # Если директория
        print(os.path.isdir(name_dir) and not os.path.isdir(dst))  # существует
        os.makedirs(dst)                  # но нет директории с номером версии
    else:       # Если путь существует значит там что то лежит, удалить всё
        shutil.rmtree(dst)
        os.makedirs(dst)

    shutil.unpack_archive(src, dst, 'zip')


def pkg_install(pkg_name):
    """Функция устанавливает пакет с указанным именем."""
    if CACHEPKGLIST.has_section(pkg_name):
        cachepkg_version = CACHEPKGLIST.get(pkg_name, 'version')
    else:
        cachepkg_version = '0'

    if PKGLIST.has_section(pkg_name):         # Проверяем есть ли такой в репах
        pkg_version = PKGLIST.get(pkg_name, 'version')  # Какая версия в репах
    else:
        print(pkg_name + " Пакет с таким именет отсутствует!!")
        return 0

    # Проверка не установлен ли уже пакет
    if CACHEPKGLIST.has_section(pkg_name):
        if cachepkg_version == pkg_version:
            print(pkg_name + " Пакет уже установлен и это последняя версия!!")
            return 0
        elif cachepkg_version < pkg_version:
            print("Пакет будет обновлён")
            pkg_download(pkg_name, pkg_version)
            p = subprocess.call(['python',
                os.path.join('', CACHE_DIR, pkg_name, pkg_version, 'script.py'),
                'install'], stdout=subprocess.PIPE)
            change_index('update', pkg_name)
    else:
        print("Пакет будет установлен")
        pkg_download(pkg_name)
        p = subprocess.call(['python',
            os.path.join('', CACHE_DIR, pkg_name, pkg_version, 'script.py'),
            'install'], stdout=subprocess.PIPE)
        change_index('write', pkg_name)


def pkgs_install(packages):
    """Функция групповой установки пакетов"""
    for pkg_name in packages:
        pkg_install(pkg_name)
    write_index()


def pkg_remove(pkg_name):
    """Функция удаляет ранее установленный пакет"""
    if CACHEPKGLIST.has_section(pkg_name):  # Проверяем есть ли такой
        pkg_version = CACHEPKGLIST.get(pkg_name, 'version')
    else:
        print(pkg_name + " Пакет с таким именет отсутствует!!")
        return 0

    subprocess.call(['python',
        os.path.join('', CACHE_DIR, pkg_name, pkg_version, 'script.py'),
        'remove'], shell=True, stdout=subprocess.PIPE)
    shutil.rmtree(os.path.join('', CACHE_DIR, pkg_name, pkg_version))
    change_index('delete', pkg_name)


def pkgs_remove(packages):
    """Функция группового удаления"""
    for pkg_name in packages:
        pkg_remove(pkg_name)
    write_index()


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