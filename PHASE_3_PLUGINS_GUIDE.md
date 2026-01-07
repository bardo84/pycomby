# Phase 3: Extensible Resolver Plugin System — Complete Guide

**Status:** ✅ COMPLETE  
**Tests:** 30 new plugin tests, all passing  
**Total Tests:** 78/78 passing (48 Phase 1-2 + 30 Phase 3)  

---

## Overview

Phase 3 introduces an **extensible resolver plugin system** that allows domain-specific semantic resolution. Instead of hardcoding resolution logic, users can now implement custom resolvers for their specific code domain.

### Key Concept

**Before (Phase 2):** Semantic resolution is built into the engine
```python
# Fixed behavior: detect context → lookup in registry
hint = detect_context(text, start, end)
result = registry.get(function, hint.backend)
```

**After (Phase 3):** Pluggable resolvers with custom logic
```python
# Custom behavior: your resolver decides how to resolve
class MyResolver(ResolverPlugin):
    def resolve(self, context, function):
        # Your custom logic here
        pass

chain = ResolverChain().add(MyResolver()).add(BuiltinResolver())
```

---

## Architecture

### Core Components

```
ResolverPlugin (abstract base class)
    ├── BuiltinResolver       (function, backend) -> path lookups
    ├── LibraryResolver       (library, function) -> import paths
    ├── ConditionalResolver   condition-based dispatch
    ├── TransformResolver     value transformations
    └── CustomResolver        (user-implemented)

CompositeResolver            multiple plugins, first match wins

ResolverChain                sequential plugins with fallback modes
```

### Data Flow

```
┌──────────────────────┐
│ ResolutionContext    │
│ - text               │
│ - match_start/end    │
│ - captures           │
│ - hints              │
│ - metadata           │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────┐
│ ResolverPlugin.resolve()     │
│ (can_handle check first)     │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ ResolutionResult             │
│ - resolved: bool             │
│ - value: Optional[str]       │
│ - fallback: Optional[str]    │
│ - error: Optional[str]       │
│ - confidence: float          │
└──────────────────────────────┘
```

---

## Core Classes

### 1. ResolutionContext

Data class passed to resolvers with all necessary information.

```python
from resolver_plugin import ResolutionContext

context = ResolutionContext(
    text=source_code,
    match_start=15,
    match_end=25,
    captures={'func': 'atan', 'module': 'math'},
    hints={'backend': 'wgpu', 'scope': 'test'},
    metadata={'language': 'rust', 'version': '1.70'}
)
```

**Fields:**
- `text: str` — Full source code
- `match_start: int` — Match start position
- `match_end: int` — Match end position
- `captures: Dict[str, str]` — Pattern captures
- `hints: Dict[str, str]` — Resolved hints (backend, scope, etc.)
- `metadata: Dict[str, Any]` — Additional context (optional)

### 2. ResolutionResult

Return value from resolver plugins.

```python
from resolver_plugin import ResolutionResult

# Success
result = ResolutionResult(
    resolved=True,
    value="builtins::math::atan::wgpu"
)

# Failure with fallback
result = ResolutionResult(
    resolved=False,
    fallback="TODO_ATAN",
    error="Function not in registry",
    confidence=0.5
)
```

**Fields:**
- `resolved: bool` — Whether resolution succeeded
- `value: Optional[str]` — Resolved value if successful
- `fallback: Optional[str]` — Fallback value if failed
- `error: Optional[str]` — Error message if failed
- `confidence: float` — Confidence level (0.0 to 1.0)

### 3. ResolverPlugin (Abstract Base)

Base class for all resolver implementations.

```python
from resolver_plugin import ResolverPlugin

class MyResolver(ResolverPlugin):
    def can_handle(self, function: str, backend: Optional[str] = None) -> bool:
        """Check if this resolver can handle the function."""
        return function in self.registry
    
    def resolve(self, context: ResolutionContext, function: str) -> ResolutionResult:
        """Resolve function based on context."""
        # Your logic here
        return ResolutionResult(resolved=True, value=resolved_value)
```

**Methods to Override:**
- `can_handle(function, backend)` — Check if this resolver handles it
- `resolve(context, function)` — Perform resolution
- `detect_backend(context)` — Detect backend from context (optional)
- `detect_scope(context)` — Detect scope from context (optional)
- `get_backends(function)` — Return available backends (optional)

**Methods Provided:**
- `clear_cache()` — Clear internal resolution cache
- `get_cached(key)` — Get cached resolution result
- `cache_result(key, value)` — Cache a resolution result

---

## Built-in Resolvers

### 1. BuiltinResolver

Resolves (function, backend) -> semantic_path using nested registry.

