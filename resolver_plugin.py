#!/usr/bin/env python3
"""
Phase 3: Extensible resolver plugin protocol.

Defines the base classes and interfaces for domain-specific semantic resolvers.
Allows users to implement custom resolvers for their code domain.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Set, Any
from dataclasses import dataclass


@dataclass
class ResolutionContext:
    """Context passed to resolver plugins during resolution."""
    text: str                           # Full source code
    match_start: int                    # Start position of match
    match_end: int                      # End position of match
    captures: Dict[str, Optional[str]]  # Captured groups from pattern
    hints: Dict[str, str]               # Resolved hints (backend, scope, etc.)
    metadata: Dict[str, Any] = None     # Additional metadata
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ResolutionResult:
    """Result of resolver plugin execution."""
    resolved: bool                      # Whether resolution succeeded
    value: Optional[str] = None         # Resolved value if successful
    error: Optional[str] = None         # Error message if failed
    fallback: Optional[str] = None      # Fallback value if resolution failed
    confidence: float = 1.0             # Confidence level (0.0 to 1.0)


class ResolverPlugin(ABC):
    """
    Abstract base class for semantic resolver plugins.
    
    A plugin resolves domain-specific transformations based on code context.
    Plugins can:
    - Detect backend/language/version from surrounding code
    - Look up semantic paths from metadata registries
    - Transform captured values based on domain rules
    - Handle fallback and error cases gracefully
    """
    
    def __init__(self, registry: Optional[Dict[str, Any]] = None):
        """
        Initialize resolver plugin.
        
        :param registry: Optional domain-specific metadata registry
        """
        self.registry = registry or {}
        self._cache: Dict[str, str] = {}
    
    @abstractmethod
    def can_handle(self, function: str, backend: Optional[str] = None) -> bool:
        """
        Check if this plugin can handle the given function/backend.
        
        :param function: Function or symbol name
        :param backend: Optional backend identifier
        :return: True if this plugin handles this case
        """
        pass
    
    @abstractmethod
    def resolve(self, context: ResolutionContext, function: str) -> ResolutionResult:
        """
        Resolve a function call based on context.
        
        :param context: Resolution context with text, captures, hints
        :param function: Function or symbol name to resolve
        :return: ResolutionResult with resolved value or fallback
        """
        pass
    
    def detect_backend(self, context: ResolutionContext) -> Optional[str]:
        """
        Detect backend from surrounding code context.
        
        Override this in subclasses for domain-specific detection.
        
        :param context: Resolution context
        :return: Detected backend name or None
        """
        return context.hints.get('backend')
    
    def detect_scope(self, context: ResolutionContext) -> Optional[str]:
        """
        Detect scope type (test, fallback, gpu_block, etc.).
        
        Override this in subclasses for domain-specific scope detection.
        
        :param context: Resolution context
        :return: Detected scope type or None
        """
        return context.hints.get('scope_type')
    
    def get_backends(self, function: str) -> Set[str]:
        """
        Get available backends for a function.
        
        Override this in subclasses.
        
        :param function: Function name
        :return: Set of available backend names
        """
        return set()
    
    def clear_cache(self) -> None:
        """Clear internal resolution cache."""
        self._cache.clear()
    
    def get_cached(self, key: str) -> Optional[str]:
        """Get cached resolution result."""
        return self._cache.get(key)
    
    def cache_result(self, key: str, value: str) -> None:
        """Cache a resolution result."""
        self._cache[key] = value


class CompositeResolver:
    """
    Composite resolver that delegates to multiple plugins.
    
    Tries plugins in order until one succeeds.
    Useful for chaining multiple domain-specific resolvers.
    """
    
    def __init__(self, plugins: Optional[List[ResolverPlugin]] = None):
        """
        Initialize composite resolver.
        
        :param plugins: List of resolver plugins
        """
        self.plugins = plugins or []
    
    def add_plugin(self, plugin: ResolverPlugin) -> 'CompositeResolver':
        """
        Add a resolver plugin.
        
        :param plugin: ResolverPlugin instance
        :return: self for chaining
        """
        self.plugins.append(plugin)
        return self
    
    def resolve(self, context: ResolutionContext, function: str) -> ResolutionResult:
        """
        Resolve using first matching plugin.
        
        :param context: Resolution context
        :param function: Function name to resolve
        :return: ResolutionResult from first plugin that handles it
        """
        for plugin in self.plugins:
            if plugin.can_handle(function, context.hints.get('backend')):
                result = plugin.resolve(context, function)
                if result.resolved:
                    return result
        
        # No plugin succeeded
        return ResolutionResult(resolved=False, error="No plugin could resolve")
    
    def get_backends(self, function: str) -> Set[str]:
        """Get combined set of backends from all plugins."""
        backends = set()
        for plugin in self.plugins:
            backends.update(plugin.get_backends(function))
        return backends
    
    def clear_caches(self) -> None:
        """Clear caches in all plugins."""
        for plugin in self.plugins:
            plugin.clear_cache()


class BuiltinResolver(ResolverPlugin):
    """
    Resolver for builtin functions using metadata registry.
    
    Resolves (function, backend) -> semantic_path lookups.
    """
    
    def __init__(self, registry: Optional[Dict[str, Dict[str, str]]] = None):
        """
        Initialize builtin resolver.
        
        :param registry: Nested dict {function: {backend: path}}
        """
        super().__init__(registry)
    
    def can_handle(self, function: str, backend: Optional[str] = None) -> bool:
        """Check if function exists in registry."""
        return function in self.registry
    
    def resolve(self, context: ResolutionContext, function: str) -> ResolutionResult:
        """
        Resolve builtin function to semantic path.
        
        Tries preferred backend, then fallbacks, then default.
        """
        if function not in self.registry:
            return ResolutionResult(
                resolved=False,
                error=f"Function '{function}' not in registry"
            )
        
        # Get backends to try
        preferred = context.hints.get('backend')
        fallbacks = context.hints.get('fallback_backends', [])
        
        # Check cache
        cache_key = f"{function}:{preferred}"
        if cached := self.get_cached(cache_key):
            return ResolutionResult(resolved=True, value=cached)
        
        # Build lookup chain
        backends_to_try = []
        if preferred:
            backends_to_try.append(preferred)
        if isinstance(fallbacks, list):
            backends_to_try.extend(fallbacks)
        backends_to_try.append('default')
        
        # Try each backend
        func_registry = self.registry[function]
        for backend in backends_to_try:
            if backend in func_registry:
                value = func_registry[backend]
                self.cache_result(cache_key, value)
                return ResolutionResult(resolved=True, value=value)
        
        # No backend found
        return ResolutionResult(
            resolved=False,
            fallback=f"TODO_BUILTIN_{function}_{preferred}",
            error=f"No backend variant for '{function}' with backend '{preferred}'"
        )
    
    def get_backends(self, function: str) -> Set[str]:
        """Get available backends for function."""
        if function not in self.registry:
            return set()
        backends = set(self.registry[function].keys())
        backends.discard('default')
        return backends


class LibraryResolver(ResolverPlugin):
    """
    Resolver for library-specific functions.
    
    Maps function names to library paths/imports.
    """
    
    def __init__(self, registry: Optional[Dict[str, Dict[str, str]]] = None):
        """
        Initialize library resolver.
        
        :param registry: Nested dict {library: {function: path}}
        """
        super().__init__(registry)
    
    def can_handle(self, function: str, backend: Optional[str] = None) -> bool:
        """Check if function exists in any library."""
        for lib_funcs in self.registry.values():
            if function in lib_funcs:
                return True
        return False
    
    def resolve(self, context: ResolutionContext, function: str) -> ResolutionResult:
        """Resolve function to library path."""
        for library, funcs in self.registry.items():
            if function in funcs:
                path = funcs[function]
                return ResolutionResult(resolved=True, value=path)
        
        return ResolutionResult(
            resolved=False,
            fallback=f"TODO_LIBRARY_{function}",
            error=f"Function '{function}' not found in any library"
        )


class ConditionalResolver(ResolverPlugin):
    """
    Resolver that applies conditional transformations.
    
    Applies different resolutions based on context conditions.
    """
    
    def __init__(self):
        """Initialize conditional resolver."""
        super().__init__()
        self.conditions: List[tuple] = []  # List of (condition_func, resolver)
    
    def add_condition(
        self,
        condition: callable,
        resolver: ResolverPlugin
    ) -> 'ConditionalResolver':
        """
        Add conditional resolution.
        
        :param condition: Function that takes ResolutionContext and returns bool
        :param resolver: ResolverPlugin to use if condition is true
        :return: self for chaining
        """
        self.conditions.append((condition, resolver))
        return self
    
    def can_handle(self, function: str, backend: Optional[str] = None) -> bool:
        """Check if any condition's resolver can handle this."""
        for _, resolver in self.conditions:
            if resolver.can_handle(function, backend):
                return True
        return False
    
    def resolve(self, context: ResolutionContext, function: str) -> ResolutionResult:
        """
        Resolve using first matching condition.
        
        :param context: Resolution context
        :param function: Function name
        :return: ResolutionResult from matching resolver
        """
        for condition, resolver in self.conditions:
            if condition(context):
                result = resolver.resolve(context, function)
                if result.resolved:
                    return result
        
        return ResolutionResult(
            resolved=False,
            error="No condition matched"
        )


