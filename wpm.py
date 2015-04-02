import os, sys, re, argparse, shutil, subprocess, configparser

REPO_DIR = ''            # Адрес сетевого репозитория
CACHE_DIR = ''           # Адрес локального кэша

INDEX = ''               # Адрес индекса репозитория
CACHEINDEX = ''          # Адрес локального индекса

PKGLIST = []             # Список доступных пакетов
CACHEPKGLIST = []        # Список установленных пакетов


def read_index(index):
    """Функция читает индекс и возвращает массив"""
    f = open(index, "r")
    pkgs_re = re.compile('(?:name=)([a-zA-Z0-9_-]+.pkg)(?: +version=)([0-9.]+)(?: *)')
    tmp = f.read()
    f.close()
    return pkgs_re.findall(tmp)


def read_config():
    """Функция читает конфиг и инициализирует глобальные переменные"""
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

    INDEX = os.path.join('', REPO_DIR, 'index.txt')
    CACHEINDEX = os.path.join('', CACHE_DIR, 'index.txt')

    PKGLIST = read_index(INDEX)
    CACHEPKGLIST = read_index(CACHEINDEX)

    print(REPO_DIR)
    print(CACHE_DIR)
    print(INDEX)
    print(CACHEINDEX)


def repo_check():
    print(REPO_DIR)
    print(CACHE_DIR)
    print(INDEX)
    print(CACHEINDEX)
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
    elif not os.path.isfile(CACHEINDEX):
        open(CACHEINDEX, 'a').close()
    else:
        print('Кэш доступен...')


def search_in_index(index, name):
    """Функция ищет в списке пакетов пакет с именем указанным во втором
    параметре Возвращает индекс элемента в списке или если элемент не найдет
    то отрицательное значение"""
    for i in index:
        if name == i[0]:
            return index.index(i)
    return -1


def change_index(action, changes):
    """Функция добавляет или удаляет запись о пакете в системной
    переменной(не в файле индекса) Первый аргумент это необходимое действие
    а второй запись о пакете вида ("имя", "версия")"""
    tmp = search_in_index(CACHEPKGLIST, changes[0])

    if action == 'd' and tmp >= 0:
        del CACHEPKGLIST[tmp]
    elif action == 'w':
        if tmp >= 0:
            CACHEPKGLIST[tmp] = changes
        else:
            CACHEPKGLIST.append(changes)


def write_index():
    """Запись локального файла индекса"""
    f = open(CACHEINDEX, "w")

    for i in CACHEPKGLIST:
        if len(i) != 0:
            f.write("name=" + i[0] + " version=" + i[1] + "\n")
    f.close()


def pkgs_list():
    """Функция выводит список доступных в репозитории пакетов"""
    print("\n\nИмя       \t\t\t| Версия")
    for pkg_name, pkg_version in PKGLIST:
        print(pkg_name + "\t\t\t| " + pkg_version)


def pkgs_list_installed():
    """Функция выводит список установленных пакетов"""
    print("\n\nИмя       \t\t\t| Версия")
    for pkg_name, pkg_version in CACHEPKGLIST:
        print(pkg_name + "\t\t\t| " + pkg_version)


def pkgs_list_updated():
    """Функция выводит список установленных пакетов"""
    print("\n\nИмя       \t\t\t| Версия")
    for pkg_name, pkg_version in CACHEPKGLIST:
        tmp = search_in_index(PKGLIST, pkg_name)
        if tmp >= 0 and pkg_version != PKGLIST[tmp][1]:
            print(pkg_name + "\t\t\t| " + pkg_version)


