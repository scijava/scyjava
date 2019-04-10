import logging
import os
import sys
import subprocess
from pathlib import Path

_logger = logging.getLogger(__name__)

def _init_jvm():
    import scyjava_config
    import jnius_config
    import jgo

    if jnius_config.vm_running:
        _logger.warning('JVM is already running, will not add endpoints to classpath -- required classes might not be on classpath..')
        import jnius
        return jnius

    # attempt to find pyjnius.jar if the envrionment variable is not set.
    PYJNIUS_JAR_STR = 'PYJNIUS_JAR'
    if PYJNIUS_JAR_STR not in globals():
        PYJNIUS_JAR = None
        try:
            PYJNIUS_JAR = os.environ[PYJNIUS_JAR_STR]
        except KeyError as e:
            PYJNIUS_JAR = os.path.join(sys.prefix, 'share', 'pyjnius', 'pyjnius.jar')
        if Path(PYJNIUS_JAR).is_file():
            jnius_config.add_classpath(PYJNIUS_JAR)
        else:
            _logger.error('Unable to import scyjava: pyjnius JAR not found.')
            return None

    # attempt to set JAVA_HOME if the environment variable is not set.
    JAVA_HOME_STR = 'JAVA_HOME'
    if JAVA_HOME_STR not in globals():
        JAVA_HOME = None
        try:
            JAVA_HOME = os.environ[JAVA_HOME_STR]
        except KeyError as e:
            # attempt to find the jre by interrogating maven
            # (which we have because is needed by jgo)
            try: 
                mvn = str(subprocess.check_output(['mvn', '-v']))
            except subprocess.CalledProcessError as e:
                _logger.error('Unable to import scyjava, could not find Maven')
                return None
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
            begin = mvn.index('/', begin)
            end = mvn.index('\\n', begin)
            JAVA_HOME = mvn[begin:end]
        if Path(JAVA_HOME).is_dir():
            os.environ['JAVA_HOME'] = JAVA_HOME
        else:
            _logger.error('Unable to import scyjava: jre not found')
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
