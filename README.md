[![build status](https://github.com/scijava/scyjava/actions/workflows/build.yml/badge.svg)](https://github.com/scijava/scyjava/actions/workflows/build.yml)
[![codecov](https://codecov.io/gh/scijava/scyjava/branch/master/graph/badge.svg?token=NLK3ADZUCU)](https://codecov.io/gh/scijava/scyjava)

Supercharged Java access from Python.

Built on [JPype](https://jpype.readthedocs.io/en/latest/)
and [jgo](https://github.com/scijava/jgo).

## Use Java classes from Python

```python
>>> from scyjava import jimport
>>> System = jimport('java.lang.System')
>>> System.getProperty('java.version')
'1.8.0_252'
```

To pass parameters to the JVM, such as an increased max heap size:

```python
>>> from scyjava import config, jimport
>>> config.add_option('-Xmx6g')
>>> Runtime = jimport('java.lang.Runtime')
>>> Runtime.getRuntime().maxMemory() / 2**30
5.33349609375
```

See the [JPype documentation](https://jpype.readthedocs.io/en/latest/)
for all the gritty details on how this wrapping works.

## Use Maven artifacts from remote repositories

### From Maven Central

```python
>>> import sys
>>> sys.version_info
sys.version_info(major=3, minor=8, micro=5, releaselevel='final', serial=0)
>>> from scyjava import config, jimport
>>> config.endpoints.append('org.python:jython-slim:2.7.2')
>>> jython = jimport('org.python.util.jython')
>>> jython.main([])
Jython 2.7.2 (v2.7.2:925a3cc3b49d, Mar 21 2020, 10:12:24)
[OpenJDK 64-Bit Server VM (JetBrains s.r.o)] on java1.8.0_152-release
Type "help", "copyright", "credits" or "license" for more information.
>>> import sys
>>> sys.version_info
sys.version_info(major=2, minor=7, micro=1, releaselevel='final', serial=0)
>>> from java.lang import System
>>> System.getProperty('java.version')
u'1.8.0_152-release'
```

### From other Maven repositories

```python
>>> from scyjava import config, jimport
>>> config.add_option('-Djava.awt.headless=true')
>>> config.add_repositories({'scijava.public': 'https://maven.scijava.org/content/groups/public'})
>>> config.endpoints.append('net.imagej:imagej:2.1.0')
>>> ImageJ = jimport('net.imagej.ImageJ')
>>> ij = ImageJ()
>>> formula = "10 * (Math.cos(0.3*p[0]) + Math.sin(0.3*p[1]))"
>>> ArrayImgs = jimport('net.imglib2.img.array.ArrayImgs')
>>> blank = ArrayImgs.floats(64, 16)
>>> sinusoid = ij.op().image().equation(blank, formula)
>>> print(ij.op().image().ascii(sinusoid))
,,,--+oo******oo+--,,,,,--+oo******o++--,,,,,--+oo******o++--,,,
...,--+ooo**oo++--,....,,--+ooo**oo++-,,....,,--+ooo**oo++-,,...
 ...,--++oooo++--,... ...,--++oooo++--,... ...,--++oooo++-,,...
   ..,--++++++--,..     ..,--++o+++--,..     .,,--++o+++--,..
   ..,,-++++++-,,.      ..,,-++++++-,,.      ..,--++++++-,,.
    .,,--++++--,,.       .,,--++++--,,.       .,,--++++--,..
    .,,--++++--,,.       .,,-+++++--,,.       .,,-+++++--,,.
   ..,--++++++--,..     ..,--++++++--,..     ..,--++++++-,,..
  ..,,-++oooo++-,,..   ..,,-++oooo++-,,..   ..,,-++ooo+++-,,..
...,,-++oooooo++-,,.....,,-++oooooo++-,,.....,,-++oooooo+--,,...
.,,,-++oo****oo++-,,,.,,,-++oo****oo+--,,,.,,,-++oo****oo+--,,,.
,,--++o***OO**oo++-,,,,--++o***OO**oo+--,,,,--++o***OO**oo+--,,,
---++o**OOOOOO**o++-----++o**OOOOOO*oo++-----++o**OOOOOO*oo++---
--++oo*OO####OO*oo++---++oo*OO####OO*oo++---++o**OO####OO*oo++--
+++oo*OO######O**oo+++++oo*OO######O**oo+++++oo*OO######O**oo+++
+++oo*OO######OO*oo+++++oo*OO######OO*oo+++++oo*OO######OO*oo+++
```

See the [jgo documentation](https://github.com/scijava/jgo) for more about Maven endpoints.

## Convert between Python and Java data structures

### Convert Java collections to Python

```python
>>> from scyjava import jimport
>>> HashSet = jimport('java.util.HashSet')
>>> moves = {'jump', 'duck', 'dodge'}
>>> fish = {'walleye', 'pike', 'trout'}
>>> jbirds = HashSet()
>>> for bird in ('duck', 'goose', 'swan'): jbirds.add(bird)
...
True
True
True
>>> jbirds.isdisjoint(moves)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
AttributeError: 'java.util.HashSet' object has no attribute 'isdisjoint'
>>> from scyjava import to_python as j2p
>>> j2p(jbirds).isdisjoint(moves)
False
>>> j2p(jbirds).isdisjoint(fish)
True
```

### Convert Python collections to Java

```python
>>> squares = [n**2 for n in range(1, 10)]
>>> squares
[1, 4, 9, 16, 25, 36, 49, 64, 81]
>>> squares.stream()
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
AttributeError: 'list' object has no attribute 'stream'
>>> from scyjava import to_java as p2j
>>> p2j(squares).stream()
<java object 'java.util.stream.ReferencePipeline.Head'>
```

```python
>>> from scyjava import jimport
>>> HashSet = jimport('java.util.HashSet')
>>> jset = HashSet()
>>> pset = {1, 2, 3}
>>> jset.addAll(pset)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
TypeError: No matching overloads found for java.util.Set.addAll(set), options are:
	public abstract boolean java.util.Set.addAll(java.util.Collection)
>>> from scyjava import to_java as p2j
>>> jset.addAll(p2j(pset))
True
>>> jset.toString()
'[1, 2, 3]'
```

## Available functions

```
>>> import scyjava
>>> help(scyjava)
...
FUNCTIONS
    add_java_converter(converter: scyjava.Converter)
        Adds a converter to the list used by to_java
        :param converter: A Converter going from python to java

    add_py_converter(converter: scyjava.Converter)
        Adds a converter to the list used by to_python
        :param converter: A Converter from java to python

    constant(func: Callable[[], Any], cache=True) -> Callable[[], Any]
        Turns a function into a property of this module
        Functions decorated with this property must have a
        leading underscore!
        :param func: The function to turn into a property

    get_version(java_class_or_python_package)
        Return the version of a Java class or Python package.

        For Python packages, uses importlib.metadata.version if available
        (Python 3.8+), with pkg_resources.get_distribution as a fallback.

        For Java classes, requires org.scijava:scijava-common on the classpath.

        The version string is extracted from the given class's associated JAR
        artifact (if any), either the embedded Maven POM if the project was built
        with Maven, or the JAR manifest's Specification-Version value if it exists.

        See org.scijava.VersionUtils.getVersion(Class) for further details.

    is_awt_initialized()
        Return true iff the AWT subsystem has been initialized.

        Java starts up its AWT subsystem automatically and implicitly, as
        soon as an action is performed requiring it -- for example, if you
        jimport a java.awt or javax.swing class. This can lead to deadlocks
        on macOS if you are not running in headless mode and did not invoke
        those actions via the jpype.setupGuiEnvironment wrapper function;
        see the Troubleshooting section of the scyjava README for details.

    is_jvm_headless()
        Return true iff Java is running in headless mode.

        :raises RuntimeError: If the JVM has not started yet.

    is_version_at_least(actual_version, minimum_version)
        Return a boolean on a version comparison.
        Requires org.scijava:scijava-common on the classpath.

        Returns True if the given actual version is greater than or
        equal to the specified minimum version, or False otherwise.

        See org.scijava.VersionUtils.compare(String, String) for further details.

    isjava(data)
        Return whether the given data object is a Java object.

    jclass(data)
        Obtain a Java class object.

        :param data: The object from which to glean the class.
        Supported types include:
        A. Name of a class to look up, analogous to
        Class.forName("java.lang.String");
        B. A jpype.JClass object analogous to String.class;
        C. A _jpype._JObject instance analogous to o.getClass().
        :returns: A java.lang.Class object, suitable for use with reflection.
        :raises TypeError: if the argument is not one of the aforementioned types.

    jimport(class_name)
        Import a class from Java to Python.

        :param class_name: Name of the class to import.
        :returns: A pointer to the class, which can be used to
                  e.g. instantiate objects of that class.

    jstacktrace(exc)
        Extract the Java-side stack trace from a Java exception.

        Example of usage:

            from scyjava import jimport, jstacktrace
            try:
                Integer = jimport('java.lang.Integer')
                nan = Integer.parseInt('not a number')
            except Exception as exc:
                print(jstacktrace(exc))

        :param exc: The Java Throwable from which to extract the stack trace.
        :returns: A multi-line string containing the stack trace, or empty string
        if no stack trace could be extracted.

    jvm_started()
        Return true iff a Java virtual machine (JVM) has been started.

    jvm_version()
        Gets the version of the JVM as a tuple,
        with each dot-separated digit as one element.
        Characters in the version string beyond only
        numbers and dots are ignored, in line
        with the java.version system property.

        Examples:
        * OpenJDK 17.0.1 -> [17, 0, 1]
        * OpenJDK 11.0.9.1-internal -> [11, 0, 9, 1]
        * OpenJDK 1.8.0_312 -> [1, 8, 0]

        If the JVM is already started,
        this function should return the equivalent of:
           jimport('java.lang.System')
             .getProperty('java.version')
             .split('.')

        In case the JVM is not started yet,a best effort is made to deduce
        the version from the environment without actually starting up the
        JVM in-process. If the version cannot be deduced, a RuntimeError
        with the cause is raised.

    shutdown_jvm()
        Shutdown the JVM.

        This function makes a best effort to clean up Java resources first.
        In particular, shutdown hooks registered with scyjava.when_jvm_stops
        are sequentially invoked.

        Then, if the AWT subsystem has started, all AWT windows (as identified
        by the java.awt.Window.getWindows() method) are disposed to reduce the
        risk of GUI resources delaying JVM shutdown.

        Finally, the jpype.shutdownJVM() function is called. Note that you can
        set the jpype.config.destroy_jvm flag to request JPype to destroy the
        JVM explicitly, although setting this flag can lead to delayed shutdown
        times while the JVM is waiting for threads to finish.

        Note that if the JVM is not already running, then this function does
        nothing! In particular, shutdown hooks are skipped in this situation.

    start_jvm(options=[])
        Explicitly connect to the Java virtual machine (JVM). Only one JVM can
        be active; does nothing if the JVM has already been started. Calling
        this function directly is typically not necessary, because the first
        time a scyjava function needing a JVM is invoked, one is started on the
        fly with the configuration specified via the scijava.config mechanism.

        :param options: List of options to pass to the JVM. For example:
                        ['-Djava.awt.headless=true', '-Xmx4g']

    to_java(obj: Any) -> Any
        Recursively convert a Python object to a Java object.
        :param data: The Python object to convert.
        Supported types include:
        * str -> String
        * bool -> Boolean
        * int -> Integer, Long or BigInteger as appropriate
        * float -> Float, Double or BigDecimal as appropriate
        * dict -> LinkedHashMap
        * set -> LinkedHashSet
        * list -> ArrayList
        :returns: A corresponding Java object with the same contents.
        :raises TypeError: if the argument is not one of the aforementioned types.

    to_python(data: Any, gentle: bool = False) -> Any
        Recursively convert a Java object to a Python object.
        :param data: The Java object to convert.
        :param gentle: If set, and the type cannot be converted, leaves
                       the data alone rather than raising a TypeError.
        Supported types include:
        * String, Character -> str
        * Boolean -> bool
        * Byte, Short, Integer, Long, BigInteger -> int
        * Float, Double, BigDecimal -> float
        * Map -> collections.abc.MutableMapping (dict-like)
        * Set -> collections.abc.MutableSet (set-like)
        * List -> collections.abc.MutableSequence (list-like)
        * Collection -> collections.abc.Collection
        * Iterable -> collections.abc.Iterable
        * Iterator -> collections.abc.Iterator
        :returns: A corresponding Python object with the same contents.
        :raises TypeError: if the argument is not one of the aforementioned types,
                           and the gentle flag is not set.

    when_jvm_starts(f)
        Registers a function to be called when the JVM starts (or immediately).
        This is useful to defer construction of Java-dependent data structures
        until the JVM is known to be available. If the JVM has already been
        started, the function executes immediately.

        :param f: Function to invoke when scyjava.start_jvm() is called.

    when_jvm_stops(f)
        Registers a function to be called just before the JVM shuts down.
        This is useful to perform cleanup of Java-dependent data structures.

        Note that if the JVM is not already running when shutdown_jvm is
        called, then these registered callback functions will be skipped!

        :param f: Function to invoke when scyjava.shutdown_jvm() is called.
```

## Troubleshooting

On macOS, attempting to use AWT/Swing from Python will cause a hang,
unless you do one of two things:

1.  Start Java in headless mode:

    ```python
    from scyjava import config, jimport
    config.add_option('-Djava.awt.headless=true')
    ```

    In which case, you'll get `java.awt.HeadlessException` instead of a
    hang when you attempt to do something graphical, e.g. create a window.

2.  Or install [PyObjC](https://pyobjc.readthedocs.io/), specifically the
    `pyobjc-core` and `pyobjc-framework-cocoa` packages from conda-forge,
    or `pyobjc` from PyPI; and then do your AWT-related things inside of
    a `jpype.setupGuiEnvironment` call on the main Python thread:

    ```python
    import jpype, scyjava
    scyjava.start_jvm()
    def hello():
        JOptionPane = scyjava.jimport('javax.swing.JOptionPane')
        JOptionPane.showMessageDialog(None, "Hello world")
    jpype.setupGuiEnvironment(hello)
    ```

    In which case, the `setupGuiEnvironment` call will block the main Python
    thread forever.
