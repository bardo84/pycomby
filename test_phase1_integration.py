#!/usr/bin/env python3
"""
Integration test for Phase 1: Lightweight Lookup.
Demonstrates the complete workflow from pattern definition to registry usage.
"""

import json
import tempfile
from pathlib import Path
from pycomby import pycomby
from pycomby_cli import main as cli_main


def test_phase1_runmat_example():
    """
    Real-world example: RunMat provider migration.
    
    Before:
        runmat_accelerate_api::provider::<builtins::math>::call_hook("atan", ...)
    
    After:
        runtime::accel_provider::call_provider("builtins::math::trigonometry::atan::wgpu", ...)
    """
    # Input
    input_text = '''
runmat_accelerate_api::provider::<builtins::math>::call_hook("atan", ...)
runmat_accelerate_api::provider::<builtins::math>::call_hook("sin", ...)
runmat_accelerate_api::provider::<builtins::array>::call_hook("zeros", ...)
'''.strip()
    
    # Pattern
    pattern = 'provider::<:[module]>::call_hook(":[func]",'
    
    # Replacement
    replacement = 'runtime::accel_provider::call_provider(":[func.lookup]",'
    
    # Registry
    registry = {
        "builtin:atan": "builtins::math::trigonometry::atan::wgpu_matches_cpu",
        "builtin:sin": "builtins::math::trigonometry::sin::wgpu_matches_cpu",
        "builtin:zeros": "builtins::array::creation::zeros::host_zeros"
    }
    
    # Apply
    result = pycomby(input_text, pattern, replacement, registry=registry)
    
    # Verify
    assert 'builtins::math::trigonometry::atan::wgpu_matches_cpu' in result
    assert 'builtins::math::trigonometry::sin::wgpu_matches_cpu' in result
    assert 'builtins::array::creation::zeros::host_zeros' in result
    print("[OK] RunMat example test passed")


def test_phase1_cli_integration():
    """
    Test CLI end-to-end with temporary files.
    """
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create input file
        input_file = tmpdir / "input.txt"
        input_file.write_text("""
provider::<atan>
provider::<sin>
provider::<unknown>
""".strip())
        
        # Create registry file
        registry_file = tmpdir / "registry.json"
        registry_file.write_text(json.dumps({
            "builtin:atan": "builtins::math::trigonometry::atan::wgpu",
            "builtin:sin": "builtins::math::trigonometry::sin::wgpu"
        }))
        
        # Expected output file
        output_file = tmpdir / "output.txt"
        
        # Run CLI
        try:
            # Capture output via temp redirect
            import sys
            from io import StringIO
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            
            cli_main([
                '-i', str(input_file),
                'provider::<:[func]>',
                'resolved(":[func.lookup]")',
                '--registry', str(registry_file)
            ])
            
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout
            
            # Verify
            assert 'builtins::math::trigonometry::atan::wgpu' in output
            assert 'builtins::math::trigonometry::sin::wgpu' in output
            assert 'TODO_CONTEXT_unknown' in output
            print("[OK] CLI integration test passed")
        
        except SystemExit as e:
            sys.stdout = old_stdout
            if e.code == 0:
                print("[OK] CLI integration test passed (exit code 0)")
            else:
                raise


def test_phase1_fallback_behavior():
    """
    Test that missing registry keys fall back to TODO_CONTEXT placeholder.
    """
    input_text = "provider::<missing_func>"
    pattern = "provider::<:[func]>"
    replacement = 'accel(":[func.lookup]")'
    
    result = pycomby(input_text, pattern, replacement, registry={})
    
    # Should have fallback placeholder
    assert "TODO_CONTEXT_missing_func" in result
    assert result == 'accel("TODO_CONTEXT_missing_func")'
    print("[OK] Fallback behavior test passed")


def test_phase1_operation_chaining():
    """
    Test that lookup can be chained with other operations.
    """
    input_text = "call(zeros)"
    pattern = "call(:[func])"
    replacement = "accel_call(:[func.lookup.upper])"
    registry = {
        "builtin:zeros": "builtins::array::zeros::host_zeros"
    }
    
    result = pycomby(input_text, pattern, replacement, registry=registry)
    
    # Lookup should be applied first, then upper
    assert result == "accel_call(BUILTINS::ARRAY::ZEROS::HOST_ZEROS)"
    print("[OK] Operation chaining test passed")


if __name__ == '__main__':
    print("Phase 1 Integration Tests\n" + "=" * 40)
    test_phase1_runmat_example()
    test_phase1_fallback_behavior()
    test_phase1_operation_chaining()
    test_phase1_cli_integration()
    print("\n" + "=" * 40)
    print("All tests passed [OK]")
