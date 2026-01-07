#!/usr/bin/env python3
"""
Phase 2 CLI integration tests.

Tests the command-line interface with Phase 2 features:
- --builtin-registry argument
- --detect-context flag
- @hint directives in patterns
- Context-aware replacements
"""

import unittest
import tempfile
import json
from pathlib import Path
from io import StringIO
import sys

from pycomby_cli import main, parse_args, load_builtin_registry
from builtin_registry import BuiltinRegistry


class TestPhase2CLIArguments(unittest.TestCase):
    """Test Phase 2 CLI argument parsing."""
    
    def test_parse_builtin_registry_argument(self):
        """Test parsing --builtin-registry argument."""
        args = [
            'pattern',
            'replacement',
            '--builtin-registry', 'registry.json'
        ]
        parsed = parse_args(args)
        self.assertEqual(parsed.builtin_registry_file, 'registry.json')
    
    def test_parse_detect_context_flag(self):
        """Test parsing --detect-context flag."""
        args = [
            'pattern',
            '--detect-context'
        ]
        parsed = parse_args(args)
        self.assertTrue(parsed.detect_context)
    
    def test_parse_combined_phase1_and_phase2(self):
        """Test parsing both Phase 1 and Phase 2 arguments together."""
        args = [
            'pattern',
            'replacement',
            '--registry', 'phase1.json',
            '--builtin-registry', 'phase2.json',
            '--detect-context'
        ]
        parsed = parse_args(args)
        self.assertEqual(parsed.registry_file, 'phase1.json')
        self.assertEqual(parsed.builtin_registry_file, 'phase2.json')
        self.assertTrue(parsed.detect_context)


