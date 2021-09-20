import logging
import pathlib
import jpype
from jgo import maven_scijava_repository

_logger = logging.getLogger(__name__)

endpoints = []
_repositories = {'scijava.public': maven_scijava_repository()}
_verbose = 0
_manage_deps = True
_cache_dir = pathlib.Path.home() / '.jgo'
_m2_repo = pathlib.Path.home() / '.m2' / 'repository'
_options = []


def add_endpoints(*new_endpoints):
    """
    DEPRECATED since v1.2.1
    Please modify the endpoints field directly instead.
    """
    _logger.warn('Deprecated method call: scyjava.config.add_endpoints(). Please modify scyjava.config.endpoints directly instead.')
    global endpoints
    _logger.debug('Adding endpoints %s to %s', new_endpoints, endpoints)
    endpoints.extend(new_endpoints)


def get_endpoints():
    """
    DEPRECATED since v1.2.1
    Please access the endpoints field directly instead.
    """
    _logger.warn('Deprecated method call: scyjava.config.get_endpoints(). Please access scyjava.config.endpoints directly instead.')
    global endpoints
    return endpoints


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


def get_classpath():
    return jpype.getClassPath()


def add_option(option):
    global _options
    _options.append(option)


def add_options(options):
    global _options
    if isinstance(options, str):
        _options.append(options)
    else:
        _options.extend(options)


def get_options():
    global _options
    return _options
