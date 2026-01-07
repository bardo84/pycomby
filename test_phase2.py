#!/usr/bin/env python3
"""
Phase 2 tests: Context detection, registry, and semantic resolver.
"""

import unittest
import tempfile
from pathlib import Path

from context_detector import ContextDetector, detect_context, detect_backends
from builtin_registry import BuiltinRegistry, load_registry
from semantic_resolver import SemanticResolver, TemplateRenderer, apply_hints_to_replacement


class TestContextDetector(unittest.TestCase):
    """Test context detection from surrounding code."""
    
    def setUp(self):
        self.detector = ContextDetector(context_window=10)
    
    def test_detect_wgpu_context(self):
        """Test detection of WGPU backend hint."""
        code = '''
        #[wgpu_test]
        fn test_atan() {
            let result = provider::<atan>
        }
        '''
        pos_start = code.find('provider')
        pos_end = pos_start + 8
        
        hint = self.detector.detect(code, pos_start, pos_end)
        self.assertIsNotNone(hint.backend)
        self.assertIn('wgpu', hint.backend.lower())
    
    def test_detect_host_context(self):
        """Test detection of host/CPU backend hint."""
        code = '''
        #[host_test]
        fn test_add() {
            let result = provider::<add>
        }
        '''
        pos_start = code.find('provider')
        pos_end = pos_start + 8
        
        hint = self.detector.detect(code, pos_start, pos_end)
        self.assertIsNotNone(hint.backend)
        self.assertIn('host', hint.backend.lower())
    
    def test_detect_gpu_tensor(self):
        """Test detection of GPU context via GpuTensor."""
        code = '''
        fn process() {
            let tensor: GpuTensor = ...
            let result = provider::<multiply>
        }
        '''
        pos_start = code.find('provider')
        pos_end = pos_start + 8
        
        hint = self.detector.detect(code, pos_start, pos_end)
        # Should detect GPU context
        self.assertIsNotNone(hint.attributes)
    
    def test_detect_backends_set(self):
        """Test getting set of possible backends."""
        code = '''
        if fallback_available {
            let result = provider::<divide>
        }
        '''
        pos_start = code.find('provider')
        pos_end = pos_start + 8
        
        backends = detect_backends(code, pos_start, pos_end)
        # Fallback context should suggest both host and wgpu
        self.assertTrue(len(backends) >= 1)


