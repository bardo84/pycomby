#!/usr/bin/env python3
"""
CLI wrapper for pycomby.
"""

import sys
import json
import argparse
from typing import Optional, Tuple
from pycomby import pycomby, pycomby_single


def parse_args(args=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog='pycomby',
        description='Comby-like structural search and replace engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pycomby ':[name] is :[age:digit]'                    # stdin, query
  pycomby ':[name]' ':[name.upper]'                    # stdin, replace
  cat file.txt | pycomby 'pattern' 'replacement'       # stdin via pipe
  pycomby -i file.txt 'pattern'                        # file, query
  pycomby -i file.txt -p pattern.txt 'replacement'     # pattern from file
  pycomby -i file.txt 'pattern' -r replacement.txt     # replacement from file
        """.strip()
    )
    
    parser.add_argument('pattern', nargs='?',
                        help='Pattern string (or use -p for file)')
    parser.add_argument('replacement', nargs='?',
                        help='Replacement string (optional, or use -r for file)')
    
    parser.add_argument('-i', '--input', dest='input_file',
                        help='Input file (default: stdin)')
    parser.add_argument('-p', '--pattern-file', dest='pattern_file',
                        help='Read pattern from file')
    parser.add_argument('-r', '--replacement-file', dest='replacement_file',
                        help='Read replacement from file')
    parser.add_argument('--first', action='store_true',
                        help='Match only first occurrence (default: all)')
    
    parsed = parser.parse_args(args)
    
    # Validate that pattern is provided
    if not parsed.pattern and not parsed.pattern_file:
        parser.error('PATTERN is required (provide as argument or via -p)')
    
    return parsed


def read_input(input_file: Optional[str]) -> str:
    """Read input from file or stdin."""
    if not input_file or input_file == '-':
        return sys.stdin.read()
    else:
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            sys.stderr.write(f"Error: File not found: {input_file}\n")
            sys.exit(2)
        except Exception as e:
            sys.stderr.write(f"Error reading file: {e}\n")
            sys.exit(2)


def read_file_or_inline(file_path: Optional[str], inline_text: Optional[str]) -> Optional[str]:
    """Read from file if provided, otherwise use inline text."""
    if file_path:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            sys.stderr.write(f"Error: File not found: {file_path}\n")
            sys.exit(2)
        except Exception as e:
            sys.stderr.write(f"Error reading file: {e}\n")
            sys.exit(2)
    return inline_text


def format_ndjson(matches: list) -> str:
    """Format matches as newline-delimited JSON."""
    lines = []
    for match in matches:
        lines.append(json.dumps(match, separators=(',', ':')))
    return '\n'.join(lines) if lines else ''


def main(args=None):
    """Main CLI entry point."""
    parsed = parse_args(args)
    
    # Read inputs
    input_text = read_input(parsed.input_file)
    pattern = read_file_or_inline(parsed.pattern_file, parsed.pattern)
    replacement = read_file_or_inline(parsed.replacement_file, parsed.replacement)
    
    if not pattern:
        sys.stderr.write("Error: Pattern is empty\n")
        sys.exit(2)
    
    try:
        # Choose function based on --first flag
        match_func = pycomby_single if parsed.first else pycomby
        
        if replacement:
            # Replacement mode: output modified text
            result = match_func(input_text, pattern, replacement)
            if isinstance(result, str):
                sys.stdout.write(result)
                # Exit code: 0 if there were replacements (result differs)
                exit_code = 0 if result != input_text else 1
            else:
                # Single mode returned a dict (no matches)
                exit_code = 1
        else:
            # Query mode: output matches as NDJSON
            result = match_func(input_text, pattern)
            
            if parsed.first:
                # pycomby_single returns a dict
                if result:
                    sys.stdout.write(json.dumps(result, separators=(',', ':')) + '\n')
                    exit_code = 0
                else:
                    exit_code = 1
            else:
                # pycomby returns a list
                if result:
                    output = format_ndjson(result)
                    sys.stdout.write(output + '\n')
                    exit_code = 0
                else:
                    exit_code = 1
        
        sys.exit(exit_code)
    
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(2)


if __name__ == '__main__':
    main()