class TransformResolver(ResolverPlugin):
    """
    Resolver that transforms captured values.
    
    Applies custom transformations (upper, split, join, etc.).
    """
    
    def __init__(self, transforms: Optional[Dict[str, callable]] = None):
        """
        Initialize transform resolver.
        
        :param transforms: Dict of {transform_name: function}
        """
        super().__init__()
        self.transforms = transforms or {}
    
    def add_transform(self, name: str, func: callable) -> 'TransformResolver':
        """
        Add a transform function.
        
        :param name: Transform name
        :param func: Function that takes string and returns string
        :return: self for chaining
        """
        self.transforms[name] = func
        return self
    
    def can_handle(self, function: str, backend: Optional[str] = None) -> bool:
        """Check if this is a known transform."""
        return function in self.transforms
    
    def resolve(self, context: ResolutionContext, function: str) -> ResolutionResult:
        """
        Apply transform to captured value.
        
        :param context: Resolution context with captures
        :param function: Transform name
        :return: ResolutionResult with transformed value
        """
        if function not in self.transforms:
            return ResolutionResult(
                resolved=False,
                error=f"Unknown transform: {function}"
            )
        
        # Get input value (first capture or metadata)
        input_value = context.captures.get('value') or context.metadata.get('value')
        if not input_value:
            return ResolutionResult(
                resolved=False,
                error="No input value for transform"
            )
        
        try:
            transform_func = self.transforms[function]
            result = transform_func(str(input_value))
            return ResolutionResult(resolved=True, value=str(result))
        except Exception as e:
            return ResolutionResult(
                resolved=False,
                fallback=str(input_value),
                error=f"Transform failed: {e}"
            )


