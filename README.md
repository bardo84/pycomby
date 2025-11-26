# pycomby – A structural Comby-like engine in Python

This is a Python implementation of a **Comby-like structural search and replace**
engine, designed to illustrate the "VM-based" architecture: instead of compiling
patterns into one giant regex, we:

1. Parse the pattern into **tokens** (literals and holes).
2. Interpret these tokens with a small backtracking **matcher**.
3. Implement structural features like **balanced parentheses/braces/brackets**
   with a tiny **stack-based scanner**, not regex hacks.

## Installation

Install from the repository:

```bash
git clone https://github.com/bardo84/pycomby.git
cd pycomby
pip install -e .
```

Or install in development mode (editable):

```bash
pip install -e .
```

This installs the `pycomby` command-line tool and the Python package.

## Usage

### As a Python library

The core API is:

```python
from pycomby import pycomby

# Extract
caps = pycomby("Hello, world!", "Hello, :[greeting:word]!")
# [{'greeting': 'world'}]

# Replace
out = pycomby(
    "file is /path/to/some_file.txt and number is 99",
    "file is :[filepath] and number is :[num:digit]",
    "Basename: :[filepath.basename], next: :[num.inc]",
)
# 'Basename: some_file, next: 100'
```

## Pattern syntax

Patterns are strings with **holes** written as `:[ ... ]`:

- `:[_]` – anonymous wildcard (matches any substring).
- `:[name]` – named wildcard, captured as `name`.
- `:[name?]` – optional named wildcard (may match empty / be absent).
- `:[name:macro]` – named macro.
- `:[name~regex]` – named hole constrained by a regex.
- `:[~regex]` – anonymous regex-constrained hole.
- `:[name:macro?]` or `:[name~regex?]` – macro/regex hole that is optional.
- `...` – shorthand for `:[_]` (wildcard).

### Macros

There are two kinds of macros:

**Regex-based macros** (flat):
- `digit` – `\d+`
- `word`  – `\w+`
- `num`   – floating-point / scientific notation number

**Structural macros** (balanced delimiters):
- `()` – a balanced parenthesis block, including delimiters.
- `[]` – a balanced bracket block, including delimiters.
- `{}` – a balanced brace block, including delimiters.
- `(_)` – balanced parens, **inner content only**.
- `[_]` – balanced brackets, inner content only.
- `{_}` – balanced braces, inner content only.

Example:

```python
text = "y = ((a + b)*(c + d)) + 1"
pattern = ":[term1:()]:[rest~.*]"

caps = pycomby(text, pattern)
# caps == [{'term1': '((a + b)*(c + d))', 'rest': ' + 1'}]
```

Structural macros are implemented with a simple stack-based scan and support
**arbitrary nesting** (unlike regex-only approximations).

### Optional holes

Any hole can end with `?` to make it **optional**:

```python
# Matches both '-1.4e-3' and '-1.4k'
pattern = ":[x:num]:[ext:word?]"
```

Internally, the matcher first tries to **skip** optional holes and only
backtracks into them if needed.

## Replacement and operations

Replacement templates use the same `:[ ... ]` syntax, but interpreted as
**substitutions** instead of matchers:

- `:[name]` – insert the captured value of `name`.
- `:[name.op1.op2]` – apply a chain of operations to the capture.

Built-in operations:

- String operations:
  - `upper`, `lower`, `capitalize`, `strip`
- Integer arithmetic (on captures that parse as ints):
  - `inc` – increment by 1
  - `dec` – decrement by 1
- Path operations (using `pathlib.Path`):
  - `filename` – final path component
  - `basename` – filename without extension
  - `extension` – file extension without dot

Example:

```python
text = "file is /path/to/some_file.txt and number is 99"
pattern = "file is :[filepath] and number is :[num:digit]"
repl = "File: :[filepath.filename], NEXT=: [num.inc]"

out = pycomby(text, pattern, repl)
# 'File: some_file.txt, NEXT=: 100'
```

If an operation is unknown or fails (e.g. `inc` on non-integer), the original
placeholder is left untouched.

## Architecture

### 1. Tokenization

The pattern is scanned for holes of the form `:[... ]` using a small regex.
We split the pattern into:

- `LiteralToken(text, regex)`: fixed text between holes. The regex is compiled
  from `text` with spaces relaxed to `\s*` (structural whitespace).
