import logging
import os
import platform
import sys
import subprocess
from pathlib import Path

_logger = logging.getLogger(__name__)

# Enable debug logging if DEBUG environment variable is set.
try:
    debug = os.environ['DEBUG']
    if debug:
        _logger.setLevel(logging.DEBUG)
except KeyError as e:
    pass

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
            _logger.debug('Checking %s environment variable', PYJNIUS_JAR_STR)
            PYJNIUS_JAR = os.environ[PYJNIUS_JAR_STR]
        except KeyError:
            _logger.debug('No %s environment variable', PYJNIUS_JAR_STR)
        if not PYJNIUS_JAR:
            # NB: This logic handles both None and empty string cases.
            _logger.debug('%s still unknown; falling back to default path', PYJNIUS_JAR_STR)
            PYJNIUS_JAR = os.path.join(sys.prefix, 'share', 'pyjnius', 'pyjnius.jar')
        if Path(PYJNIUS_JAR).is_file():
            _logger.debug('%s found at "%s"', PYJNIUS_JAR_STR, PYJNIUS_JAR)
            jnius_config.add_classpath(PYJNIUS_JAR)
        else:
            _logger.error('Unable to import scyjava: pyjnius JAR not found.')
            return None
    else:
        _logger.debug('%s found in globals', PYJNIUS_JAR_STR)

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
                    mvn = mvn.replace('\\r\\n', '\\n') # Fix Windows line breaks.
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
        java_path = Path(JAVA_HOME)
        if java_path.is_dir():
            _logger.debug('%s found at "%s"', JAVA_HOME_STR, JAVA_HOME)
            if java_path.name is 'jre':
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
        if Path(os.path.join(jvm_server_dir, 'jvm.dll')).is_file():
            os.environ['PATH'] += ';' + jvm_server_dir
        else:
            # Java 8 and earlier
            jvm_server_dir = os.path.join(os.environ['JAVA_HOME'], 'jre', 'bin', 'server')
            if Path(os.path.join(jvm_server_dir, 'jvm.dll')).is_file():
                os.environ['PATH'] += ';' + jvm_server_dir

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
            manage_dependencies=scyjava_config.get_manage_deps(),
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
if jnius is None:
    raise ImportError('Unable to import scyjava dependency jnius.')

from .convert import isjava, jclass, to_java, to_python
