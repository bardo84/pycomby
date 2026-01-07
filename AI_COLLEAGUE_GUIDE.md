# Pycomby for AI Colleagues: Quick Start Guide

**Purpose:** Guide AI code transformation agents on how to use Pycomby for structural code search and replacement.

---

## What Pycomby Does

Pycomby is a Comby-like **structural search and replace engine** designed for AI code transformation tasks:

```
Input: Source code + pattern + optional replacement
↓
Process: Find all matches, extract named captures, apply transformations
↓
Output: Modified code OR NDJSON matches (query mode)
```

Perfect for:
- ✅ Automated code migrations
- ✅ Structural refactoring
- ✅ Context-aware transformations
- ✅ Backend-specific code generation
- ✅ Domain-specific pattern matching

---

## Three Levels of Capability

### Level 1: Basic Structural Matching
```python
from pycomby import pycomby

pattern = 'function(:[arg1], :[arg2])'
replacement = 'renamed_function(:[arg1], :[arg2])'

result = pycomby(source_code, pattern, replacement)
# Returns: modified source code
```

**Use When:** You need simple find-and-replace with named captures

### Level 2: Context-Aware Transformations
```python
from pycomby import pycomby
from semantic_resolver import SemanticResolver
from builtin_registry import BuiltinRegistry

registry = BuiltinRegistry()
registry.load_json('registry.json')
resolver = SemanticResolver(registry)

pattern = 'call(:[func])'
replacement = 'backend_call(":[func.lookup(backend)]")'

result = pycomby(source_code, pattern, replacement,
                 semantic_resolver=resolver)
# Automatically detects backend from surrounding code
```

**Use When:** Transformations depend on detected code context (backend, scope, etc.)

### Level 3: Custom Domain Logic
```python
from pycomby import pycomby
from resolver_plugin import ResolverChain, ResolverPlugin
from pycomby import ResolutionContext, ResolutionResult

class MyDomainResolver(ResolverPlugin):
    def can_handle(self, function, backend=None):
        return function in self.registry
    
    def resolve(self, context: ResolutionContext, function: str) -> ResolutionResult:
        # Your custom domain-specific logic
        return ResolutionResult(resolved=True, value=resolved_value)

chain = ResolverChain()
chain.add(MyDomainResolver(config))
chain.set_failure_mode('placeholder')

# Use with pycomby or standalone
result = chain.resolve(context, 'function')
```

**Use When:** You need domain-specific transformation logic beyond general patterns

---

## Quick Start Examples

### Example 1: Rename All Function Calls

```python
from pycomby import pycomby

source = '''
fn test() {
    old_func(a, b);
    old_func(c, d);
}
'''

pattern = 'old_func(:[arg1], :[arg2])'
replacement = 'new_func(:[arg1], :[arg2])'

result = pycomby(source, pattern, replacement)
print(result)
```

### Example 2: Query Mode - Find All Matches

```python
from pycomby import pycomby

source = 'call(atan) and call(sin) and call(cos)'
pattern = 'call(:[func])'

matches = pycomby(source, pattern)  # No replacement = query mode
# Returns: [{'func': 'atan'}, {'func': 'sin'}, {'func': 'cos'}]
```

### Example 3: Static Registry Lookup (Phase 1)

```python
from pycomby import pycomby

registry = {
    'builtin:atan': 'builtins::math::trigonometry::atan::wgpu',
    'builtin:sin': 'builtins::math::trigonometry::sin::wgpu'
}

pattern = 'call(:[func])'
replacement = 'backend_call(":[func.lookup]")'

result = pycomby(source, pattern, replacement, registry=registry)
# :[func.lookup] replaces func name with registry value
```

### Example 4: Context Detection (Phase 2)

```python
from pycomby import pycomby
from semantic_resolver import SemanticResolver
from builtin_registry import BuiltinRegistry

registry_data = {
    'atan': {
        'host': 'math::atan::host',
        'wgpu': 'math::atan::wgpu',
        'default': 'math::atan::host'
    }
}

registry = BuiltinRegistry()
for func, backends in registry_data.items():
    for backend, path in backends.items():
        registry.add(func, backend, path)

resolver = SemanticResolver(registry)

code = '''
#[wgpu_test]
fn test() {
    call(atan)
}
'''

pattern = 'call(:[func])'
replacement = 'backend_call(":[func.lookup(backend)]")'

result = pycomby(code, pattern, replacement, semantic_resolver=resolver)
# Automatically detects #[wgpu] context and uses wgpu variant
```

### Example 5: Custom Resolver (Phase 3)

