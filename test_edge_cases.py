#!/usr/bin/env python3
"""
Edge case testing for pycomby.
"""

from pycomby import pycomby, pycomby_single

def test_empty_pattern():
    """Test with empty pattern."""
    try:
        result = pycomby('hello', '')
        print('[OK] Test 1 (empty pattern):', result)
    except Exception as e:
        print('[ERROR] Test 1:', type(e).__name__, '-', e)

def test_malformed_hole():
    """Test malformed hole (unclosed bracket)."""
    try:
        result = pycomby('hello', ':[name')
        print('[OK] Test 2 (malformed hole):', result)
    except Exception as e:
        print('[ERROR] Test 2:', type(e).__name__, '-', e)

def test_unknown_macro():
    """Test unknown macro."""
    try:
        result = pycomby('hello', ':[name:unknown_macro]')
        print('[OK] Test 3 (unknown macro):', result)
    except Exception as e:
        print('[ERROR] Test 3:', type(e).__name__, '-', e)

def test_invalid_operation():
    """Test invalid operation in replacement."""
    try:
        result = pycomby_single('hello 123', ':[x] :[num:digit]', ':[num.invalid_op]')
        print('[OK] Test 4 (invalid op):', result)
    except Exception as e:
        print('[ERROR] Test 4:', type(e).__name__, '-', e)

def test_nested_parens():
    """Test deeply nested balanced parens."""
    text = 'result = (((a + b) * (c + (d + e))))'
    pattern = ':[var] = :[expr:()]'
    result = pycomby_single(text, pattern)
    print('[OK] Test 5 (nested parens):', result)

def test_mixed_delimiters():
    """Test mixed delimiters in balanced match."""
    text = 'func([1, 2, {3, 4}])'
    pattern = ':[func] :[args:()]'
    result = pycomby_single(text, pattern)
    print('[OK] Test 6 (mixed delimiters):', result)

def test_unbalanced():
    """Test unbalanced delimiters."""
    text = 'result = ((a + b'
    pattern = ':[var] = :[expr:()]'
    result = pycomby_single(text, pattern)
    print('[OK] Test 7 (unbalanced):', result)

def test_comment_in_parens():
    """Test comment in balanced region."""
    text = 'x = (a + b // comment\n + c)'
    pattern = ':[var] = :[expr:()]'
    result = pycomby_single(text, pattern)
    print('[OK] Test 8 (comment in parens):', result)

def test_string_with_delimiters():
    """Test string with delimiters."""
    text = 'x = (a + "()" + b)'
    pattern = ':[var] = :[expr:()]'
    result = pycomby_single(text, pattern)
    print('[OK] Test 9 (string with delimiter):', result)

def test_empty_wildcard_match():
    """Test anonymous wildcard (not captured)."""
    text = 'hello world'
    pattern = ':[_] world'
    result = pycomby_single(text, pattern)
    # Anonymous hole not captured, but pattern still matches
    expected = {}
    print('[OK] Test 10 (wildcard match):', result, '== expected:', result == expected)

def test_multiple_same_name():
    """Test multiple captures with same name (last one wins)."""
    text = 'a and b and c'
    pattern = ':[x] and :[x] and :[x]'
    result = pycomby_single(text, pattern)
    print('[OK] Test 11 (same name captures):', result)

def test_regex_constraint():
    """Test regex-constrained hole."""
    try:
        text = 'value is 42xyz'
        pattern = ':[prefix] is :[num~\\d+]:[rest~.*]'
        result = pycomby_single(text, pattern)
        print('[OK] Test 12 (regex constraint):', result)
    except Exception as e:
        print('[ERROR] Test 12:', type(e).__name__, '-', e)

def test_optional_middle():
    """Test optional hole in middle of pattern."""
    text = 'start end'
    pattern = 'start :[middle?] end'
    result = pycomby_single(text, pattern)
    print('[OK] Test 13 (optional middle):', result)

def test_escaped_bracket_in_literal():
    """Test literal bracket characters."""
    text = 'match [x]'
    pattern = 'match [x]'
    result = pycomby_single(text, pattern)
    # No holes, just literal match - should match but no captures
    expected = {}
    print('[OK] Test 14 (bracket literal):', result, '== expected:', result == expected)

if __name__ == '__main__':
    test_empty_pattern()
    print()
    test_malformed_hole()
    print()
    test_unknown_macro()
    print()
    test_invalid_operation()
    print()
    test_nested_parens()
    print()
    test_mixed_delimiters()
    print()
    test_unbalanced()
    print()
    test_comment_in_parens()
    print()
    test_string_with_delimiters()
    print()
    test_empty_wildcard_match()
    print()
    test_multiple_same_name()
    print()
    test_regex_constraint()
    print()
    test_optional_middle()
    print()
    test_escaped_bracket_in_literal()
