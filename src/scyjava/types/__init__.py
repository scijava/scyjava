"""
Dynamic type-safe imports for scyjava types with lazy initialization.

This module provides a meta path finder that intercepts imports from scyjava.types
and dynamically generates the requested modules at import time.

Usage:
    1. Set up a module generator function:
    
        def my_generator(module_name: str) -> types.ModuleType:
            # Create and return a module based on module_name
            module = types.ModuleType(module_name)
            # ... populate module with classes/functions ...
            return module
    
    2. Register the generator:
    
        scyjava.types.set_module_generator(my_generator)
    
    3. Import dynamically generated modules:
    
        import scyjava.types.SomeClass as some_class_module
        SomeClass = some_class_module.SomeClass
        
        # Or use from import:
        from scyjava.types import SomeClass as some_class_module
        SomeClass = some_class_module.SomeClass

The generator function will be called at import time with the full module name
(e.g., "scyjava.types.SomeClass") and should return a populated module.

API Functions:
    - set_module_generator(func): Register a module generator function
    - get_registered_generator(): Get the currently registered generator
    - is_meta_finder_installed(): Check if the meta finder is active
    - clear_generated_modules(): Remove all generated modules from cache
    - list_generated_modules(): List all currently loaded generated modules

Example:
    >>> import scyjava.types
    >>> 
    >>> def java_stub_generator(module_name):
    ...     import types
    ...     module = types.ModuleType(module_name)
    ...     class_name = module_name.split('.')[-1]
    ...     # Generate Java class stub here...
    ...     java_class = create_java_stub(class_name)
    ...     setattr(module, class_name, java_class)
    ...     return module
    ...
    >>> scyjava.types.set_module_generator(java_stub_generator)
    >>> 
    >>> # This will call java_stub_generator("scyjava.types.ArrayList")
    >>> import scyjava.types.ArrayList as al_module
    >>> ArrayList = al_module.ArrayList
"""

import importlib.util
import sys
import types
from typing import Any, Callable, Optional, Sequence

# The function that will be called to generate modules at import time
_module_generator: Optional[Callable[[str], Optional[types.ModuleType]]] = None


def set_module_generator(func: Callable[[str], Optional[types.ModuleType]]) -> None:
    """
    Set the function that will be called to generate modules at import time.

    Args:
        func: A callable that takes a module name (str) and returns a module
              or None if the module cannot be generated.
    """
    global _module_generator
    _module_generator = func


class ScyJavaTypesMetaFinder:
    """
    A meta path finder that intercepts imports from scyjava.types and
    dynamically generates modules at import time.
    """

    @classmethod
    def _get_base_package_name(cls) -> str:
        """Get the base package name for portability."""
        # Use __name__ for portability - this will be 'scyjava.types'
        return __name__

    def find_spec(
        self,
        fullname: str,
        path: Optional[Sequence[str]] = None,
        target: Optional[types.ModuleType] = None,
    ):
        """
        Find a module spec for dynamic module generation.

        Args:
            fullname: The fully qualified name of the module being imported
            path: The search path (unused)
            target: The target module (unused)

        Returns:
            A ModuleSpec if this finder should handle the import, None otherwise
        """
        base_package = self._get_base_package_name()

        # Only handle imports that start with our base package
        if not fullname.startswith(base_package + "."):
            return None

        # Don't handle the base package itself
        if fullname == base_package:
            return None

        # Create a module spec with our custom loader
        spec = importlib.util.spec_from_loader(
            fullname, ScyJavaTypesLoader(fullname), origin="dynamic"
        )
        return spec


class ScyJavaTypesLoader:
    """
    A module loader that calls the registered module generator function
    to create modules dynamically at import time.
    """

    def __init__(self, fullname: str):
        self.fullname = fullname

    def create_module(self, spec) -> Optional[types.ModuleType]:
        """
        Create a module by calling the registered generator function.

        Args:
            spec: The module spec

        Returns:
            The generated module or None to use default module creation
        """
        if _module_generator is None:
            raise ImportError(
                f"No module generator registered for {self.fullname}. "
                f"Call scyjava.types.set_module_generator() first."
            )

        # Call the registered function to generate the module
        module = _module_generator(self.fullname)
        if module is None:
            raise ImportError(
                f"Module generator failed to create module: {self.fullname}"
            )

        return module

    def exec_module(self, module: types.ModuleType) -> None:
        """
        Execute the module. Since our modules are generated dynamically,
        there's nothing to execute here.

        Args:
            module: The module to execute
        """
        # Module is already fully initialized by the generator function
        pass
    
    def load_module(self, fullname: str) -> types.ModuleType:
        """
        Load a module (deprecated method, kept for compatibility).
        
        Args:
            fullname: The fully qualified module name
            
        Returns:
            The loaded module
        """
        # Check if module is already in sys.modules
        if fullname in sys.modules:
            return sys.modules[fullname]
        
        # Create module spec and load it
        spec = importlib.util.spec_from_loader(fullname, self, origin="dynamic")
        if spec is None:
            raise ImportError(f"Failed to create spec for module: {fullname}")
            
        module = importlib.util.module_from_spec(spec)
        if module is None:
            raise ImportError(f"Failed to create module: {fullname}")
        
        # Add to sys.modules before exec
        sys.modules[fullname] = module
        
        try:
            if spec.loader:
                spec.loader.exec_module(module)
        except Exception:
            # Remove from sys.modules if exec fails
            sys.modules.pop(fullname, None)
            raise
            
        return module


