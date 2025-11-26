# pycomby

**Comby-like structural search and rewrite for code**

A Python implementation of [Comby](https://comby.dev) patterns for structural code matching and transformation. Write once, match and replace patterns across different code contexts without regex complexity.

## Quick Start

```python
from pycomby import pycomby

# Extract matches
matches = pycomby("Hello, world!", "Hello, :[greeting:word]!")
# [{'greeting': 'world'}]

# Rewrite code
code = "foo(bar(1, 2))"
result = pycomby(code, ":[func:()]", "[CALL :[func]]")
# "[CALL foo(bar(1, 2))]"
```

## Command Line

```bash
# Extract
echo "John is 30. Jane is 25." | pycomby ':[name:word] is :[age:digit]'
{"name":"John","age":"30"}
{"name":"Jane","age":"25"}

# Replace
echo "John is 30" | pycomby ':[name:word] is :[age:digit]' 'Person: :[name.upper]'
Person: JOHN
```

## Key Features

- **Balanced delimiters** – Match `()`, `[]`, `{}` with proper nesting (no regex hacks)
- **Macros** – `:[x:word]`, `:[x:digit]`, `:[x:num]` for common patterns
- **Structural macros** – `:[x:()]` for balanced parentheses, `:[x:(_)]` for content only
- **Optional holes** – `:[x?]` or `:[x:word?]` for optional matching
- **Regex constraints** – `:[x~\d{3}]` for custom patterns
- **Transformations** – Chain operations: `:[path.basename.upper]`
- **Comment/string aware** – Ignores delimiters inside strings and comments

## Installation

```bash
git clone https://github.com/bardo84/pycomby.git
cd pycomby
pip install -e .
```

Then use:
```bash
pycomby [OPTIONS] PATTERN [REPLACEMENT] < input.txt
```

## Pattern Syntax

See [SYNTAX.md](SYNTAX.md) for complete documentation.

### Basic Examples

| Pattern | Matches |
|---------|---------|
| `:[name]` | Any text, captured as `name` |
| `:[_]` | Any text, not captured |
| `...` | Any text (shorthand for `:[_]`) |
| `:[x:word]` | Word characters (`\w+`) |
| `:[x:digit]` | Digits (`\d+`) |
| `:[x:num]` | Numbers (int, float, scientific) |
| `:[x:()]` | Balanced parentheses with content |
| `:[x:(_)]` | Content inside parentheses only |
| `:[x~[a-z]+]` | Custom regex pattern |
| `:[x?]` | Optional match |

### Replacement Operations

```python
# String operations
pycomby(text, pattern, ":[name.upper]")       # Uppercase
pycomby(text, pattern, ":[name.lower]")       # Lowercase
pycomby(text, pattern, ":[name.capitalize]")  # Capitalize

# Arithmetic (on numbers)
pycomby(text, pattern, ":[num.inc]")          # +1
pycomby(text, pattern, ":[num.dec]")          # -1

# Path operations
pycomby(text, pattern, ":[path.basename]")    # Filename without extension
pycomby(text, pattern, ":[path.extension]")   # File extension
pycomby(text, pattern, ":[path.filename]")    # Full filename

# Chain operations
pycomby(text, pattern, ":[x.basename.upper]") # basename, then uppercase
```

## Use Cases

- **Code refactoring** – Find and rewrite patterns across files
- **API migration** – Update function calls (e.g., `old_api()` → `new_api()`)
- **Linting** – Detect problematic patterns in code
- **Code generation** – Template-based transformations
- **Log parsing** – Extract structured data from unformatted text

## Testing

```bash
python -m unittest discover -p "*test*.py" -v
```

All 28 tests pass. See [pycomby_test.py](pycomby_test.py) and [test_cli.py](test_cli.py).

## How It Works

Unlike regex engines, pycomby:

1. **Tokenizes** patterns into literals and holes
2. **Backtracks** intelligently to find matches
3. **Handles structure** with a stack-based scanner for balanced delimiters

This means you get:
- No regex escaping needed for literal text
- Proper handling of nested delimiters (unlike `\(.*\)`)
- Whitespace flexibility without explicit patterns

## Limitations

- Backtracking can be quadratic in worst case (use specific patterns when possible)
- Structural macros are language-agnostic (don't skip language-specific comments)
- Entire input loaded into memory

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License. See [LICENSE](LICENSE).

---

**Related:** [Comby](https://comby.dev) – The original Go implementation
