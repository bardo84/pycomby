#!/usr/bin/env python3
"""
Phase 3 tests: Extensible resolver plugin system.

Tests the plugin architecture for domain-specific semantic resolution.
"""

import unittest
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


class TestResolutionContext(unittest.TestCase):
    """Test ResolutionContext data class."""
    
    def test_create_context(self):
        """Create resolution context."""
        ctx = ResolutionContext(
            text="fn test() { call(func) }",
            match_start=15,
            match_end=19,
            captures={'func': 'atan'},
            hints={'backend': 'wgpu'}
        )
        
        self.assertEqual(ctx.text[:14], "fn test() { ca")
        self.assertEqual(ctx.captures['func'], 'atan')
        self.assertEqual(ctx.hints['backend'], 'wgpu')
    
    def test_context_metadata(self):
        """Context can hold arbitrary metadata."""
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={},
            metadata={'custom': 'value', 'count': 42}
        )
        
        self.assertEqual(ctx.metadata['custom'], 'value')
        self.assertEqual(ctx.metadata['count'], 42)


class TestResolutionResult(unittest.TestCase):
    """Test ResolutionResult data class."""
    
    def test_success_result(self):
        """Create successful result."""
        result = ResolutionResult(
            resolved=True,
            value="builtins::math::atan::wgpu"
        )
        
        self.assertTrue(result.resolved)
        self.assertEqual(result.value, "builtins::math::atan::wgpu")
        self.assertIsNone(result.error)
    
    def test_failure_result_with_fallback(self):
        """Create failure result with fallback."""
        result = ResolutionResult(
            resolved=False,
            fallback="TODO_ATAN",
            error="Function not found"
        )
        
        self.assertFalse(result.resolved)
        self.assertEqual(result.fallback, "TODO_ATAN")
        self.assertIsNotNone(result.error)
    
    def test_confidence_level(self):
        """Result can include confidence level."""
        result = ResolutionResult(
            resolved=True,
            value="path",
            confidence=0.85
        )
        
        self.assertEqual(result.confidence, 0.85)


class TestBuiltinResolver(unittest.TestCase):
    """Test BuiltinResolver plugin."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = {
            'atan': {
                'host': 'builtins::math::atan::host',
                'wgpu': 'builtins::math::atan::wgpu',
                'default': 'builtins::math::atan::host'
            },
            'zeros': {
                'host': 'builtins::array::zeros::host',
                'wgpu': 'builtins::array::zeros::wgpu'
            }
        }
        self.resolver = BuiltinResolver(self.registry)
    
    def test_can_handle_existing_function(self):
        """Check if resolver can handle existing function."""
        self.assertTrue(self.resolver.can_handle('atan'))
        self.assertTrue(self.resolver.can_handle('zeros'))
    
    def test_cannot_handle_missing_function(self):
        """Check if resolver rejects unknown function."""
        self.assertFalse(self.resolver.can_handle('unknown'))
    
    def test_resolve_with_preferred_backend(self):
        """Resolve function with preferred backend."""
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={'func': 'atan'},
            hints={'backend': 'wgpu'}
        )
        
        result = self.resolver.resolve(ctx, 'atan')
        
        self.assertTrue(result.resolved)
        self.assertEqual(result.value, 'builtins::math::atan::wgpu')
    
    def test_resolve_with_fallback_backend(self):
        """Resolve falls back to default if backend not available."""
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={'backend': 'unknown'}
        )
        
        result = self.resolver.resolve(ctx, 'atan')
        
        self.assertTrue(result.resolved)
        self.assertEqual(result.value, 'builtins::math::atan::host')
    
    def test_resolve_missing_function(self):
        """Resolve fails for unknown function."""
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={}
        )
        
        result = self.resolver.resolve(ctx, 'unknown')
        
        self.assertFalse(result.resolved)
        self.assertIsNotNone(result.error)
    
    def test_caching(self):
        """Resolver caches results."""
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={'backend': 'wgpu'}
        )
        
        # First resolution
        result1 = self.resolver.resolve(ctx, 'atan')
        self.assertTrue(result1.resolved)
        
        # Verify cache was populated
        cache_key = f"atan:wgpu"
        cached = self.resolver.get_cached(cache_key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached, result1.value)
    
    def test_get_backends(self):
        """Get available backends for function."""
        backends = self.resolver.get_backends('atan')
        self.assertEqual(backends, {'host', 'wgpu'})
        
        # Default is excluded
        self.assertNotIn('default', backends)


class TestLibraryResolver(unittest.TestCase):
    """Test LibraryResolver plugin."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = {
            'numpy': {
                'array': 'numpy.array',
                'zeros': 'numpy.zeros'
            },
            'torch': {
                'tensor': 'torch.Tensor',
                'cuda': 'torch.cuda.is_available'
            }
        }
        self.resolver = LibraryResolver(self.registry)
    
    def test_can_handle_library_function(self):
        """Check if resolver can handle library functions."""
        self.assertTrue(self.resolver.can_handle('array'))
        self.assertTrue(self.resolver.can_handle('tensor'))
    
    def test_resolve_to_library_path(self):
        """Resolve function to library path."""
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={}
        )
        
        result = self.resolver.resolve(ctx, 'array')
        
        self.assertTrue(result.resolved)
        self.assertEqual(result.value, 'numpy.array')
    
    def test_missing_function(self):
        """Resolve fails for unknown function."""
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={}
        )
        
        result = self.resolver.resolve(ctx, 'unknown')
        
        self.assertFalse(result.resolved)
        self.assertIn('TODO_LIBRARY', result.fallback)


