#!/usr/bin/env python3
"""
Tests for pycomby_cli.
"""

import unittest
import json
import sys
from io import StringIO
from pycomby_cli import parse_args, read_file_or_inline, format_ndjson, main
from pycomby import pycomby, pycomby_single


class TestParseArgs(unittest.TestCase):
    """Test argument parsing."""

    def test_pattern_only(self):
        """Pattern as required positional."""
        args = parse_args(['pattern_string'])
        self.assertEqual(args.pattern, 'pattern_string')
        self.assertIsNone(args.replacement)
        self.assertIsNone(args.input_file)

    def test_pattern_and_replacement(self):
        """Both pattern and replacement as positionals."""
        args = parse_args(['pattern', 'replacement'])
        self.assertEqual(args.pattern, 'pattern')
        self.assertEqual(args.replacement, 'replacement')

    def test_pattern_and_input_file(self):
        """Pattern and input file via flag."""
        args = parse_args(['-i', 'file.txt', 'pattern'])
        self.assertEqual(args.pattern, 'pattern')
        self.assertEqual(args.input_file, 'file.txt')

    def test_pattern_file_flag(self):
        """Pattern from file via -p."""
        args = parse_args(['-p', 'pattern.txt'])
        self.assertEqual(args.pattern_file, 'pattern.txt')
        self.assertIsNone(args.pattern)  # pattern positional not provided when using -p

    def test_replacement_file_flag(self):
        """Replacement from file via -r."""
        args = parse_args(['pattern', '-r', 'repl.txt'])
        self.assertEqual(args.pattern, 'pattern')
        self.assertEqual(args.replacement_file, 'repl.txt')

    def test_first_flag(self):
        """--first flag."""
        args = parse_args(['pattern', '--first'])
        self.assertTrue(args.first)

    def test_missing_pattern_error(self):
        """Error when pattern is missing."""
        with self.assertRaises(SystemExit):
            parse_args([])

    def test_all_flags(self):
        """All flags together."""
        args = parse_args([
            '-i', 'input.txt',
            '-p', 'pattern.txt',
            '-r', 'repl.txt',
            '--first'
        ])
        self.assertEqual(args.input_file, 'input.txt')
        self.assertEqual(args.pattern_file, 'pattern.txt')
        self.assertEqual(args.replacement_file, 'repl.txt')
        self.assertTrue(args.first)


class TestReadFileOrInline(unittest.TestCase):
    """Test file/inline reading."""

    def test_inline_text(self):
        """Use inline text when no file."""
        result = read_file_or_inline(None, 'inline_pattern')
        self.assertEqual(result, 'inline_pattern')

    def test_file_not_found(self):
        """Exit with code 2 on file not found."""
        with self.assertRaises(SystemExit) as cm:
            read_file_or_inline('nonexistent.txt', 'fallback')
        self.assertEqual(cm.exception.code, 2)

    def test_file_priority(self):
        """File takes priority over inline."""
        # Write a temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('file_content')
            fname = f.name
        
        try:
            result = read_file_or_inline(fname, 'inline')
            self.assertEqual(result, 'file_content')
        finally:
            import os
            os.unlink(fname)


class TestFormatNdjson(unittest.TestCase):
    """Test NDJSON formatting."""

    def test_single_match(self):
        """Single match formatted as one JSON line."""
        matches = [{'name': 'John', 'age': '30'}]
        result = format_ndjson(matches)
        self.assertEqual(result, '{"name":"John","age":"30"}')

    def test_multiple_matches(self):
        """Multiple matches formatted as multiple JSON lines."""
        matches = [
            {'name': 'John', 'age': '30'},
            {'name': 'Jane', 'age': '25'}
        ]
        result = format_ndjson(matches)
        lines = result.split('\n')
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0]), {'name': 'John', 'age': '30'})
        self.assertEqual(json.loads(lines[1]), {'name': 'Jane', 'age': '25'})

    def test_empty_matches(self):
        """No matches returns empty string."""
        result = format_ndjson([])
        self.assertEqual(result, '')


class TestMainCLI(unittest.TestCase):
    """Test main() function with mocked stdin/stdout."""

    def setUp(self):
        """Save original stdout/stdin."""
        self.original_stdout = sys.stdout
        self.original_stdin = sys.stdin

    def tearDown(self):
        """Restore stdout/stdin."""
        sys.stdout = self.original_stdout
        sys.stdin = self.original_stdin

    def test_query_single_match(self):
        """Query mode with single match."""
        sys.stdin = StringIO('Hello John, you are 30 years old.')
        sys.stdout = StringIO()
        
        try:
            main(['Hello :[name], you are :[age:digit]'])
        except SystemExit as e:
            self.assertEqual(e.code, 0)
        
        output = sys.stdout.getvalue()
        result = json.loads(output.strip())
        self.assertEqual(result['name'], 'John')
        self.assertEqual(result['age'], '30')

    def test_query_multiple_matches(self):
        """Query mode with multiple matches."""
        text = 'John is 30. Jane is 25.'
        sys.stdin = StringIO(text)
        sys.stdout = StringIO()
        
        try:
            main([':[name:word] is :[age:digit]'])
        except SystemExit as e:
            self.assertEqual(e.code, 0)
        
        output = sys.stdout.getvalue().strip()
        lines = output.split('\n')
        self.assertEqual(len(lines), 2)
        
        m1 = json.loads(lines[0])
        m2 = json.loads(lines[1])
        self.assertEqual(m1['name'], 'John')
        self.assertEqual(m2['name'], 'Jane')

    def test_query_no_matches(self):
        """Query mode with no matches."""
        sys.stdin = StringIO('No match here')
        sys.stdout = StringIO()
        
        try:
            main([':[name] is :[age:digit]'])
        except SystemExit as e:
            self.assertEqual(e.code, 1)

    def test_replace_single_match(self):
        """Replace mode with --first flag."""
        sys.stdin = StringIO('John is 30. Jane is 25.')
        sys.stdout = StringIO()
        
        try:
            main([':[name] is :[age:digit]', 'NAME: :[name.upper]', '--first'])
        except SystemExit as e:
            self.assertEqual(e.code, 0)
        
        output = sys.stdout.getvalue()
        self.assertEqual(output, 'NAME: JOHN. Jane is 25.')

    def test_replace_all_matches(self):
        """Replace mode with all matches (default)."""
        sys.stdin = StringIO('John is 30. Jane is 25.')
        sys.stdout = StringIO()
        
        try:
            main([':[name:word] is :[age:digit]', 'NAME: :[name.upper]'])
        except SystemExit as e:
            self.assertEqual(e.code, 0)
        
        output = sys.stdout.getvalue()
        self.assertEqual(output, 'NAME: JOHN. NAME: JANE.')

    def test_replace_no_matches(self):
        """Replace mode with no matches."""
        sys.stdin = StringIO('No match here')
        sys.stdout = StringIO()
        
        try:
            main([':[name] is :[age:digit]', 'replacement'])
        except SystemExit as e:
            self.assertEqual(e.code, 1)

    def test_first_query_mode(self):
        """Query mode with --first returns single match."""
        sys.stdin = StringIO('John is 30. Jane is 25.')
        sys.stdout = StringIO()
        
        try:
            main([':[name:word] is :[age:digit]', '--first'])
        except SystemExit as e:
            self.assertEqual(e.code, 0)
        
        output = sys.stdout.getvalue().strip()
        # Single match, not multiple, so it's one JSON object
        result = json.loads(output)
        self.assertEqual(result['name'], 'John')


if __name__ == '__main__':
    unittest.main()