```python
from resolver_plugin import BuiltinResolver

registry = {
    'atan': {
        'host': 'builtins::math::atan::host',
        'wgpu': 'builtins::math::atan::wgpu',
        'default': 'builtins::math::atan::host'
    }
}

resolver = BuiltinResolver(registry)

# In context with backend='wgpu':
result = resolver.resolve(context, 'atan')
# Returns: ResolutionResult(resolved=True, value='builtins::math::atan::wgpu')
```

**Features:**
- Tries preferred backend first
- Falls back to alternatives and 'default'
- Caches results for performance
- Returns available backends for function

### 2. LibraryResolver

Resolves (library, function) -> import_path.

```python
from resolver_plugin import LibraryResolver

registry = {
    'numpy': {
        'array': 'numpy.array',
        'zeros': 'numpy.zeros'
    },
    'torch': {
        'tensor': 'torch.Tensor'
    }
}

resolver = LibraryResolver(registry)

result = resolver.resolve(context, 'array')
# Returns: ResolutionResult(resolved=True, value='numpy.array')
```

### 3. ConditionalResolver

Dispatches to different resolvers based on context conditions.

```python
from resolver_plugin import ConditionalResolver, BuiltinResolver

resolver = ConditionalResolver()

# If in WGPU context, use wgpu resolver
wgpu_reg = {'atan': {'wgpu': 'wgpu_atan'}}
resolver.add_condition(
    lambda ctx: ctx.hints.get('backend') == 'wgpu',
    BuiltinResolver(wgpu_reg)
)

# If in host context, use host resolver
host_reg = {'atan': {'host': 'host_atan'}}
resolver.add_condition(
    lambda ctx: ctx.hints.get('backend') == 'host',
    BuiltinResolver(host_reg)
)
```

### 4. TransformResolver

Applies value transformations (upper, lower, split, etc.).

```python
from resolver_plugin import TransformResolver

resolver = TransformResolver()
resolver.add_transform('upper', str.upper)
resolver.add_transform('lower', str.lower)
resolver.add_transform('reverse', lambda s: s[::-1])
resolver.add_transform('len', lambda s: str(len(s)))

# Use in context with captures={'value': 'hello'}
result = resolver.resolve(context, 'upper')
# Returns: ResolutionResult(resolved=True, value='HELLO')
```

### 5. CompositeResolver

Tries multiple plugins until one succeeds.

```python
from resolver_plugin import CompositeResolver, BuiltinResolver, LibraryResolver

composite = CompositeResolver()
composite.add_plugin(BuiltinResolver(builtins_reg))
composite.add_plugin(LibraryResolver(libs_reg))

result = composite.resolve(context, 'atan')
# Tries BuiltinResolver first, then LibraryResolver
```

---

## Advanced Usage: ResolverChain

Chain multiple resolvers with fallback behavior.

```python
from resolver_plugin import ResolverChain, BuiltinResolver, LibraryResolver

chain = ResolverChain()
chain.add(BuiltinResolver(builtins))
chain.add(LibraryResolver(libs))
chain.set_failure_mode('placeholder')  # or 'skip', 'error'

result = chain.resolve(context, 'unknown_func')
# If resolution fails: returns placeholder "TODO_CONTEXT_unknown_func"
```

**Failure Modes:**
- `'placeholder'` — Return `TODO_CONTEXT_<function>` (default)
- `'skip'` — Return unresolved with error
- `'error'` — Return unresolved with error (strict mode)

---

## Implementing Custom Resolvers

### Simple Example: Function Name Transformation

```python
from resolver_plugin import ResolverPlugin, ResolutionResult, ResolutionContext

class PrefixResolver(ResolverPlugin):
    """Add domain prefix to function names."""
    
    def __init__(self, prefix='domain'):
        super().__init__()
        self.prefix = prefix
    
    def can_handle(self, function: str, backend=None):
        return True  # Handle everything
    
    def resolve(self, context: ResolutionContext, function: str) -> ResolutionResult:
        backend = context.hints.get('backend', 'default')
        value = f"{self.prefix}::{function}::{backend}"
        return ResolutionResult(resolved=True, value=value)

# Use it
resolver = PrefixResolver('mylib')
result = resolver.resolve(context, 'atan')
# Returns: ResolutionResult(resolved=True, value='mylib::atan::wgpu')
```

### Complex Example: Language-Specific Resolver

