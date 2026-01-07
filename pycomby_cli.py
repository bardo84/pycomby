#!/usr/bin/env python3
"""
CLI wrapper for pycomby.
"""

import sys
import json
import argparse
from typing import Optional, Tuple, Dict
from pathlib import Path
from pycomby import pycomby, pycomby_single

# Phase 2 imports (optional)
try:
    from semantic_resolver import SemanticResolver
    from builtin_registry import BuiltinRegistry
    PHASE_2_AVAILABLE = True
except ImportError:
    PHASE_2_AVAILABLE = False


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
    parser.add_argument('--registry', dest='registry_file',
                        help='Read registry (JSON) for lookup operations')
    parser.add_argument('--on-unresolved', dest='on_unresolved', choices=['placeholder', 'skip', 'fail'],
                        default='placeholder',
                        help='Behavior when lookup fails: placeholder (default), skip, or fail')
    parser.add_argument('--first', action='store_true',
                        help='Match only first occurrence (default: all)')
    
    # Phase 2 arguments
    if PHASE_2_AVAILABLE:
        parser.add_argument('--builtin-registry', dest='builtin_registry_file',
                            help='Phase 2: Load builtin registry from JSON file')
        parser.add_argument('--detect-context', action='store_true',
                            help='Phase 2: Enable context-aware backend detection')
    
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


def load_registry(registry_file: Optional[str]) -> Dict[str, str]:
    """Load Phase 1 registry from JSON file."""
    if not registry_file:
        return {}
    try:
        with open(registry_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                sys.stderr.write(f"Error: Registry must be a JSON object (dict), got {type(data).__name__}\n")
                sys.exit(2)
            return data
    except FileNotFoundError:
        sys.stderr.write(f"Error: Registry file not found: {registry_file}\n")
        sys.exit(2)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Error: Invalid JSON in registry file: {e}\n")
        sys.exit(2)
    except Exception as e:
        sys.stderr.write(f"Error reading registry: {e}\n")
        sys.exit(2)


def load_builtin_registry(registry_file: Optional[str]) -> Optional['BuiltinRegistry']:
    """Load Phase 2 builtin registry from JSON file."""
    if not PHASE_2_AVAILABLE or not registry_file:
        return None
    try:
        registry = BuiltinRegistry()
        registry.load_json(registry_file)
        return registry
    except FileNotFoundError:
        sys.stderr.write(f"Error: Builtin registry file not found: {registry_file}\n")
        sys.exit(2)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Error: Invalid JSON in builtin registry file: {e}\n")
        sys.exit(2)
    except ValueError as e:
        sys.stderr.write(f"Error: Invalid builtin registry format: {e}\n")
        sys.exit(2)
    except Exception as e:
        sys.stderr.write(f"Error reading builtin registry: {e}\n")
        sys.exit(2)


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
    registry = load_registry(parsed.registry_file)
    
    # Phase 2: Load builtin registry and create semantic resolver
    builtin_registry = None
    semantic_resolver = None
    
    if PHASE_2_AVAILABLE:
        builtin_registry = load_builtin_registry(
            getattr(parsed, 'builtin_registry_file', None)
        )
        
        if builtin_registry or getattr(parsed, 'detect_context', False):
            semantic_resolver = SemanticResolver(builtin_registry)
    
    if not pattern:
        sys.stderr.write("Error: Pattern is empty\n")
        sys.exit(2)
    
    try:
        # Choose function based on --first flag
        match_func = pycomby_single if parsed.first else pycomby
        
        if replacement:
            # Replacement mode: output modified text
            result = match_func(
                input_text,
                pattern,
                replacement,
                registry=registry,
                builtin_registry=builtin_registry,
                semantic_resolver=semantic_resolver
            )
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
