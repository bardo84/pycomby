#!/usr/bin/env python3
"""
Phase 2: Metadata-driven builtin registry.

Maps (function, backend) tuples to semantic paths.
Supports multiple backends and fallback chains.
"""

import json
from typing import Dict, Set, Optional, Tuple, List
from pathlib import Path


class BuiltinRegistry:
    """
    Metadata-driven registry for builtin functions.
    
    Format: {
      "zeros": {
        "host": "builtins::array::creation::zeros::host_zeros",
        "wgpu": "builtins::array::creation::zeros::wgpu_zeros",
        "default": "builtins::array::creation::zeros::host_zeros"
      },
      "atan": {
        "host": "builtins::math::trigonometry::atan::host_atan",
        "wgpu": "builtins::math::trigonometry::atan::wgpu_matches_cpu"
      }
    }
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._registry: Dict[str, Dict[str, str]] = {}
    
    def add(self, function: str, backend: str, path: str) -> None:
        """
        Add a (function, backend) -> path mapping.
        
        :param function: Function name (e.g., "atan", "zeros")
        :param backend: Backend identifier (e.g., "host", "wgpu", "gpu")
        :param path: Resolved semantic path
        """
        if function not in self._registry:
            self._registry[function] = {}
        self._registry[function][backend] = path
    
    def add_default(self, function: str, path: str) -> None:
        """
        Add a default path for a function (used when backend unknown).
        
        :param function: Function name
        :param path: Resolved semantic path
        """
        self.add(function, 'default', path)
    
    def get(
        self,
        function: str,
        backend: Optional[str] = None,
        fallback_backends: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Resolve a function to a semantic path.
        
        :param function: Function name
        :param backend: Preferred backend (e.g., "host", "wgpu")
        :param fallback_backends: List of fallback backends to try
        :return: Semantic path or None if not found
        """
        if function not in self._registry:
            return None
        
        backends_to_try = []
        
        # Add preferred backend
        if backend:
            backends_to_try.append(backend)
        
        # Add fallbacks
        if fallback_backends:
            backends_to_try.extend(fallback_backends)
        
        # Add default
        backends_to_try.append('default')
        
        # Try each backend in order
        for b in backends_to_try:
            if b in self._registry[function]:
                return self._registry[function][b]
        
        return None
    
    def load_json(self, path: str) -> None:
        """
        Load registry from JSON file.
        
        Expected format:
        {
          "zeros": {"host": "path1", "wgpu": "path2", "default": "path1"},
          "atan": {"host": "path3", "wgpu": "path4"}
        }
        
        :param path: Path to JSON file
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            raise ValueError(f"Registry must be a dict, got {type(data).__name__}")
        
        for func, backends in data.items():
            if not isinstance(backends, dict):
                raise ValueError(
                    f"Registry['{func}'] must be a dict of backends, "
                    f"got {type(backends).__name__}"
                )
            
            for backend, path in backends.items():
                self.add(func, backend, path)
    
    def save_json(self, path: str) -> None:
        """Save registry to JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self._registry, f, indent=2)
    
    def get_backends(self, function: str) -> Set[str]:
        """Get all available backends for a function."""
        if function not in self._registry:
            return set()
        
        backends = set(self._registry[function].keys())
        backends.discard('default')
        return backends
    
    def has(self, function: str, backend: Optional[str] = None) -> bool:
        """Check if function (with optional backend) exists."""
        if function not in self._registry:
            return False
        
        if backend is None:
            return True
        
        return backend in self._registry[function]
    
    def merge(self, other: 'BuiltinRegistry') -> None:
        """Merge another registry into this one."""
        for func, backends in other._registry.items():
            for backend, path in backends.items():
                self.add(func, backend, path)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"BuiltinRegistry({len(self._registry)} functions)"


# Global registry instance
_global_registry = BuiltinRegistry()


def get_global_registry() -> BuiltinRegistry:
    """Get the global builtin registry."""
    return _global_registry


def resolve(
    function: str,
    backend: Optional[str] = None,
    fallback_backends: Optional[List[str]] = None
) -> Optional[str]:
    """
    Convenience function to resolve a function using global registry.
    
    :param function: Function name
    :param backend: Preferred backend
    :param fallback_backends: Fallback backends
    :return: Semantic path or None
    """
    return _global_registry.get(function, backend, fallback_backends)


def load_registry(path: str) -> BuiltinRegistry:
    """
    Load registry from JSON file and return it.
    
    :param path: Path to JSON file
    :return: Loaded BuiltinRegistry
    """
    registry = BuiltinRegistry()
    registry.load_json(path)
    return registry
