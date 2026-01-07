#!/usr/bin/env python3
"""
Phase 2: Semantic resolver that combines context detection with registry lookups.

Implements the @hint directive and context-aware replacement.
"""

import re
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass

from context_detector import detect_context, detect_backends, ContextHint
from builtin_registry import BuiltinRegistry, resolve as resolve_builtin


@dataclass
class HintDirective:
    """Represents a @hint directive in a pattern."""
    name: str                          # e.g., "backend"
    operation: str                     # e.g., "detect_from_context"
    args: List[str] = None             # Additional arguments
    
    def __post_init__(self):
        if self.args is None:
            self.args = []


class SemanticResolver:
    """
    Semantic resolver for Phase 2 context-aware transformations.
    
    Supports:
    - @hint directives in patterns
    - Context-aware backend detection
    - Registry-driven suffix resolution
    """
    
    # Hint directive regex: @hint name = operation(args)
    HINT_PATTERN = re.compile(
        r'@hint\s+(\w+)\s*=\s*(\w+)\s*\(([^)]*)\)',
        re.IGNORECASE
    )
    
    def __init__(self, registry: Optional[BuiltinRegistry] = None):
        """
        Initialize resolver.
        
        :param registry: BuiltinRegistry to use (default: global)
        """
        self.registry = registry
        self.hint_handlers: Dict[str, Callable] = {
            'detect_from_context': self._handle_detect_from_context,
            'detect_backends': self._handle_detect_backends,
        }
    
    def extract_hints(self, pattern: str) -> tuple[str, List[HintDirective]]:
        """
        Extract @hint directives from a pattern.
        
        :param pattern: Pattern string (may contain @hint lines)
        :return: (cleaned_pattern, list_of_hints)
        """
        hints = []
        lines = pattern.split('\n')
        cleaned_lines = []
        
        for line in lines:
            match = self.HINT_PATTERN.search(line)
            if match:
                name, operation, args_str = match.groups()
                args = [a.strip() for a in args_str.split(',') if a.strip()]
                hints.append(HintDirective(name, operation, args))
            else:
                cleaned_lines.append(line)
        
        cleaned_pattern = '\n'.join(cleaned_lines)
        return cleaned_pattern, hints
    
    def resolve(
        self,
        text: str,
        match_start: int,
        match_end: int,
        captures: Dict[str, Optional[str]],
        hints: List[HintDirective]
    ) -> Dict[str, str]:
        """
        Resolve hint values for a match.
        
        :param text: Full source code
        :param match_start: Start of match
        :param match_end: End of match
        :param captures: Captured groups from pattern match
        :param hints: Hint directives from pattern
        :return: Dict of {hint_name: resolved_value}
        """
        resolved = {}
        
        for hint in hints:
            handler = self.hint_handlers.get(hint.operation)
            if handler:
                value = handler(text, match_start, match_end, captures, hint.args)
                resolved[hint.name] = value
        
        return resolved
    
    def _handle_detect_from_context(
        self,
        text: str,
        match_start: int,
        match_end: int,
        captures: Dict[str, Optional[str]],
        args: List[str]
    ) -> Optional[str]:
        """
        @hint backend = detect_from_context()
        
        Detects backend from surrounding code.
        Returns: "host", "wgpu", or None
        """
        hint = detect_context(text, match_start, match_end)
        return hint.backend
    
    def _handle_detect_backends(
        self,
        text: str,
        match_start: int,
        match_end: int,
        captures: Dict[str, Optional[str]],
        args: List[str]
    ) -> str:
        """
        @hint backends = detect_backends()
        
        Detects all possible backends.
        Returns: comma-separated list (e.g., "host,wgpu")
        """
        backends = detect_backends(text, match_start, match_end)
        return ','.join(sorted(backends)) if backends else ''
    
    def resolve_registry_lookup(
        self,
        function: str,
        backend: Optional[str] = None,
        fallback_backends: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Resolve a function via registry lookup.
        
        :param function: Function name
        :param backend: Preferred backend
        :param fallback_backends: Fallback backends
        :return: Semantic path or None
        """
        if self.registry:
            return self.registry.get(function, backend, fallback_backends)
        else:
            # Use global registry
            return resolve_builtin(function, backend, fallback_backends)


class TemplateRenderer:
    """
    Extended template renderer that supports context hints.
    
    Syntax extensions:
    - :[name.lookup(backend)] – Registry lookup with specified backend
    - :[name.lookup(hint_name)] – Registry lookup using resolved hint
    """
    
    def __init__(self, resolver: SemanticResolver):
        """
        Initialize renderer.
        
        :param resolver: SemanticResolver for context hints
        """
        self.resolver = resolver
    
    def render(
        self,
        template: str,
        captures: Dict[str, Optional[str]],
        resolved_hints: Dict[str, str]
    ) -> str:
        """
        Render template with captures and resolved hints.
        
        :param template: Template string
        :param captures: Captured values from pattern
        :param resolved_hints: Resolved hint values
        :return: Rendered template
        """
        def replacer(m):
            placeholder = m.group(1)
            parts = placeholder.split('.')
            field = parts[0]
            ops = parts[1:]
            
            # Get field value (from captures or hints)
            if field in captures and captures[field] is not None:
                value = str(captures[field])
            elif field in resolved_hints and resolved_hints[field] is not None:
                value = str(resolved_hints[field])
            else:
                return m.group(0)
            
            # Apply operations
            for op_spec in ops:
                if op_spec.startswith('lookup(') and op_spec.endswith(')'):
                    # :[func.lookup(backend)] or :[func.lookup(hint)]
                    arg = op_spec[7:-1]
                    
                    # If arg is a hint name, resolve it
                    backend = resolved_hints.get(arg) or arg
                    
                    # Lookup in registry
                    resolved = self.resolver.resolve_registry_lookup(value, backend)
                    if resolved:
                        value = resolved
                    else:
                        value = f"TODO_CONTEXT_{value}_{backend}"
                else:
                    # Other operations not yet supported in Phase 2
                    return m.group(0)
            
            return value
        
        return re.sub(r':\[([^\]]+)\]', replacer, template)


def apply_hints_to_replacement(
    template: str,
    captures: Dict[str, Optional[str]],
    resolved_hints: Dict[str, str],
    resolver: SemanticResolver
) -> str:
    """
    Convenience function to apply hints to a replacement template.
    
    :param template: Replacement template
    :param captures: Captured values from pattern
    :param resolved_hints: Resolved hint values
    :param resolver: SemanticResolver instance
    :return: Rendered template
    """
    renderer = TemplateRenderer(resolver)
    return renderer.render(template, captures, resolved_hints)