```python
from resolver_plugin import ResolverPlugin, ResolutionContext, ResolutionResult, ResolverChain

class LibraryResolver(ResolverPlugin):
    def can_handle(self, function, backend=None):
        return function in self.registry
    
    def resolve(self, context: ResolutionContext, function: str) -> ResolutionResult:
        if function not in self.registry:
            return ResolutionResult(resolved=False, error=f"Unknown: {function}")
        
        path = self.registry[function]
        return ResolutionResult(resolved=True, value=path)

# Use resolver
resolver = LibraryResolver({
    'atan': 'numpy.arctan',
    'sin': 'numpy.sin'
})

context = ResolutionContext(
    text=source_code,
    match_start=0,
    match_end=10,
    captures={'func': 'atan'},
    hints={'backend': 'numpy'}
)

result = resolver.resolve(context, 'atan')
if result.resolved:
    print(result.value)  # 'numpy.arctan'
```

---

## Pattern Syntax Guide

### Basic Captures
```
:[name]           # Capture any characters
:[name:word]      # Capture word characters (\w+)
:[name:digit]     # Capture digits (\d+)
:[name:num]       # Capture numbers (including floats, scientific notation)
:[name~regex]     # Capture matching regex
:[name?]          # Optional capture (may not match)
```

### Structural Macros
```
:[match:()]       # Match balanced parentheses
:[match:[]]       # Match balanced brackets
:[match:{}]       # Match balanced braces
:[match:(_)]      # Match inner content of parentheses (no parens in result)
:[match:[_]]      # Match inner content of brackets
:[match:{_}]      # Match inner content of braces
...               # Synonym for :[_] (matches anything including newlines)
```

### Operations (in replacements)
```
:[name.upper]           # Convert to uppercase
:[name.lower]           # Convert to lowercase
:[name.capitalize]      # Capitalize
:[name.strip]           # Strip whitespace
:[name.inc]             # Increment number
:[name.dec]             # Decrement number
:[name.filename]        # Extract filename from path
:[name.basename]        # Extract file basename
:[name.extension]       # Extract file extension
:[name.lookup]          # Phase 1: lookup in registry
:[name.lookup(backend)] # Phase 2: lookup with context
:[name.op1.op2]         # Chain operations
```

### Special Syntax
```
@hint name = operation()  # Phase 2: Hint directive for context resolution
```

---

## CLI Quick Reference

### Basic Query (find matches)
```bash
pycomby 'pattern' < input.txt
```

### Basic Replace
```bash
pycomby 'pattern' 'replacement' < input.txt
```

### From Files
```bash
pycomby -p pattern.txt -r replacement.txt -i input.txt
```

### Phase 1: Static Lookup
```bash
pycomby 'pattern' 'replacement' \
        --registry registry.json \
        < input.txt
```

### Phase 2: Context Detection
```bash
pycomby 'pattern' 'replacement' \
        --builtin-registry phase2.json \
        --detect-context \
        < input.txt
```

### Options
```
-i FILE              Input file (default: stdin)
-p FILE              Pattern from file
-r FILE              Replacement from file
--registry FILE      Phase 1 static lookup registry
--builtin-registry FILE   Phase 2 builtin registry
--detect-context     Enable Phase 2 context detection
--first              Only replace first match
```

### Exit Codes
```
0 = Success (match found and replaced)
1 = No match found
2 = Error (file not found, invalid input, etc.)
```

---

## For AI Colleagues: Integration Patterns

### Pattern 1: Simple Refactoring

```python
def refactor_function_names(source_code: str) -> str:
    """Rename functions across codebase."""
    from pycomby import pycomby
    
    renames = {
        'old_name': 'new_name',
        'deprecated_func': 'modern_func'
    }
    
    result = source_code
    for old, new in renames.items():
        pattern = f'{old}(:[args])'
        replacement = f'{new}(:[args])'
        result = pycomby(result, pattern, replacement)
    
    return result
```

### Pattern 2: Query and Process

```python
def find_and_process(source_code: str, pattern: str) -> list:
    """Find all matches and process them."""
    from pycomby import pycomby
    
    matches = pycomby(source_code, pattern)
    return [
        process_match(match)
        for match in matches
    ]
```

### Pattern 3: Context-Aware Transformation

```python
def transform_with_context(source_code: str) -> str:
    """Transform code based on detected context."""
    from pycomby import pycomby
    from semantic_resolver import SemanticResolver
    from builtin_registry import BuiltinRegistry
    
    registry = BuiltinRegistry()
    registry.load_json('registry.json')
    resolver = SemanticResolver(registry)
    
    return pycomby(
        source_code,
        pattern,
        replacement,
        semantic_resolver=resolver
    )
```

### Pattern 4: Custom Domain Resolver

