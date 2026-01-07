import unittest
from pycomby import pycomby, pycomby_single

class TestPycomby(unittest.TestCase):

    def test_basic_pattern_matching(self):
        str_in = 'Hello, world! My name is John and I am 30 years old.'
        pattern = 'Hello, :[greeting:word]! My name is :[name] and I am :[age:digit] years old.'
        replacement = 'Greetings, :[name]! Your greeting was ":[greeting]" and you are :[age] years old.'
        
        groups = pycomby_single(str_in, pattern)
        self.assertEqual(groups, {'greeting': 'world', 'name': 'John', 'age': '30'})

        outstr = pycomby_single(str_in, pattern, replacement)
        self.assertEqual(outstr, 'Greetings, John! Your greeting was "world" and you are 30 years old.')

    def test_optional_group_no_extension(self):
        str_in = '-1.4e-3'
        pattern = ':[x:num]:[ext:word?]'
        groups = pycomby_single(str_in, pattern)
        self.assertEqual(groups, {'x': '-1.4e-3', 'ext': None})

    def test_optional_group_with_extension(self):
        str_in = '-1.4k'
        pattern = ':[x:num]:[ext:word?]'
        groups = pycomby_single(str_in, pattern)
        self.assertEqual(groups, {'x': '-1.4', 'ext': 'k'})

    def test_operations_string_arithmetic(self):
        str_in = 'file is /path/to/some_file.txt and number is 99'
        pattern = 'file is :[filepath] and number is :[num:digit]'
        replacement = 'File is :[filepath.filename], number is now :[num.inc]'
        outstr = pycomby_single(str_in, pattern, replacement)
        self.assertEqual(outstr, 'File is some_file.txt, number is now 100')

    def test_operations_file_path(self):
        str_in = 'file is /path/to/some_file.txt and number is 99'
        pattern = 'file is :[filepath] and number is :[num:digit]'
        replacement = 'Basename: :[filepath.basename], Extension: :[filepath.extension]'
        outstr = pycomby_single(str_in, pattern, replacement)
        self.assertEqual(outstr, 'Basename: some_file, Extension: txt')

    def test_operations_chaining(self):
        str_in = 'file is /path/to/some_file.txt and number is 99'
        pattern = 'file is :[filepath] and number is :[num:digit]'
        replacement = 'Chained ops: :[filepath.basename.upper]'
        outstr = pycomby_single(str_in, pattern, replacement)
        self.assertEqual(outstr, 'Chained ops: SOME_FILE')

    def test_balanced_parentheses(self):
        str_in = 'y = ((a + b)*(c + d)) + 1'
        pattern = ':[term1:()]:[rest~.*]'
        groups = pycomby_single(str_in, pattern)
        self.assertEqual(groups, {'term1': '((a + b)*(c + d))', 'rest': ' + 1'})

    def test_lookup_operation_found(self):
        """Test lookup operation with key found in registry."""
        str_in = 'provider::<atan>'
        pattern = 'provider::<:[func]>'
        replacement = 'maybe_provider(":[func.lookup]")'
        registry = {
            'builtin:atan': 'builtins::math::trigonometry::atan::wgpu_matches_cpu'
        }
        outstr = pycomby_single(str_in, pattern, replacement, registry=registry)
        self.assertEqual(outstr, 'maybe_provider("builtins::math::trigonometry::atan::wgpu_matches_cpu")')

    def test_lookup_operation_not_found(self):
        """Test lookup operation with key not found in registry (fallback)."""
        str_in = 'provider::<unknown_func>'
        pattern = 'provider::<:[func]>'
        replacement = 'maybe_provider(":[func.lookup]")'
        registry = {}
        outstr = pycomby_single(str_in, pattern, replacement, registry=registry)
        self.assertEqual(outstr, 'maybe_provider("TODO_CONTEXT_unknown_func")')

    def test_lookup_with_other_operations(self):
        """Test chaining lookup with other operations."""
        str_in = 'provider::<zeros>'
        pattern = 'provider::<:[func]>'
        replacement = ':[func.lookup.upper]'
        registry = {
            'builtin:zeros': 'builtins::array::creation::zeros::host_zeros'
        }
        outstr = pycomby_single(str_in, pattern, replacement, registry=registry)
        self.assertEqual(outstr, 'BUILTINS::ARRAY::CREATION::ZEROS::HOST_ZEROS')

    def test_lookup_multiple_replacements(self):
        """Test lookup operation on multiple matches."""
        str_in = 'call(atan) and call(sin)'
        pattern = 'call(:[func])'
        replacement = 'lookup(":[func.lookup]")'
        registry = {
            'builtin:atan': 'builtins::math::trigonometry::atan::wgpu',
            'builtin:sin': 'builtins::math::trigonometry::sin::wgpu'
        }
        outstr = pycomby(str_in, pattern, replacement, registry=registry)
        self.assertEqual(outstr, 'lookup("builtins::math::trigonometry::atan::wgpu") and lookup("builtins::math::trigonometry::sin::wgpu")')

if __name__ == '__main__':
    unittest.main()
