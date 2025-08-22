# scyjava.types Meta Path Finder Infrastructure

This module provides a complete meta path finder infrastructure for `scyjava.types` that:

## Core Features

1. **Intercepts imports** from `scyjava.types.XXX` using a custom meta path finder
2. **Calls a user-defined function** at import time to generate the module
3. **Executes the import** after the module is generated
4. **Uses `__name__` for portability** - works regardless of where the module is located

## Key Components

### ScyJavaTypesMetaFinder
- Implements the `find_spec()` method required by Python's import system
- Only handles imports that start with `scyjava.types.`
- Creates a `ModuleSpec` with our custom loader

### ScyJavaTypesLoader  
- Implements `create_module()` and `exec_module()` for the new import system
- Also implements `load_module()` for backward compatibility
- Calls the registered generator function to create modules

### Module Generator Function
- User-provided function that receives the full module name
- Must return a `types.ModuleType` instance
- Called exactly once per unique import (modules are cached)

## API Functions

- `set_module_generator(func)` - Register your module generation function
- `get_registered_generator()` - Get the currently registered function  
- `is_meta_finder_installed()` - Check if the meta finder is active
- `clear_generated_modules()` - Remove generated modules from cache
- `list_generated_modules()` - List all currently loaded generated modules

## Usage Pattern

```python
import scyjava.types

def my_generator(module_name: str) -> types.ModuleType:
    # module_name will be something like "scyjava.types.ArrayList"
    module = types.ModuleType(module_name)
    
    # Extract class name from the module path
    class_name = module_name.split('.')[-1]  # "ArrayList"
    
    # Generate your class/content here
    generated_class = create_java_stub(class_name)
    setattr(module, class_name, generated_class)
    
    module.__file__ = f"<generated:{module_name}>"
    return module

# Register the generator
scyjava.types.set_module_generator(my_generator)

# Now imports will trigger the generator
import scyjava.types.ArrayList as al_module
ArrayList = al_module.ArrayList

# Or using from-import
from scyjava.types import HashMap as hm_module  
HashMap = hm_module.HashMap
```

## Error Handling

- If no generator is registered, imports raise `ImportError`
- If the generator returns `None`, imports raise `ImportError`
- Generator exceptions propagate to the import statement

## Caching

- Modules are automatically cached in `sys.modules` 
- Subsequent imports of the same module return the cached version
- Use `clear_generated_modules()` to force regeneration

This infrastructure provides the foundation for dynamic Java class stub generation
at import time, enabling type-safe imports with lazy initialization.
