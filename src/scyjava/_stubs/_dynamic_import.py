import ast
from logging import warning
from pathlib import Path
from typing import Any, Callable, Sequence


def setup_java_imports(
    module_name: str,
    module_file: str,
    endpoints: Sequence[str] = (),
    base_prefix: str = "",
) -> tuple[list[str], Callable[[str], Any]]:
    """Setup a module to dynamically import Java class names.

    This function creates a `__getattr__` function that, when called, will dynamically
    import the requested class from the Java namespace corresponding to this module.

    :param module_name: The dotted name/identifier of the module that is calling this
        function (usually `__name__` in the calling module).
    :param module_file: The path to the module file (usually `__file__` in the calling
        module).
    :param endpoints: A list of Java endpoints to add to the scyjava configuration.
    :param base_prefix: The base prefix for the Java package name. This is used when
        determining the Java class path for the requested class. The java class path
        will be truncated to only the part including the base_prefix and after.  This
        makes it possible to embed a module in a subpackage (like `scyjava.types`) and
        still have the correct Java class path.
    :return: A 2-tuple containing:
        - A list of all classes in the module (as defined in the stub file), to be
            assigned to `__all__`.
        - A callable that takes a class name and returns a proxy for the Java class.
            This callable should be assigned to `__getattr__` in the calling module.
            The proxy object, when called, will start the JVM, import the Java class,
            and return an instance of the class.  The JVM will *only* be started when
            the object is called.

    Example:
    If the module calling this function is named `scyjava.types.org.scijava.parsington`,
    then it should invoke this function as:

    .. code-block:: python

        from scyjava._stubs import setup_java_imports

        __all__, __getattr__ = setup_java_imports(
            __name__,
            __file__,
            endpoints=["org.scijava:parsington:3.1.0"],
            base_prefix="org"
        )
    """
    import scyjava
    import scyjava.config

    for ep in endpoints:
        if ep not in scyjava.config.endpoints:
            scyjava.config.endpoints.append(ep)

    module_all = []
    try:
        my_stub = Path(module_file).with_suffix(".pyi")
        stub_ast = ast.parse(my_stub.read_text())
        module_all = sorted(
            {
                node.name
                for node in stub_ast.body
                if isinstance(node, ast.ClassDef) and not node.name.startswith("__")
            }
        )
    except (OSError, SyntaxError):
        warning(
            f"Failed to read stub file {my_stub!r}. Falling back to empty __all__.",
            stacklevel=3,
        )

    def module_getattr(name: str, mod_name: str = module_name) -> Any:
        if module_all and name not in module_all:
            raise AttributeError(f"module {module_name!r} has no attribute {name!r}")

        # cut the mod_name to only the part including the base_prefix and after
        if base_prefix in mod_name:
            mod_name = mod_name[mod_name.index(base_prefix) :]

        class_path = f"{mod_name}.{name}"

        class ProxyMeta(type):
            def __repr__(self) -> str:
                return f"<scyjava class {class_path!r}>"

        class Proxy(metaclass=ProxyMeta):
            def __new__(_cls_, *args: Any, **kwargs: Any) -> Any:
                cls = scyjava.jimport(class_path)
                return cls(*args, **kwargs)

        Proxy.__name__ = name
        Proxy.__qualname__ = name
        Proxy.__module__ = module_name
        Proxy.__doc__ = f"Proxy for {class_path}"
        return Proxy

    return module_all, module_getattr