def _install_meta_finder() -> None:
    """Install the meta path finder if it's not already installed."""
    finder_class = ScyJavaTypesMetaFinder

    # Check if our finder is already installed
    for finder in sys.meta_path:
        if isinstance(finder, finder_class):
            return

    # Install our finder at the beginning of meta_path
    sys.meta_path.insert(0, finder_class())


def _uninstall_meta_finder() -> None:
    """Remove the meta path finder."""
    finder_class = ScyJavaTypesMetaFinder

    # Remove all instances of our finder
    sys.meta_path[:] = [
        finder for finder in sys.meta_path if not isinstance(finder, finder_class)
    ]


# Install the meta finder when this module is imported
_install_meta_finder()


def get_registered_generator() -> Optional[Callable[[str], Optional[types.ModuleType]]]:
    """
    Get the currently registered module generator function.
    
    Returns:
        The registered generator function, or None if none is registered
    """
    return _module_generator


def is_meta_finder_installed() -> bool:
    """
    Check if the meta path finder is currently installed.
    
    Returns:
        True if the finder is installed, False otherwise
    """
    finder_class = ScyJavaTypesMetaFinder
    return any(isinstance(finder, finder_class) for finder in sys.meta_path)


def clear_generated_modules() -> None:
    """
    Clear all dynamically generated modules from sys.modules.
    
    This is useful for testing or when you want to regenerate modules
    with a different generator function.
    """
    base_package = __name__
    to_remove = [
        name for name in sys.modules.keys()
        if name.startswith(base_package + ".") and name != base_package
    ]
    
    for name in to_remove:
        sys.modules.pop(name, None)


def list_generated_modules() -> list[str]:
    """
    List all currently loaded dynamically generated modules.
    
    Returns:
        A list of module names that were generated by this meta finder
    """
    base_package = __name__
    generated = []
    
    for name, module in sys.modules.items():
        if (name.startswith(base_package + ".") and 
            name != base_package and
            hasattr(module, '__file__') and
            module.__file__ and
            ('<generated:' in module.__file__ or '<dynamic:' in module.__file__)):
            generated.append(name)
    
    return generated


# Example usage and testing functions
def _example_module_generator(module_name: str) -> Optional[types.ModuleType]:
    """
    Example module generator function for testing.

    This would be replaced with your actual module generation logic.

    Args:
        module_name: The full module name being imported

    Returns:
        A dynamically generated module
    """
    # Create a new module
    module = types.ModuleType(module_name)

    # Add some example attributes based on the module name
    parts = module_name.split(".")
    if len(parts) > 2:  # scyjava.types.XXX
        class_name = parts[-1]

        # Add a dummy class with the same name as the module
        dummy_class = type(
            class_name,
            (),
            {
                "__module__": module_name,
                "__doc__": f"Dynamically generated class for {class_name}",
            },
        )

        setattr(module, class_name, dummy_class)
        # Set __all__ as a regular attribute using setattr
        setattr(module, '__all__', [class_name])

    module.__file__ = f"<dynamic:{module_name}>"
    module.__package__ = ".".join(parts[:-1]) if len(parts) > 1 else None

    return module


def _test_dynamic_import():
    """Test function to verify the meta finder works."""
    # Set up the example generator
    set_module_generator(_example_module_generator)

    try:
        # This should trigger our meta finder
        # Type checker will complain since SomeTestClass doesn't exist statically
        from scyjava.types import SomeTestClass  # type: ignore

        print(f"Successfully imported: {SomeTestClass}")
        print(f"Module name: {SomeTestClass.__name__}")
        # Get the class from the module
        if hasattr(SomeTestClass, 'SomeTestClass'):
            test_class = getattr(SomeTestClass, 'SomeTestClass')
            print(f"Class module: {test_class.__module__}")
        return True
    except ImportError as e:
        print(f"Import failed: {e}")
        return False


if __name__ == "__main__":
    # Run test if this module is executed directly
    _test_dynamic_import()