class ResolverChain:
    """
    Chain multiple resolvers with fallback logic.
    
    Tries each resolver in sequence, falling back if one fails.
    """
    
    def __init__(self):
        """Initialize resolver chain."""
        self.resolvers: List[ResolverPlugin] = []
        self.on_failure = 'placeholder'  # or 'skip', 'error'
    
    def add(self, resolver: ResolverPlugin) -> 'ResolverChain':
        """
        Add resolver to chain.
        
        :param resolver: ResolverPlugin to add
        :return: self for chaining
        """
        self.resolvers.append(resolver)
        return self
    
    def set_failure_mode(self, mode: str) -> 'ResolverChain':
        """
        Set behavior on resolution failure.
        
        :param mode: 'placeholder', 'skip', or 'error'
        :return: self for chaining
        """
        if mode not in ('placeholder', 'skip', 'error'):
            raise ValueError(f"Invalid failure mode: {mode}")
        self.on_failure = mode
        return self
    
    def resolve(self, context: ResolutionContext, function: str) -> ResolutionResult:
        """
        Resolve through chain of resolvers.
        
        :param context: Resolution context
        :param function: Function name to resolve
        :return: ResolutionResult from first successful resolver
        """
        last_error = None
        
        for resolver in self.resolvers:
            if not resolver.can_handle(function, context.hints.get('backend')):
                continue
            
            result = resolver.resolve(context, function)
            if result.resolved:
                return result
            
            last_error = result.error
        
        # All resolvers failed
        if self.on_failure == 'error':
            return ResolutionResult(resolved=False, error=last_error)
        elif self.on_failure == 'skip':
            return ResolutionResult(resolved=False, error="Skipped (no resolver matched)")
        else:  # placeholder
            fallback = f"TODO_CONTEXT_{function}"
            return ResolutionResult(
                resolved=False,
                fallback=fallback,
                error=last_error
            )
