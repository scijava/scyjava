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
>>> from scyjava import jimport
>>> import scyjava.config
>>> scyjava.config.add_option('-Xmx6g')
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
>>> import scyjava.config
>>> scyjava.config.add_endpoints('org.python:jython-slim:2.7.2')
>>> from scyjava import jimport
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
>>> import scyjava.config
>>> scyjava.config.add_repositories({'scijava.public': 'https://maven.scijava.org/content/groups/public'})
>>> scyjava.config.add_endpoints('net.imagej:imagej:2.1.0')
>>> from scyjava import jimport
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
>>> moves = set(('jump', 'duck', 'dodge'))
>>> fish = set(('walleye', 'pike', 'trout'))
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
>>> pset = set((1, 2, 3))
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

            from scyjava import jimport
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

    start_jvm(options=[])
        Explicitly connect to the Java virtual machine (JVM). Only one JVM can
        be active; does nothing if the JVM has already been started. Calling
        this function directly is typically not necessary, because the first
        time a scyjava function needing a JVM is invoked, one is started on the
        fly with the configuration specified via the scijava.config mechanism.

        :param options: List of options to pass to the JVM. For example:
                        ['-Djava.awt.headless=true', '-Xmx4g']

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

    to_python(data, gentle=False)
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
```