class TestConditionalResolver(unittest.TestCase):
    """Test ConditionalResolver plugin."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.resolver = ConditionalResolver()
        
        # Condition 1: if backend is wgpu, use wgpu registry
        wgpu_registry = {'atan': {'wgpu': 'wgpu_atan'}}
        wgpu_resolver = BuiltinResolver(wgpu_registry)
        self.resolver.add_condition(
            lambda ctx: ctx.hints.get('backend') == 'wgpu',
            wgpu_resolver
        )
        
        # Condition 2: if backend is host, use host registry
        host_registry = {'atan': {'host': 'host_atan'}}
        host_resolver = BuiltinResolver(host_registry)
        self.resolver.add_condition(
            lambda ctx: ctx.hints.get('backend') == 'host',
            host_resolver
        )
    
    def test_resolve_with_first_condition(self):
        """Resolve using first matching condition."""
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={'backend': 'wgpu'}
        )
        
        result = self.resolver.resolve(ctx, 'atan')
        
        self.assertTrue(result.resolved)
        self.assertEqual(result.value, 'wgpu_atan')
    
    def test_resolve_with_second_condition(self):
        """Resolve using second matching condition."""
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={'backend': 'host'}
        )
        
        result = self.resolver.resolve(ctx, 'atan')
        
        self.assertTrue(result.resolved)
        self.assertEqual(result.value, 'host_atan')
    
    def test_no_matching_condition(self):
        """Fail when no condition matches."""
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={'backend': 'unknown'}
        )
        
        result = self.resolver.resolve(ctx, 'atan')
        
        self.assertFalse(result.resolved)


class TestTransformResolver(unittest.TestCase):
    """Test TransformResolver plugin."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.resolver = TransformResolver()
        self.resolver.add_transform('upper', str.upper)
        self.resolver.add_transform('lower', str.lower)
        self.resolver.add_transform('reverse', lambda s: s[::-1])
    
    def test_can_handle_known_transform(self):
        """Check if resolver can handle known transforms."""
        self.assertTrue(self.resolver.can_handle('upper'))
        self.assertTrue(self.resolver.can_handle('lower'))
    
    def test_apply_transform(self):
        """Apply transformation to value."""
        # Build context with value in both captures and metadata
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={'value': 'hello'},
            hints={},
        )
        
        result = self.resolver.resolve(ctx, 'upper')
        
        self.assertTrue(result.resolved)
        self.assertEqual(result.value, 'HELLO')
    
    def test_unknown_transform(self):
        """Fail for unknown transform."""
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={}
        )
        
        result = self.resolver.resolve(ctx, 'unknown')
        
        self.assertFalse(result.resolved)


