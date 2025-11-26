#!/usr/bin/env python3
"""
Verification script for bug fixes.
"""

from pycomby import pycomby, pycomby_single

print("=" * 60)
print("PYCOMBY BUG FIX VERIFICATION")
print("=" * 60)
print()

# Test 1: Empty pattern infinite loop fix
print("Test 1: Empty Pattern (was infinite loop)")
print("-" * 40)
try:
    result = pycomby("hello world", "")
    print("[PASS] pycomby('hello world', '') = {}".format(result))
except Exception as e:
    print("[FAIL] {}: {}".format(type(e).__name__, e))
print()

# Test 2: Invalid regex error handling
print("Test 2: Invalid Regex Pattern (error handling)")
print("-" * 40)
try:
    result = pycomby("test", ":[x~[invalid]")
    print("[FAIL] Should have raised ValueError")
except ValueError as e:
    if "Invalid regex pattern" in str(e):
        print("[PASS] Caught with proper error message")
        print("  Message: {}".format(e))
    else:
        print("[FAIL] Wrong error message: {}".format(e))
except Exception as e:
    print("[FAIL] Wrong exception type: {}: {}".format(type(e).__name__, e))
print()

# Test 3: Normal operation still works
print("Test 3: Normal Operation (regression check)")
print("-" * 40)
try:
    text = "Hello, John! You are 30 years old."
    pattern = "Hello, :[name:word]! You are :[age:digit] years old."
    result = pycomby_single(text, pattern)
    expected = {'name': 'John', 'age': '30'}
    if result == expected:
        print("[PASS] Pattern matching works")
        print("  Result: {}".format(result))
    else:
        print("[FAIL] Got {}, expected {}".format(result, expected))
except Exception as e:
    print("[FAIL] {}: {}".format(type(e).__name__, e))
print()

# Test 4: Edge case - optional holes
print("Test 4: Optional Holes (edge case)")
print("-" * 40)
try:
    text = "value is -1.5"
    pattern = "value is :[num:num]:[ext:word?]"
    result = pycomby_single(text, pattern)
    if result.get('ext') is None:
        print("[PASS] Optional hole correctly None")
        print("  Result: {}".format(result))
    else:
        print("[FAIL] Optional should be None, got {}".format(result))
except Exception as e:
    print("[FAIL] {}: {}".format(type(e).__name__, e))
print()

print("=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
