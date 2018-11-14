import logging
import os

_logger = logging.getLogger(__name__)

def _init_jvm():
    import scyjava_config
    import jnius_config
    import jgo

    if jnius_config.vm_running:
        _logger.warning('JVM is already running, will not add endpoints to classpath -- required classes might not be on classpath..')
        import jnius
        return jnius

    PYJNIUS_JAR_STR = 'PYJNIUS_JAR'
    if PYJNIUS_JAR_STR not in globals():
        try:
            PYJNIUS_JAR = os.environ[PYJNIUS_JAR_STR]
            jnius_config.add_classpath(PYJNIUS_JAR)
        except KeyError as e:
            if e.args[0] == PYJNIUS_JAR_STR:
                _logger.error('Unable to import scyjava: %s environment variable not defined.', PYJNIUS_JAR_STR)
            else:
                raise e
            return None

    endpoints = scyjava_config.get_endpoints()
    repositories = scyjava_config.get_repositories()

    _logger.debug('Adding jars from endpoints %s', endpoints)

    if len(endpoints) > 0:
        endpoints = endpoints[:1] + sorted(endpoints[1:])
        _logger.debug('Using endpoints %s', endpoints)
        _, workspace = jgo.resolve_dependencies(
            '+'.join(endpoints),
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
            _logger.error('Unable to import scyjava: JAVA_HOME environment variable not defined, cannot import jnius.')
        else:
            raise e
        return None

jnius = _init_jvm()
if (jnius == None):
    raise ImportError('Unable to import scyjava dependency jnius.')

from .convert import isjava, jclass, to_java, to_python
