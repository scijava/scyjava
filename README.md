# scyjava

Supercharged Java access from Python.

Built on [pyjnius](https://pyjnius.readthedocs.io/en/latest/) and [jgo](https://github.com/scijava/jgo).

## Use Java classes from Python

```python
>>> import scyjava, jnius
>>> System = jnius.autoclass('java.lang.System')
>>> System.getProperty('java.version')
'1.8.0_152-release'
```

To pass parameters to the JVM, such as an increased max heap size:

```python
>>> import scyjava_config
>>> scyjava_config.add_options('-Xmx6g')
>>> import scyjava, jnius
>>> Runtime = jnius.autoclass('java.lang.Runtime')
>>> Runtime.getRuntime().maxMemory() / 2**30
5.33349609375
```

See the [Pyjnius documentation](https://pyjnius.readthedocs.io/en/latest/) for more about calling Java from Python.

## Use Maven artifacts from remote repositories

### From Maven Central

```python
>>> import sys; sys.version_info
sys.version_info(major=3, minor=6, micro=5, releaselevel='final', serial=0)
>>> import scyjava_config
>>> scyjava_config.add_endpoints('org.python:jython-standalone:2.7.1')
>>> import scyjava, jnius
>>> jython = jnius.autoclass('org.python.util.jython')
>>> jython.main([])
Jython 2.7.1 (default:0df7adb1b397, Jun 30 2017, 19:02:43)
[OpenJDK 64-Bit Server VM (JetBrains s.r.o)] on java1.8.0_152-release
Type "help", "copyright", "credits" or "license" for more information.
>>> import sys; sys.version_info
sys.version_info(major=2, minor=7, micro=1, releaselevel='final', serial=0)
```

### From other Maven repositories

```python
>>> import scyjava_config
>>> scyjava_config.add_repositories({'scijava.public': 'https://maven.scijava.org/content/groups/public'})
>>> scyjava_config.add_endpoints('net.imagej:imagej:2.0.0-rc-65')
>>> import scyjava, jnius
>>> System = jnius.autoclass('java.lang.System')
>>> System.setProperty('java.awt.headless', 'true')
>>> ImageJ = jnius.autoclass('net.imagej.ImageJ')
>>> ij = ImageJ()
>>> formula = "10 * (Math.cos(0.3*p[0]) + Math.sin(0.3*p[1]))"
>>> blank = ij.op().create().img([64, 16])
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
>>> import scyjava, jnius
>>> System = jnius.autoclass('java.lang.System')
>>> props = System.getProperties()
>>> props
<java.util.Properties at 0x10dc2daf0 jclass=java/util/Properties jself=<LocalRef obj=0x7fcfefd34b20 at 0x10dc371f0>>
>>> [k for k in props]
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
TypeError: 'java.util.Properties' object is not iterable
>>> [k for k in scyjava.to_python(props) if k.startswith('java.vm.')]
['java.vm.version', 'java.vm.vendor', 'java.vm.name', 'java.vm.specification.name', 'java.vm.specification.vendor', 'java.vm.specification.version', 'java.vm.info']
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
>>> scyjava.to_java(squares).stream()
<java.util.stream.Stream at 0x119d8ba40 jclass=java/util/stream/Stream jself=<LocalRef obj=0x7fcfefd34810 at 0x10dc37810>>
```

### Introspect Java classes

```python
>>> import scyjava
>>> NumberClass = scyjava.jclass('java.lang.Number')
>>> NumberClass
<Class at 0x10dca89e8 jclass=java/lang/Class jself=<LocalRef obj=0x7fcfefd33420 at 0x10dc37a30>>
>>> NumberClass.getName()
'java.lang.Number'
>>> NumberClass.isInstance(scyjava.to_java(5))
True
>>> NumberClass.isInstance(scyjava.to_java('Hello'))
False
```

## Available functions

```
>>> import scyjava
>>> help(scyjava.convert)
...
FUNCTIONS
    isjava(data)
        Return whether the given data object is a Java object.

    jclass(data)
        Obtain a Java class object.

        :param data: The object from which to glean the class.
        Supported types include:
        A. Name of a class to look up, analogous to
        Class.forName("java.lang.String");
        B. A jnius.MetaJavaClass object e.g. from jnius.autoclass, analogous to
        String.class;
        C. A jnius.JavaClass object e.g. instantiated from a jnius.MetaJavaClass,
        analogous to "Hello".getClass().
        :returns: A java.lang.Class object, suitable for use with reflection.
        :raises TypeError: if the argument is not one of the aforementioned types.

    to_java(data)
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

    to_python(data)
        Recursively convert a Java object to a Python object.
        :param data: The Java object to convert.
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
        :raises TypeError: if the argument is not one of the aforementioned types.
```
