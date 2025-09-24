#!/usr/bin/env python3
"""
Test script demonstrating the scyjava.types meta path finder.
"""

import sys

sys.path.insert(0, "src")

import types
import scyjava.types


def java_class_generator(module_name: str) -> types.ModuleType:
    """
    Example generator that creates Java-like classes dynamically.

    This is where you would implement your actual Java class introspection
    and stub generation logic.
    """
    print(f"🔧 Generating module for: {module_name}")

    # Create the module
    module = types.ModuleType(module_name)
    module.__file__ = f"<generated:{module_name}>"

    # Extract class name from module path
    parts = module_name.split(".")
    if len(parts) > 2:  # scyjava.types.ClassName
        class_name = parts[-1]

        # Create a mock Java class
        def __init__(self, *args, **kwargs):
            self._java_args = args
            self._java_kwargs = kwargs
            print(f"📦 Created {class_name} instance with args={args}, kwargs={kwargs}")

        def toString(self):
            return f"{class_name}@{id(self):x}"

        # Create the class dynamically
        java_class = type(
            class_name,
            (),
            {
                "__module__": module_name,
                "__doc__": f"Dynamically generated Java class: {class_name}",
                "__init__": __init__,
                "toString": toString,
                # Add some Java-like methods
                "getClass": lambda self: type(self),
                "equals": lambda self, other: self is other,
                "hashCode": lambda self: hash(id(self)),
            },
        )

        # Add the class to the module
        setattr(module, class_name, java_class)
        setattr(module, "__all__", [class_name])

        print(f"✅ Generated class {class_name} in module {module_name}")

    return module


def main():
    print("🚀 Testing scyjava.types meta path finder")
    print("=" * 50)

    # Register our generator
    print("1. Registering module generator...")
    scyjava.types.set_module_generator(java_class_generator)

    print("\n2. Testing dynamic imports...")

    # Test 1: Import a "Java" class
    print("\n📥 Importing scyjava.types.ArrayList...")
    import scyjava.types.ArrayList as arraylist_module

    ArrayList = arraylist_module.ArrayList

    # Create an instance
    arr = ArrayList(10, "initial", capacity=100)
    print(f"Created ArrayList: {arr.toString()}")
    print(f"Class: {arr.getClass()}")

    # Test 2: Import another class
    print("\n📥 Importing scyjava.types.HashMap...")
    from scyjava.types import HashMap as hashmap_module

    HashMap = hashmap_module.HashMap

    map_obj = HashMap()
    print(f"Created HashMap: {map_obj.toString()}")

    # Test 3: Show that imports are cached
    print("\n📥 Re-importing ArrayList (should be cached)...")
    import scyjava.types.ArrayList as arraylist_module2

    print(f"Same module? {arraylist_module is arraylist_module2}")

    print("\n✅ All tests passed!")

    # Show what's in sys.modules
    print("\n📋 Dynamic modules in sys.modules:")
    for name, module in sys.modules.items():
        if name.startswith("scyjava.types.") and hasattr(module, "__file__"):
            if "<generated:" in str(module.__file__):
                print(f"  - {name}: {module.__file__}")


if __name__ == "__main__":
    main()