class TestLoadBuiltinRegistry(unittest.TestCase):
    """Test loading builtin registry from file."""
    
    def test_load_valid_builtin_registry(self):
        """Test loading a valid builtin registry JSON file."""
        registry_data = {
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
        
        with tempfile.TemporaryDirectory() as tmpdir:
            reg_file = Path(tmpdir) / 'registry.json'
            with open(reg_file, 'w') as f:
                json.dump(registry_data, f)
            
            registry = load_builtin_registry(str(reg_file))
            
            self.assertIsNotNone(registry)
            self.assertEqual(
                registry.get('atan', 'host'),
                'builtins::math::atan::host'
            )
            self.assertEqual(
                registry.get('zeros', 'wgpu'),
                'builtins::array::zeros::wgpu'
            )
    
    def test_load_missing_registry_file(self):
        """Test error handling for missing registry file."""
        with self.assertRaises(SystemExit) as cm:
            load_builtin_registry('/nonexistent/registry.json')
        self.assertEqual(cm.exception.code, 2)
    
    def test_load_invalid_json(self):
        """Test error handling for invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reg_file = Path(tmpdir) / 'bad.json'
            with open(reg_file, 'w') as f:
                f.write("not valid json {")
            
            with self.assertRaises(SystemExit) as cm:
                load_builtin_registry(str(reg_file))
            self.assertEqual(cm.exception.code, 2)
    
    def test_load_invalid_registry_format(self):
        """Test error handling for wrong registry format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reg_file = Path(tmpdir) / 'bad_format.json'
            with open(reg_file, 'w') as f:
                json.dump(['not', 'a', 'dict'], f)
            
            with self.assertRaises(SystemExit) as cm:
                load_builtin_registry(str(reg_file))
            self.assertEqual(cm.exception.code, 2)


class TestPhase2CLIIntegration(unittest.TestCase):
    """Integration tests for Phase 2 CLI features."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry_data = {
            'atan': {
                'host': 'builtins::math::trigonometry::atan::host_atan',
                'wgpu': 'builtins::math::trigonometry::atan::wgpu_matches_cpu',
                'default': 'builtins::math::trigonometry::atan::host_atan'
            },
            'sin': {
                'host': 'builtins::math::trigonometry::sin::host_sin',
                'wgpu': 'builtins::math::trigonometry::sin::wgpu_matches_cpu',
                'default': 'builtins::math::trigonometry::sin::host_sin'
            }
        }
        self.tmpdir = tempfile.TemporaryDirectory()
        self.reg_file = Path(self.tmpdir.name) / 'phase2.json'
        with open(self.reg_file, 'w') as f:
            json.dump(self.registry_data, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.tmpdir.cleanup()
    
    def test_replacement_with_builtin_registry(self):
        """Test replacement using builtin registry."""
        input_text = 'call(atan)'
        pattern = 'call(:[func])'
        replacement = 'backend_call(":[func.lookup(host)]")'
        
        # Create temp input file
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / 'input.txt'
            with open(input_file, 'w') as f:
                f.write(input_text)
            
            # Capture stdout
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            
            try:
                main([
                    pattern,
                    replacement,
                    '-i', str(input_file),
                    '--builtin-registry', str(self.reg_file)
                ])
            except SystemExit as e:
                exit_code = e.code
            finally:
                output = sys.stdout.getvalue()
                error = sys.stderr.getvalue()
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            # Should have made replacement
            self.assertIn('host_atan', output)
            self.assertEqual(exit_code, 0)
    
    def test_query_mode_outputs_ndjson(self):
        """Test that query mode outputs NDJSON."""
        input_text = 'call(atan) and call(sin)'
        pattern = 'call(:[func])'
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / 'input.txt'
            with open(input_file, 'w') as f:
                f.write(input_text)
            
            # Capture stdout
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            
            try:
                main([
                    pattern,
                    '-i', str(input_file)
                ])
            except SystemExit as e:
                exit_code = e.code
            finally:
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            # Should output NDJSON with matches (filter empty lines)
            lines = [l for l in output.strip().split('\n') if l]
            self.assertEqual(len(lines), 2)
            
            # Parse first line
            match1 = json.loads(lines[0])
            self.assertEqual(match1['func'], 'atan')
            
            # Parse second line
            match2 = json.loads(lines[1])
            self.assertEqual(match2['func'], 'sin')
    
    def test_first_flag_with_builtin_registry(self):
        """Test --first flag with Phase 2 builtin registry."""
        input_text = 'call(atan) and call(sin)'
        pattern = 'call(:[func])'
        replacement = 'result(":[func.lookup(wgpu)]")'
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / 'input.txt'
            with open(input_file, 'w') as f:
                f.write(input_text)
            
            # Capture stdout
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            
            try:
                main([
                    pattern,
                    replacement,
                    '-i', str(input_file),
                    '--builtin-registry', str(self.reg_file),
                    '--first'
                ])
            except SystemExit as e:
                exit_code = e.code
            finally:
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            # Should only replace first occurrence
            self.assertIn('wgpu_matches_cpu', output)
            # Second function should be unchanged
            self.assertIn('call(sin)', output)
            self.assertEqual(exit_code, 0)
    
    def test_detect_context_flag(self):
        """Test --detect-context flag enables resolver."""
        input_text = '''
        #[wgpu_test]
        fn test() {
            call(atan)
        }
        '''
        pattern = 'call(:[func])'
        replacement = 'backend_call(":[func]")'
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / 'input.txt'
            with open(input_file, 'w') as f:
                f.write(input_text)
            
            # Capture stdout
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            
            try:
                main([
                    pattern,
                    replacement,
                    '-i', str(input_file),
                    '--detect-context'
                ])
            except SystemExit as e:
                exit_code = e.code
            finally:
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            # Should perform replacement
            self.assertIn('backend_call', output)
            self.assertEqual(exit_code, 0)
    
    def test_no_match_exit_code(self):
        """Test exit code 1 when no matches found."""
        input_text = 'foo bar baz'
        pattern = 'nonexistent'
        replacement = 'replaced'
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / 'input.txt'
            with open(input_file, 'w') as f:
                f.write(input_text)
            
            # Capture stdout
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            
            try:
                main([
                    pattern,
                    replacement,
                    '-i', str(input_file)
                ])
            except SystemExit as e:
                exit_code = e.code
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            # Should exit with code 1 (no matches, no changes)
            self.assertEqual(exit_code, 1)
    
    def test_match_found_exit_code(self):
        """Test exit code 0 when match found and replaced."""
        input_text = 'hello world'
        pattern = 'world'
        replacement = 'there'
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / 'input.txt'
            with open(input_file, 'w') as f:
                f.write(input_text)
            
            # Capture stdout
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            
            try:
                main([
                    pattern,
                    replacement,
                    '-i', str(input_file)
                ])
            except SystemExit as e:
                exit_code = e.code
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            # Should exit with code 0 (match found and changed)
            self.assertEqual(exit_code, 0)


class TestPhase2CLIErrorHandling(unittest.TestCase):
    """Test error handling for Phase 2 CLI."""
    
    def test_empty_pattern_error(self):
        """Test error when pattern is empty."""
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        
        try:
            with self.assertRaises(SystemExit) as cm:
                main([])
        finally:
            sys.stderr = old_stderr
        
        self.assertEqual(cm.exception.code, 2)
    
    def test_missing_input_file_error(self):
        """Test error when input file doesn't exist."""
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        
        try:
            with self.assertRaises(SystemExit) as cm:
                main([
                    'pattern',
                    '-i', '/nonexistent/file.txt'
                ])
        finally:
            sys.stderr = old_stderr
        
        self.assertEqual(cm.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