class TestCompositeResolver(unittest.TestCase):
    """Test CompositeResolver (delegates to multiple plugins)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.composite = CompositeResolver()
        
        # Add multiple resolvers
        builtin_reg = {'atan': {'wgpu': 'builtin_atan', 'default': 'builtin_atan'}}
        self.composite.add_plugin(BuiltinResolver(builtin_reg))
        
        lib_reg = {'torch': {'sin': 'torch.sin'}}
        self.composite.add_plugin(LibraryResolver(lib_reg))
    
    def test_resolve_via_first_plugin(self):
        """Resolve using first plugin that handles it."""
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={}
        )
        
        result = self.composite.resolve(ctx, 'atan')
        
        self.assertTrue(result.resolved)
    
    def test_resolve_via_second_plugin(self):
        """Resolve using second plugin if first doesn't handle."""
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={}
        )
        
        result = self.composite.resolve(ctx, 'sin')
        
        self.assertTrue(result.resolved)
        self.assertEqual(result.value, 'torch.sin')
    
    def test_combined_backends(self):
        """Get combined backends from all plugins."""
        backends = self.composite.get_backends('atan')
        self.assertGreater(len(backends), 0)


class TestResolverChain(unittest.TestCase):
    """Test ResolverChain with fallback logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.chain = ResolverChain()
        
        # Chain multiple resolvers
        builtin = BuiltinResolver({'atan': {'wgpu': 'builtin_atan'}})
        self.chain.add(builtin)
    
    def test_resolve_through_chain(self):
        """Resolve through chain."""
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={'backend': 'wgpu'}
        )
        
        result = self.chain.resolve(ctx, 'atan')
        
        self.assertTrue(result.resolved)
    
    def test_failure_mode_placeholder(self):
        """Use placeholder on failure."""
        self.chain.set_failure_mode('placeholder')
        
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={}
        )
        
        result = self.chain.resolve(ctx, 'unknown')
        
        self.assertFalse(result.resolved)
        self.assertIn('TODO_CONTEXT', result.fallback)
    
    def test_failure_mode_error(self):
        """Raise error on failure."""
        self.chain.set_failure_mode('error')
        
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={}
        )
        
        result = self.chain.resolve(ctx, 'unknown')
        
        self.assertFalse(result.resolved)
    
    def test_invalid_failure_mode(self):
        """Reject invalid failure mode."""
        with self.assertRaises(ValueError):
            self.chain.set_failure_mode('invalid')


class TestCustomResolver(unittest.TestCase):
    """Test implementing custom resolver."""
    
    def test_custom_resolver_implementation(self):
        """Implement custom resolver for domain."""
        
        class DomainResolver(ResolverPlugin):
            """Custom resolver for specific domain."""
            
            def can_handle(self, function: str, backend=None):
                return function.startswith('domain_')
            
            def resolve(self, context: ResolutionContext, function: str):
                # Custom logic
                value = f"resolved_{function}"
                return ResolutionResult(resolved=True, value=value)
        
        resolver = DomainResolver()
        
        # Test it
        ctx = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={}
        )
        
        result = resolver.resolve(ctx, 'domain_func')
        
        self.assertTrue(result.resolved)
        self.assertEqual(result.value, 'resolved_domain_func')


class TestResolverIntegration(unittest.TestCase):
    """Integration tests for resolver plugins."""
    
    def test_complex_resolution_pipeline(self):
        """Test complex multi-level resolution."""
        # Build a complex resolver chain
        chain = ResolverChain()
        chain.set_failure_mode('placeholder')
        
        # Add builtin resolver
        builtins = {
            'atan': {
                'host': 'math::atan::host',
                'wgpu': 'math::atan::wgpu',
                'default': 'math::atan::host'
            }
        }
        chain.add(BuiltinResolver(builtins))
        
        # Add library resolver as fallback (correct structure: library -> function -> path)
        libs = {'torch': {'sin': 'torch.sin'}}
        chain.add(LibraryResolver(libs))
        
        # Test 1: Builtin resolution
        ctx1 = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={'backend': 'wgpu'}
        )
        result1 = chain.resolve(ctx1, 'atan')
        self.assertTrue(result1.resolved)
        self.assertIn('wgpu', result1.value)
        
        # Test 2: Library fallback
        ctx2 = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={}
        )
        result2 = chain.resolve(ctx2, 'sin')
        self.assertTrue(result2.resolved)
        self.assertEqual(result2.value, 'torch.sin')
        
        # Test 3: Unknown function (placeholder)
        ctx3 = ResolutionContext(
            text="",
            match_start=0,
            match_end=0,
            captures={},
            hints={}
        )
        result3 = chain.resolve(ctx3, 'unknown')
        self.assertFalse(result3.resolved)
        self.assertIn('TODO_CONTEXT', result3.fallback)


if __name__ == '__main__':
    unittest.main()