class TestBuiltinRegistry(unittest.TestCase):
    """Test metadata-driven builtin registry."""
    
    def setUp(self):
        self.registry = BuiltinRegistry()
    
    def test_add_and_get_mapping(self):
        """Test adding and retrieving a mapping."""
        self.registry.add('atan', 'host', 'builtins::math::atan::host')
        self.registry.add('atan', 'wgpu', 'builtins::math::atan::wgpu')
        
        # Get specific backend
        result = self.registry.get('atan', 'host')
        self.assertEqual(result, 'builtins::math::atan::host')
        
        result = self.registry.get('atan', 'wgpu')
        self.assertEqual(result, 'builtins::math::atan::wgpu')
    
    def test_fallback_to_default(self):
        """Test fallback to default mapping."""
        self.registry.add('zeros', 'default', 'builtins::zeros::default')
        self.registry.add('zeros', 'wgpu', 'builtins::zeros::wgpu')
        
        # Get with missing backend falls back to default
        result = self.registry.get('zeros', 'unknown')
        self.assertEqual(result, 'builtins::zeros::default')
    
    def test_get_backends(self):
        """Test getting available backends for a function."""
        self.registry.add('sin', 'host', 'path1')
        self.registry.add('sin', 'wgpu', 'path2')
        self.registry.add('sin', 'gpu', 'path3')
        
        backends = self.registry.get_backends('sin')
        self.assertEqual(backends, {'host', 'wgpu', 'gpu'})
    
    def test_load_json(self):
        """Test loading registry from JSON file."""
        registry_json = {
            'atan': {
                'host': 'builtins::math::trigonometry::atan::host_atan',
                'wgpu': 'builtins::math::trigonometry::atan::wgpu_matches_cpu',
                'default': 'builtins::math::trigonometry::atan::host_atan'
            },
            'zeros': {
                'host': 'builtins::array::creation::zeros::host_zeros',
                'wgpu': 'builtins::array::creation::zeros::wgpu_zeros'
            }
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            reg_file = Path(tmpdir) / 'registry.json'
            import json
            with open(reg_file, 'w') as f:
                json.dump(registry_json, f)
            
            self.registry.load_json(str(reg_file))
            
            # Verify loaded data
            result = self.registry.get('atan', 'wgpu')
            self.assertEqual(result, 'builtins::math::trigonometry::atan::wgpu_matches_cpu')


class TestSemanticResolver(unittest.TestCase):
    """Test semantic resolver with context hints."""
    
    def setUp(self):
        self.registry = BuiltinRegistry()
        self.registry.add('atan', 'host', 'builtins::math::atan::host')
        self.registry.add('atan', 'wgpu', 'builtins::math::atan::wgpu')
        self.registry.add('zeros', 'host', 'builtins::array::zeros::host')
        self.registry.add('zeros', 'wgpu', 'builtins::array::zeros::wgpu')
        
        self.resolver = SemanticResolver(self.registry)
    
    def test_extract_hints(self):
        """Test extracting @hint directives from pattern."""
        pattern = '''
        provider::<:[module]>::call(":[func]"
        @hint backend = detect_from_context()
        '''
        
        cleaned, hints = self.resolver.extract_hints(pattern)
        
        self.assertEqual(len(hints), 1)
        self.assertEqual(hints[0].name, 'backend')
        self.assertEqual(hints[0].operation, 'detect_from_context')
    
    def test_resolve_hints(self):
        """Test resolving hint directives."""
        code = '''
        #[wgpu_test]
        fn test() {
            result = provider::<atan>
        }
        '''
        
        pos_start = code.find('provider')
        pos_end = pos_start + 8
        
        hints = [
            type('H', (), {'name': 'backend', 'operation': 'detect_from_context', 'args': []})()
        ]
        
        resolved = self.resolver.resolve(code, pos_start, pos_end, {}, hints)
        
        # Should have resolved backend hint
        self.assertIn('backend', resolved)
    
    def test_template_renderer_with_lookup(self):
        """Test rendering template with registry lookup."""
        renderer = TemplateRenderer(self.resolver)
        
        captures = {'func': 'atan'}
        resolved_hints = {'backend': 'wgpu'}
        
        template = 'accel(":[func.lookup(backend)]")'
        result = renderer.render(template, captures, resolved_hints)
        
        # Should resolve to wgpu atan path
        self.assertIn('wgpu', result)


class TestPhase2Integration(unittest.TestCase):
    """Integration tests for Phase 2 features."""
    
    def test_end_to_end_context_aware_replacement(self):
        """Test complete Phase 2 workflow."""
        # Setup
        registry = BuiltinRegistry()
        registry.add('multiply', 'host', 'builtins::math::multiply::host')
        registry.add('multiply', 'wgpu', 'builtins::math::multiply::wgpu')
        
        resolver = SemanticResolver(registry)
        renderer = TemplateRenderer(resolver)
        
        # Source code with WGPU context
        code = '''
        #[wgpu_test]
        fn test_multiply() {
            let x = provider::<multiply>(a, b)
        }
        '''
        
        # Find match
        pos_start = code.find('provider')
        pos_end = pos_start + 8
        
        # Resolve hints
        hints = [
            type('H', (), {'name': 'backend', 'operation': 'detect_from_context', 'args': []})()
        ]
        resolved_hints = resolver.resolve(code, pos_start, pos_end, {}, hints)
        
        # Render template
        captures = {'func': 'multiply'}
        template = 'accel_call(":[func.lookup(backend)]")'
        result = renderer.render(template, captures, resolved_hints)
        
        # Should produce WGPU path
        self.assertIn('wgpu', result.lower())


if __name__ == '__main__':
    unittest.main()
