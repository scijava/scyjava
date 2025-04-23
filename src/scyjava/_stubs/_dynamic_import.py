import ast
from logging import warning
from pathlib import Path
from typing import Any, Callable, Sequence


def dynamic_import(
    module_name: str,
    module_file: str,
    endpoints: Sequence[str] = (),
    base_prefix: str = "",
) -> tuple[list[str], Callable[[str], Any]]:
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