def pkg_download(pkg_name, pkg_version):
    """Функция загружает пакет из репозитория в кэш"""
    src = os.path.join('', REPO_DIR, pkg_name)
    tmp = os.path.join('', CACHE_DIR, pkg_name)
    dst = os.path.join('', tmp, pkg_version)
    #pkg = os.path.join('', dst, pkg_name)

    if not os.path.isdir(tmp):  # Если директория для пакета не существует
        os.makedirs(tmp)
        os.makedirs(dst)
    elif os.path.isdir(tmp) and not os.path.isdir(dst):  # Если директория
        print(os.path.isdir(tmp) and not os.path.isdir(dst))  # существует
        os.makedirs(dst)                  # но нет директории с номером версии
    else:       # Если путь существует значит там что то лежит, удалить всё
        shutil.rmtree(dst)
        os.makedirs(dst)

    shutil.unpack_archive(src, dst, 'zip')


def pkg_install(pkg_name):
    """Функция устанавливает пакет с указанным именем. В имени пакета можно
    не указывать расширение вида .pkg"""

    CACHEPKGLIST = read_index(CACHEINDEX)
    pkg_name = pkg_name.lower()

    if not '.pkg' in pkg_name:           # Если имя не содержит расширение
        pkg_name = pkg_name + '.pkg'     # то добавляем в конец (это криво)

    current_pkg = search_in_index(PKGLIST, pkg_name)  # Версия в репах
    current_cache_pkg = search_in_index(CACHEPKGLIST, pkg_name)  # Локальная

    if current_pkg < 0:                 # Проверяем есть ли такой в репах
        print(pkg_name + " Пакет с таким именет отсутствует!!")
        return 0
    else:
        pkg_version = PKGLIST[current_pkg][1]  # Какая версия в репах

# Проверка не установлен ли уже пакет
    if (pkg_name, pkg_version) in CACHEPKGLIST:
        print(pkg_name + " Пакет уже установлен и это последняя версия!!")
        return 0
    elif current_cache_pkg >= 0:
        print("Пакет будет обновлён")
        pkg_download(pkg_name, pkg_version)
        p = subprocess.call(['python',
            os.path.join('', CACHE_DIR, pkg_name, pkg_version, 'script.py'),
            'install'], stdout=subprocess.PIPE)
        change_index('w', (pkg_name, pkg_version))
    else:
        print("Пакет будет установлен")
        pkg_download(pkg_name, pkg_version)
        p = subprocess.call(['python',
            os.path.join('', CACHE_DIR, pkg_name, pkg_version, 'script.py'),
            'install'], stdout=subprocess.PIPE)
        change_index('w', (pkg_name, pkg_version))


def pkgs_install(packages):
    """Функция групповой установки пакетов"""
    for pkg_name in packages:
        pkg_install(pkg_name)
    write_index()


def pkg_remove(pkg_name):
    """Функция удаляет ранее установленный пакет"""

    CACHEPKGLIST = read_index(CACHEINDEX)
    pkg_name = pkg_name.lower()

    if not '.pkg' in pkg_name:           # Если имя не содержит расширение
        pkg_name = pkg_name + '.pkg'     # то добавляем в конец (это криво)

    current_cache_pkg = search_in_index(CACHEPKGLIST, pkg_name)

    if current_cache_pkg < 0:                 # Проверяем есть ли такой
        print(pkg_name + " Пакет с таким именет отсутствует!!")
        return 0
    else:
        pkg_version = CACHEPKGLIST[current_cache_pkg][1]

    subprocess.call(['python',
        os.path.join('', CACHE_DIR, pkg_name, pkg_version, 'script.py'),
        'remove'], shell=True, stdout=subprocess.PIPE)
    shutil.rmtree(os.path.join('', CACHE_DIR, pkg_name, pkg_version))
    change_index('d', (pkg_name, pkg_version))


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

    return parser


if __name__ == "__main__":
    parser = createParser()
    namespace = parser.parse_args(sys.argv[1:])

    read_config()
    repo_check()
    cache_check()

    if namespace.command == "list":
        if namespace.what is None:
            pkgs_list()
        elif namespace.what == 'installed':
            pkgs_list_installed()
        elif namespace.what == 'updated':
            pkgs_list_updated()
    elif namespace.command == "install":
        pkgs_install(namespace.packages)
    elif namespace.command == "remove":
        pkgs_remove(namespace.packages)