```python
from resolver_plugin import ResolverPlugin, ResolutionResult, ResolutionContext

class RustResolver(ResolverPlugin):
    """Resolve Rust crate paths."""
    
    def __init__(self, crate_manifest):
        super().__init__(crate_manifest)
    
    def can_handle(self, function: str, backend=None):
        return function in self.registry
    
    def detect_backend(self, context: ResolutionContext):
        # Detect if code is in a GPU block
        text = context.text[context.match_start-50:context.match_start]
        if '#[gpu]' in text or 'gpu_kernel' in text:
            return 'gpu'
        return 'cpu'
    
    def resolve(self, context: ResolutionContext, function: str) -> ResolutionResult:
        backend = self.detect_backend(context)
        
        if function not in self.registry:
            return ResolutionResult(resolved=False, error=f"Unknown: {function}")
        
        entry = self.registry[function]
        if backend in entry:
            path = entry[backend]
        else:
            path = entry.get('default')
        
        return ResolutionResult(resolved=True, value=path, confidence=0.9)
```

### Plugin with State Management

```python
from resolver_plugin import ResolverPlugin, ResolutionResult, ResolutionContext

class CachingResolver(ResolverPlugin):
    """Resolver with custom caching strategy."""
    
    def __init__(self, ttl_seconds=3600):
        super().__init__()
        self.ttl = ttl_seconds
        self._timestamps = {}
    
    def can_handle(self, function: str, backend=None):
        return function in self.registry
    
    def resolve(self, context: ResolutionContext, function: str) -> ResolutionResult:
        import time
        
        # Check cache with TTL
        cache_key = f"{function}:{context.hints.get('backend')}"
        if cache_key in self._cache:
            timestamp = self._timestamps.get(cache_key, 0)
            if time.time() - timestamp < self.ttl:
                return ResolutionResult(
                    resolved=True,
                    value=self._cache[cache_key]
                )
        
        # Perform resolution
        value = self._resolve_impl(context, function)
        
        # Cache result
        self.cache_result(cache_key, value)
        self._timestamps[cache_key] = time.time()
        
        return ResolutionResult(resolved=True, value=value)
    
    def _resolve_impl(self, context, function):
        # Your resolution logic
        return f"resolved_{function}"
```

---

## Integration with Pycomby Core

### Method 1: Direct Usage

```python
from resolver_plugin import BuiltinResolver, ResolutionContext
from pycomby import pycomby

# Create resolver
resolver = BuiltinResolver(registry)

# Create context
context = ResolutionContext(
    text=source_code,
    match_start=0,
    match_end=10,
    captures={'func': 'atan'},
    hints={'backend': 'wgpu'}
)

# Resolve
result = resolver.resolve(context, 'atan')
```

### Method 2: Chain in SemanticResolver

```python
from semantic_resolver import SemanticResolver
from resolver_plugin import BuiltinResolver, ResolverChain

# Build plugin chain
chain = ResolverChain()
chain.add(BuiltinResolver(registry))

# Integrate with SemanticResolver
semantic_resolver = SemanticResolver(builtin_registry=None)
# (Future: deep integration planned)
```

### Method 3: CLI (Future Enhancement)

```bash
# Pass custom resolver configuration
pycomby pattern replacement \
        --builtin-registry registry.json \
        --resolver-plugin MyDomainResolver \
        --resolver-config config.json \
        input.txt
```

---

## Testing Custom Resolvers

```python
import unittest
from resolver_plugin import ResolverPlugin, ResolutionContext, ResolutionResult

class TestMyResolver(unittest.TestCase):
    def setUp(self):
        self.resolver = MyResolver(config)
    
    def test_can_handle(self):
        self.assertTrue(self.resolver.can_handle('atan'))
        self.assertFalse(self.resolver.can_handle('unknown'))
    
    def test_resolution(self):
        context = ResolutionContext(
            text="fn test() {}",
            match_start=0,
            match_end=8,
            captures={'func': 'atan'},
            hints={'backend': 'wgpu'}
        )
        
        result = self.resolver.resolve(context, 'atan')
        
        self.assertTrue(result.resolved)
        self.assertIsNotNone(result.value)
    
    def test_fallback(self):
        context = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={}
        )
        
        result = self.resolver.resolve(context, 'unknown')
        
        self.assertFalse(result.resolved)
        self.assertIsNotNone(result.fallback)
```

---

## Best Practices

### 1. Keep Resolvers Focused

```python
# Good: Single responsibility
class BuiltinResolver(ResolverPlugin):
    """Only handles builtin registries."""

# Avoid: Multiple concerns mixed
class SuperResolver(ResolverPlugin):
    """Handles builtins, libraries, AND transforms AND caching."""
```

### 2. Use Composition Over Inheritance