- `HoleToken(name, macro, regex, optional)`: a typed hole as described above.

We also normalize `...` to `:[_]` for convenience.

### 2. Matching engine

Matching is done by a simple **backtracking recursive** function:

- We try to match the token sequence starting at each position in `text`.
- A literal token uses its precompiled regex, anchored at the current index.
- A structural macro token (e.g. `:[x:()]`) calls `match_balanced`, which:
  - checks that the expected opening delimiter is present,
  - walks forward with a depth counter,
  - returns when depth returns to zero.
- Regex-based or wildcard holes are matched by trying **increasing end
  positions** (non-greedy) and recursing on the remainder of the pattern.

This is conceptually similar to how a backtracking regex engine works, but
here we keep the **structure logic** (balanced delimiters) outside the regex
engine in straightforward Python code.

The matcher returns all successful matches and dicts of named captures.

### 3. Replacement rendering

Replacement uses a simple `re.sub` over the template, looking for `:[...]`
placeholders. Each placeholder is split into a field and optional operations,
which are applied in sequence to the captured value.

### As a command-line tool

After installation, use the `pycomby` command:

```bash
pycomby [OPTIONS] [INPUT] PATTERN [REPLACEMENT]
```

Or run directly without installation:

```bash
python -m pycomby [OPTIONS] [INPUT] PATTERN [REPLACEMENT]
```

### Options

- `-i, --input FILE` – Input file (default: read from stdin)
- `-p, --pattern-file FILE` – Read pattern from file
- `-r, --replacement-file FILE` – Read replacement from file
- `--first` – Match only the first occurrence (default: all)

### Output

**Query mode (no replacement):**
- Outputs matches as **newline-delimited JSON** (NDJSON)
- Each match is one JSON object per line
- Exit code: 0 if matches found, 1 if none

**Replace mode (with replacement):**
- Outputs modified text
- Exit code: 0 if matches found and replaced, 1 if no matches, 2 on error

### Examples

Extract all names from a file:
```bash
echo "John is 30. Jane is 25." | python -m pycomby ':[name:word] is :[age:digit]'
# {"name":"John","age":"30"}
# {"name":"Jane","age":"25"}
```

Replace all matches:
```bash
echo "John is 30. Jane is 25." | python -m pycomby ':[name:word] is :[age:digit]' 'NAME: :[name.upper], AGE: :[age]'
# NAME: JOHN, AGE: 30. NAME: JANE, AGE: 25.
```

Match only first occurrence:
```bash
cat log.txt | python -m pycomby ':[timestamp] - :[level] - :[msg]' --first
```

Pattern from file:
```bash
python -m pycomby -i data.txt -p pattern.txt 'New :[field]'
```

## API reference

### `pycomby(text, pattern, replacement=None)`

Find **all** matches. Returns:
- Without replacement: `List[Dict[str, Optional[str]]]` – list of match dicts
- With replacement: `str` – modified text with all matches replaced

### `pycomby_single(text, pattern, replacement=None)`

Find **first** match only. Returns:
- Without replacement: `Dict[str, Optional[str]]` – first match dict or empty
- With replacement: `str` – text with first match replaced

## Notes and limitations

- This implementation is intentionally simple and focused on clarity, not
  performance. The backtracking over arbitrary wildcards can be quadratic in
  the worst case.
- Structural macros are language-agnostic: they do not skip comments or
  string literals. Extending the engine with a small lexer to handle those
  would be a natural next step.
- The entire file/input is loaded into memory; not designed for multi-gigabyte
  files (but fine for typical text files).

## Running it

As a library:

```python
from pycomby import pycomby

# Extract
caps = pycomby("Hello, world!", "Hello, :[greeting:word]!")
print(caps)  # [{'greeting': 'world'}]

# Replace
out = pycomby("foo bar", ":[x] :[y]", ":[y] :[x]")
print(out)   # "bar foo"
```

As a CLI command:

```bash
python -m pycomby 'pattern' < input.txt
python -m pycomby 'pattern' 'replacement' < input.txt
cat file.txt | python -m pycomby -p pattern.txt -r replacement.txt
```

## Testing

Run all tests:

```bash
python -m unittest discover -p "test*.py" -v
```

Core engine tests: `pycomby_test.py`
CLI tests: `test_cli.py`