```python
def transform_with_custom_logic(source_code: str) -> str:
    """Apply custom domain-specific transformations."""
    from resolver_plugin import ResolverChain
    
    chain = ResolverChain()
    chain.add(MyDomainResolver(config))
    chain.set_failure_mode('placeholder')
    
    # Apply transformations
    return apply_with_chain(source_code, pattern, chain)
```

---

## Best Practices

### 1. Start with Query Mode
```python
# First: understand what matches
matches = pycomby(source, pattern)

# Then: verify pattern matches what you expect
# Finally: add replacement
```

### 2. Test Incrementally
```python
# Small test cases first
test_code = "func(a, b)"
result = pycomby(test_code, pattern, replacement)
assert result == expected

# Then on larger codebase
```

### 3. Use Meaningful Capture Names
```python
# Good
pattern = 'provider::<:[module]>:::[func]>'

# Avoid
pattern = 'provider::<:[x]>:::[y]>'
```

### 4. Chain Transformations Carefully
```python
# Good: Multiple pycomby calls
result = pycomby(code, pattern1, replacement1)
result = pycomby(result, pattern2, replacement2)

# Avoid: Complex single pattern
```

### 5. Validate Results
```python
# Always check output
if result != source_code:
    print("Changes made")
else:
    print("No matches found")

# Check for placeholder fallbacks
if 'TODO_CONTEXT' in result:
    print("Warning: Unresolved lookups found")
```

---

## Handling Edge Cases

### Empty Matches
```python
result = pycomby(code, pattern, replacement)
if result == code:
    # No matches - pattern may be wrong
    print("Pattern did not match")
```

### Optional Captures
```python
pattern = 'function(:[arg1], :[arg2?])'
# arg2 may be None if not present

replacement = 'renamed(:[arg1]:[if_arg2])'  # Handle missing arg2
```

### Balanced Delimiters
```python
pattern = ':[content:()]'  # Matches balanced parens even with nesting
# Works with: (a), (a (b c) d), etc.
```

### Fallback on Failed Lookup
```python
# Phase 1/2: Unresolved lookups get placeholder
result = pycomby(code, pattern, replacement, registry=reg)
if 'TODO_CONTEXT' in result:
    # Lookup failed - add to manual review list
    print("Unresolved:", extract_todos(result))
```

---

## Performance Tips

### 1. Cache Registries
```python
# Good: Load once
registry = BuiltinRegistry()
registry.load_json('registry.json')
resolver = SemanticResolver(registry)

# Apply to many files
for file in files:
    result = pycomby(source, pattern, replacement, semantic_resolver=resolver)
```

### 2. Use --first for Single Match
```bash
# When you only need first match
pycomby 'pattern' 'replacement' --first < input.txt
```

### 3. Pipeline Processing
```python
# Process files in sequence
for file in get_files():
    source = read_file(file)
    result = pycomby(source, pattern, replacement, semantic_resolver=resolver)
    write_file(file, result)
```

---

## Debugging Failed Patterns

### Technique 1: Query Mode
```python
matches = pycomby(source, pattern)
if not matches:
    print("Pattern did not match")
    # Simplify pattern and try again
```

### Technique 2: Incremental Matching
```python
# Start simple
pattern = 'func'
matches = pycomby(source, pattern)

# Add details
pattern = 'func(:[args])'
matches = pycomby(source, pattern)

# More details
pattern = 'namespace::func(:[args])'
matches = pycomby(source, pattern)
```

### Technique 3: Print Captures
```python
matches = pycomby(source, pattern)
for match in matches:
    print(match)  # See what was captured
```

---

## Resource Links

- **[README.md](./README.md)** — Main documentation
- **[SYNTAX.md](./SYNTAX.md)** — Complete syntax reference
- **[PHASE_1_IMPLEMENTATION.md](./PHASE_1_IMPLEMENTATION.md)** — Phase 1 details
- **[PHASE_2_CLI_SUMMARY.md](./PHASE_2_CLI_SUMMARY.md)** — Phase 2 CLI guide
- **[PHASE_3_PLUGINS_GUIDE.md](./PHASE_3_PLUGINS_GUIDE.md)** — Phase 3 custom resolvers
- **[IMPLEMENTATION_COMPLETE.md](./IMPLEMENTATION_COMPLETE.md)** — Full status

---

## Summary

Pycomby is **production-ready** for AI colleagues:

✅ Simple patterns for basic find-replace  
✅ Context-aware transformations for smart replacements  
✅ Pluggable resolvers for custom domain logic  
✅ Robust error handling with fallbacks  
✅ 78/78 tests passing  
✅ Comprehensive documentation  

**Start with basic patterns, graduate to context-aware and custom resolvers as needed.**