```python
# Good: Compose resolvers
chain = ResolverChain()
chain.add(BuiltinResolver(reg1))
chain.add(LibraryResolver(reg2))
chain.add(TransformResolver(transforms))

# Avoid: Giant monolithic resolver
class MonolithicResolver(ResolverPlugin):
    # 500 lines of mixed logic
```

### 3. Cache Aggressively

```python
def resolve(self, context, function):
    cache_key = f"{function}:{context.hints.get('backend')}"
    if cached := self.get_cached(cache_key):
        return ResolutionResult(resolved=True, value=cached)
    
    # Expensive operation
    value = expensive_lookup(function)
    self.cache_result(cache_key, value)
    return ResolutionResult(resolved=True, value=value)
```

### 4. Provide Meaningful Errors

```python
return ResolutionResult(
    resolved=False,
    fallback="TODO_ATAN",
    error="Function 'atan' not found in registry 'wgpu'",
    confidence=0.0
)
```

### 5. Test Thoroughly

```python
def test_resolution_chain(self):
    """Test all backends in order."""
    backends = ['preferred', 'fallback1', 'fallback2', 'default']
    for backend in backends:
        context = ResolutionContext(..., hints={'backend': backend})
        result = self.resolver.resolve(context, 'atan')
        self.assertTrue(result.resolved)
```

---

## Performance Considerations

### Caching Strategy

```python
# Enable caching for expensive operations
resolver = BuiltinResolver(registry)

# Cache key includes all factors
cache_key = f"{function}:{backend}:{scope}"

# Clear cache when registry updates
resolver.clear_cache()
```

### Lazy Evaluation

```python
# Don't process all backends at once
def resolve(self, context, function):
    # Try one backend at a time
    for backend in backends_to_try:
        if result := self.try_backend(backend):
            return result
    # Only reaches fallback if all fail
```

### Batch Operations

```python
# For multiple resolutions, use chain with cache
chain = ResolverChain()
for function in functions:
    result = chain.resolve(context, function)  # Cache improves subsequent calls
```

---

## Real-World Example: RunMat Domain Resolver

```python
from resolver_plugin import ResolverPlugin, ResolutionResult, ResolutionContext

class RunMatResolver(ResolverPlugin):
    """Resolver for RunMat acceleration provider migrations."""
    
    def __init__(self, builtin_registry):
        super().__init__(builtin_registry)
    
    def can_handle(self, function: str, backend=None):
        return function in self.registry
    
    def detect_backend(self, context: ResolutionContext):
        """Detect RunMat backend from surrounding code."""
        code_before = context.text[max(0, context.match_start-500):context.match_start]
        
        if '#[wgpu_test]' in code_before:
            return 'wgpu'
        elif '#[gpu' in code_before:
            return 'gpu'
        elif '#[test]' in code_before:
            return 'host'
        elif 'GpuTensor' in code_before:
            return 'gpu'
        else:
            return 'host'
    
    def resolve(self, context: ResolutionContext, function: str) -> ResolutionResult:
        if function not in self.registry:
            return ResolutionResult(
                resolved=False,
                fallback=f"TODO_RUNMAT_{function}",
                error=f"Function '{function}' not in RunMat registry"
            )
        
        backend = self.detect_backend(context)
        entry = self.registry[function]
        
        path = entry.get(backend) or entry.get('default')
        
        return ResolutionResult(
            resolved=True,
            value=path,
            confidence=0.95 if backend in entry else 0.7
        )

# Usage
runmat = RunMatResolver(runmat_registry)
result = runmat.resolve(context, 'atan')
```

---

## Files Reference

### Implementation
- `resolver_plugin.py` — Plugin system (400+ lines)

### Tests
- `test_phase3_plugins.py` — 30 comprehensive tests

### Documentation
- `PHASE_3_PLUGINS_GUIDE.md` — This file

---

## API Reference Quick Start

```python
from resolver_plugin import (
    ResolutionContext,
    ResolutionResult,
    ResolverPlugin,
    BuiltinResolver,
    LibraryResolver,
    ConditionalResolver,
    TransformResolver,
    CompositeResolver,
    ResolverChain,
)

# Create context
ctx = ResolutionContext(text, start, end, captures, hints)

# Create resolver
resolver = BuiltinResolver(registry)

# Resolve
result = resolver.resolve(ctx, 'function')

# Check result
if result.resolved:
    print(result.value)
else:
    print(result.fallback)
```

---

## Next Steps

1. **Implement domain-specific resolvers** for your code
2. **Chain resolvers** for comprehensive coverage
3. **Test thoroughly** on your actual code
4. **Optimize** with caching and lazy evaluation
5. **Report edge cases** for Phase 3.5+ enhancements

---

**Phase 3 Status:** ✅ Complete and production-ready
