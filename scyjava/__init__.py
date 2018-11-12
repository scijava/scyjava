# from .version import __version__ as version

import logging
import os

_logger = logging.getLogger(__name__)

def _init_jvm():
    import scyjava_config
    import jnius_config
    import jrun

    PYJNIUS_JAR_STR = 'PYJNIUS_JAR'
    if PYJNIUS_JAR_STR not in globals():
        try:
            PYJNIUS_JAR = os.environ[PYJNIUS_JAR_STR]
            jnius_config.add_classpath(PYJNIUS_JAR)
        except KeyError as e:
            print("Path to pyjnius.jar not defined! Use environment variable {} to define it.".format(PYJNIUS_JAR_STR))
            raise e

    endpoints = scyjava_config.get_endpoints()
    repositories = scyjava_config.get_repositories()

    _logger.debug('Adding jars from endpoints %s', endpoints)

    if len(endpoints) > 0:
        _, workspace = jrun.resolve_dependencies(
            '+'.join(endpoints[:1] + sorted(endpoints[1:])),
            m2_repo=scyjava_config.get_m2_repo(),
            cache_dir=scyjava_config.get_cache_dir(),
            repositories=repositories,
            verbose=scyjava_config.get_verbose()
        )
        jnius_config.add_classpath(os.path.join(workspace, '*'))

    try:
        import jnius
        return jnius
    except KeyError as e:
        if e.args[0] == 'JAVA_HOME':
            _logger.info('Unable to import scyjava: JAVA_HOME environment variable not defined, cannot import jnius.')
        return None

jnius = _init_jvm()
if (jnius == None):
    raise ImportError('Unable to import scyjava dependency jnius.')





