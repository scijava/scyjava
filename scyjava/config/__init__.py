__all__ = (
    'maven_scijava_repository',
    'add_endpoints',
    'get_endpoints',
    'add_repositories',
    'get_repositories',
    'set_verbose',
    'get_verbose',
    'set_manage_deps',
    'get_manage_deps',
    'set_cache_dir',
    'get_cache_dir',
    'set_m2_repo',
    'get_m2_repo',
    'set_options',
    'add_options',
    'get_options',
    'set_classpath',
    'add_classpath',
    'get_classpath',
    'expand_classpath')

import logging
import os
import platform
import pathlib
import jgo
import jpype
import jpype.imports
import subprocess

version = '0.4.1.dev1'

_logger = logging.getLogger(__name__)

_endpoints = []
_repositories = {1: 'https://maven.scijava.org/content/repositories/releases'}
_verbose = 0
_manage_deps = True
_cache_dir = pathlib.Path.home() / '.jgo'
_m2_repo = pathlib.Path.home() / '.m2' / 'repository'
_options = ""


def start_JVM(options=''):
    # if jvm JVM is already running -- break
    if JVM_status() == True:
        _logger.debug('The JVM is already running.')
        return

    # attempt to set JAVA_HOME if the environment variable is not set.
    JAVA_HOME_STR = 'JAVA_HOME'
    if JAVA_HOME_STR not in globals():
        JAVA_HOME = None
        try:
            _logger.debug('Checking %s environment variable', JAVA_HOME_STR)
            JAVA_HOME = os.environ[JAVA_HOME_STR]
        except KeyError:
            _logger.debug('No %s environment variable', JAVA_HOME_STR)
        if not JAVA_HOME:
            # NB: This logic handles both None and empty string cases.
            _logger.debug('%s still unknown; checking with Maven', JAVA_HOME_STR)
            # attempt to find Java by interrogating maven
            # (which we have because it is needed by jgo)
            try:
                if (platform.system() == 'Windows'):
                    mvn = str(subprocess.check_output(['mvn.cmd', '-v']))
                    mvn = mvn.replace('\\r\\n', '\\n')  # Fix Windows line breaks.
                else:
                    mvn = str(subprocess.check_output(['mvn', '-v']))
            except subprocess.CalledProcessError as e:
                _logger.error('Unable to import scyjava, could not find Maven')
                return None
            _logger.debug('Maven said: %s', mvn)
            try:
                begin = mvn.index('Java home: ')
            except ValueError as e:
                # in some versions of maven it is instead called runtime
                try:
                    begin = mvn.index('runtime: ')
                except ValueError as e:
                    _logger.error('Unable to import scyjava, could not locate jre')
                    return None
            # cut out 'Java home' or 'runtime'
            begin = mvn.index(':', begin) + 2
            end = mvn.index('\\n', begin)
            JAVA_HOME = mvn[begin:end]
        java_path = pathlib.Path(JAVA_HOME)
        if java_path.is_dir():
            _logger.debug('%s found at "%s"', JAVA_HOME_STR, JAVA_HOME)
            if java_path.name == 'jre':
                _logger.debug('JAVA_HOME points at jre folder; using parent instead')
                JAVA_HOME = str(java_path.parent)
            os.environ['JAVA_HOME'] = JAVA_HOME
        else:
            _logger.error('Unable to import scyjava: jre not found')
            return None
    else:
        _logger.debug('%s found in globals', JAVA_HOME_STR)

    # On Windows, add server subfolder to the PATH so jvm.dll can be found.
    if (platform.system() == 'Windows'):
        # Java 9 and later
        jvm_server_dir = os.path.join(os.environ['JAVA_HOME'], 'bin', 'server')
        if pathlib.Path(os.path.join(jvm_server_dir, 'jvm.dll')).is_file():
            os.environ['PATH'] += ';' + jvm_server_dir
        else:
            # Java 8 and earlier
            jvm_server_dir = os.path.join(os.environ['JAVA_HOME'], 'jre', 'bin', 'server')
            if pathlib.Path(os.path.join(jvm_server_dir, 'jvm.dll')).is_file():
                os.environ['PATH'] += ';' + jvm_server_dir

    # retrieve endpoint and repositories from scyjava_config
    endpoints = get_endpoints()
    repositories = get_repositories()

    # use the logger to notify user that endpoints are being added
    _logger.debug('Adding jars from endpoints {0}'.format(endpoints))

    # get endpoints and add to JPype class path
    if len(endpoints) > 0:
        endpoints = endpoints[:1] + sorted(endpoints[1:])
        _logger.debug('Using endpoints %s', endpoints)
        _, workspace = jgo.resolve_dependencies(
            '+'.join(endpoints),
            m2_repo=get_m2_repo(),
            cache_dir=get_cache_dir(),
            manage_dependencies=get_manage_deps(),
            repositories=repositories,
            verbose=get_verbose()
        )
        jpype.addClassPath(os.path.join(workspace, '*'))

    # Initialize JPype JVM
    jpype.startJVM(options)

    return


def JVM_status():
    return jpype.isJVMStarted()

def maven_scijava_repository():
    """
    :return: url for public scijava maven repo
    """
    return 'https://maven.scijava.org/content/groups/public'

def add_endpoints(*endpoints):
    global _endpoints
    _logger.debug('Adding endpoints %s to %s', endpoints, _endpoints)
    _endpoints.extend(endpoints)

def get_endpoints():
    global _endpoints
    return _endpoints

def add_repositories(*args, **kwargs):
    global _repositories
    for arg in args:
        _logger.debug('Adding repositories %s to %s', arg, _repositories)
        _repositories.update(arg)
    _logger.debug('Adding repositories %s to %s', kwargs, _repositories)
    _repositories.update(kwargs)

def get_repositories():
    global _repositories
    return _repositories

def set_verbose(level):
    global _verbose
    _logger.debug('Setting verbose level to %d (was %d)', level, _verbose)
    _verbose = level


def get_verbose():
    global _verbose
    _logger.debug('Getting verbose level: %d', _verbose)
    return _verbose


def set_manage_deps(manage):
    global _manage_deps
    _logger.debug('Setting manage deps to %d (was %d)', manage, _manage_deps)
    _manage_deps = manage


def get_manage_deps():
    global _manage_deps
    return _manage_deps


def set_cache_dir(dir):
    global _cache_dir
    _logger.debug('Setting cache dir to %s (was %s)', dir, _cache_dir)
    _cache_dir = dir


def get_cache_dir():
    global _cache_dir
    return _cache_dir


def set_m2_repo(dir):
    global _m2_repo
    _logger.debug('Setting m2 repo dir to %s (was %s)', dir, _m2_repo)
    _m2_repo = dir


def get_m2_repo():
    global _m2_repo
    return _m2_repo

def add_classpath(*path):
    jpype.addClassPath(*path)


def set_classpath(*path):
    jpype.addClassPath(*path)


def get_classpath():
    return jpype.getClassPath()

def add_options(options):
    global _options
    _options = options

def get_options():
    global _options
    return _options
