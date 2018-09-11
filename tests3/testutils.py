import os, sys, platform
from os.path import join, dirname, abspath, basename, isdir
import unittest

def add_to_path(library):
    """
    Prepends the build directory to the path so that newly built pyodbc or pyiodbc libraries
    are used, allowing it to be tested without installing it.

    * library: The library to load: pyodbc or pyiodbc
    """
    # Put the build directory into the Python path so we pick up the version we just built.
    #
    # To make this cross platform, we'll search the directories until we find the .pyd file.

    import imp

    library_exts  = [ t[0] for t in imp.get_suffixes() if t[-1] == imp.C_EXTENSION ]
    library_names = [ '%s%s' % (library, ext) for ext in library_exts ]

    # Only go into directories that match our version number.

    dir_suffix = '-%s.%s' % (sys.version_info[0], sys.version_info[1])

    root = dirname(dirname(abspath(__file__)))
    build = join(root, library, 'build')

    if not isdir(build):
        sys.exit('Build dir not found: %s' % build)

    for root, dirs, files in os.walk(build):
        for d in dirs[:]:
            if not d.endswith(dir_suffix):
                dirs.remove(d)

        for name in library_names:
            if name in files:
                sys.path.insert(0, root)
                return

    print('Did not find the %s library in the build directory (%s).  Will use an installed version.' %
          (library, build))


def print_library_info(name, module, cnxn):
    print('python:  %s' % sys.version)
    print('%s:  %s %s' % (name, module.version, os.path.abspath(module.__file__)))
    print('odbc:    %s' % cnxn.getinfo(module.SQL_ODBC_VER))
    print('driver:  %s %s' % (cnxn.getinfo(module.SQL_DRIVER_NAME), cnxn.getinfo(module.SQL_DRIVER_VER)))
    print('         supports ODBC version %s' % cnxn.getinfo(module.SQL_DRIVER_ODBC_VER))
    print('os:      %s' % platform.system())
    print('unicode: Py_Unicode=%s SQLWCHAR=%s' % (module.UNICODE_SIZE, module.SQLWCHAR_SIZE))

    cursor = cnxn.cursor()
    for typename in ['VARCHAR', 'WVARCHAR', 'BINARY']:
        t = getattr(module, 'SQL_' + typename)
        cursor.getTypeInfo(t)
        row = cursor.fetchone()
        print('Max %s = %s' % (typename, row and row[2] or '(not supported)'))

    if platform.system() == 'Windows':
        print('         %s' % ' '.join([s for s in platform.win32_ver() if s]))



def load_tests(testclass, name, *args):
    """
    Returns a TestSuite for tests in `testclass`.

    name
      Optional test name if you only want to run 1 test.  If not provided all tests in `testclass` will be loaded.

    args
      Arguments for the test class constructor.  These will be passed after the test method name.
    """
    if name:
        if not name.startswith('test_'):
            name = 'test_%s' % name
        names = [ name ]

    else:
        names = [ method for method in dir(testclass) if method.startswith('test_') ]

    return unittest.TestSuite([ testclass(name, *args) for name in names ])


def load_setup_connection_string(section):
    """
    Attempts to read the default connection string from the setup.cfg file.

    If the file does not exist or if it exists but does not contain the connection string, None is returned.  If the
    file exists but cannot be parsed, an exception is raised.
    """
    from os.path import exists, join, dirname, splitext, basename
    from configparser import SafeConfigParser

    FILENAME = 'setup.cfg'
    KEY      = 'connection-string'

    path = dirname(abspath(__file__))
    while True:
        fqn = join(path, 'tmp', FILENAME)
        if exists(fqn):
            break
        parent = dirname(path)
        if parent == path:
            return None
        path = parent

    try:
        p = SafeConfigParser()
        p.read(fqn)
    except:
        raise SystemExit('Unable to parse %s: %s' % (path, sys.exc_info()[1]))

    if p.has_option(section, KEY):
        return p.get(section, KEY)
