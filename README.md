# pycomby

**Comby-like structural search and rewrite for code**

A Python implementation of [Comby](https://comby.dev) patterns for structural code matching and transformation.

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
- **API migration** – Update function calls (e.g., `old_api()` → `new_api()`) with captured context
- **String interpolation in rewrites** – Inject captured identifiers into string literals (e.g., inject module name into `maybe_provider("...")`)
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

## Common Pattern: String Interpolation of Captures

A powerful use case is injecting captured text into string literals during a rewrite, for example when consolidating every `legacy_api::call(...)` site into a shared guard.

```python
# API migration with context: before/after
before = '''legacy_api::provider::<core::math::tan>::call(...)
legacy_api::provider::<core::array::add>::call(...)'''

# Capture the module path and inject it into the new guard call
matches = pycomby(
    before,
    "legacy_api::provider::<:[module]>::call",
    'shared_guard::maybe_provider(":[module]")?.call',
)

# Result (Tier 1):
# shared_guard::maybe_provider("core::math::tan")?.call(...)
# shared_guard::maybe_provider("core::array::add")?.call(...)
```

This is **Tier 1** (structural injection): when the literal you need is already present in the matched text and can be captured, pycomby injects it directly into the replacement string literal. For cases where the injected literal must be derived, see [pycomby_forward.md](pycomby_forward.md) for the path toward **Tier 2/3**.

## Documented Use Case: API Guard Consolidation

1. `Find`: target the existing `legacy_api::provider::<...>::call` invocations; capture the module path or guard label that now drives the helper.
2. `Replace`: feed the captured literal into the new guard call so every rewritten site expresses the same API and logging behavior.
3. `Verify`: rerun the integration or boundary tests that exercise the helper (e.g., those that expect the guard to emit a warning when the provider is missing).

This keeps every call site aligned with the shared guard and prevents `legacy_api::provider` from proliferating across the tree.

## Limitations

- Backtracking can be quadratic in worst case (use specific patterns when possible)
- Structural macros are language-agnostic (don't skip language-specific comments)
- Entire input loaded into memory
- **String interpolation** of captures inside literals currently requires the capture to already contain the desired text; if you need to derive or compute the literal, use multi-pass or external scripting

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License. See [LICENSE](LICENSE).

---

**Related:** [Comby](https://github.com/comby-tools/comby) – The original Comby implementation
