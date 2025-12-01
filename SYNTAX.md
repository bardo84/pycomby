# pycomby Pattern Syntax Reference

Complete reference for pycomby pattern and replacement syntax.

Patterns use **holes** (placeholders) in the form `:[...]` to match and capture text. See the [original Comby syntax](https://comby.dev/docs/syntax-reference) for inspiration.

## Holes (Matchers)

### Anonymous Wildcard

Match any substring without capturing.

```
:[_]
```

Or use the shorthand:
```
...
```

**Example:**
```python
pycomby("start middle end", "start ... end")
# [{'_': ' middle '}]  # With :[_]
# [{} ]                 # With ... (not captured)
```

### Named Wildcard

Match any substring and capture it.

```
:[name]
```

**Example:**
```python
pycomby("Hello, world!", "Hello, :[greeting]!")
# [{'greeting': 'world'}]
```

### Macros (Built-in Patterns)

#### `:word`

Matches one or more word characters (`\w+`).

```
:[identifier:word]
```

**Example:**
```python
pycomby("user_id", ":[name:word]")
# [{'name': 'user_id'}]

pycomby("John is 30", ":[name:word] is :[age]")
# [{'name': 'John', 'age': '30'}]
```

#### `:digit`

Matches one or more digits (`\d+`).

```
:[count:digit]
```

**Example:**
```python
pycomby("test_123_data", "test_:[num:digit]_data")
# [{'num': '123'}]
```

#### `:num`

Matches numbers in any form: integers, floats, scientific notation.

```
:[value:num]
```

**Example:**
```python
pycomby("values: 42, -1.5, 3.14e-2", ":[a:num], :[b:num], :[c:num]")
# [{'a': '42', 'b': '-1.5', 'c': '3.14e-2'}]
```

### Structural Macros (Balanced Delimiters)

Match balanced parentheses, brackets, or braces.

#### Including Delimiters

Capture the delimiters and everything inside.

```
:[name:()]    # Balanced parentheses
:[name:[]]    # Balanced brackets
:[name:{}]    # Balanced braces
```

**Example:**
```python
code = "result = func(arg1, arg2)"
pycomby(code, "result = :[call:()]")
# [{'call': '(arg1, arg2)'}]
```

Nested delimiters work correctly:
```python
code = "func(inner(1, 2), outer)"
pycomby(code, "func:[args:()]")
# [{'args': '(inner(1, 2), outer)'}]
```

#### Content Only (Inner)

Capture only the content inside delimiters, excluding them.

```
:[name:(_)]   # Content inside parentheses
:[name:[_]]   # Content inside brackets
:[name:{_}]   # Content inside braces
```

**Example:**
```python
code = "func(arg1, arg2)"
pycomby(code, "func:[args:(_)]")
# [{'args': 'arg1, arg2'}]  # No parentheses
```

### Regex Constraints

Match based on a custom regular expression.

```
:[name~regex_pattern]
```

**Example:**
```python
pycomby("color: #FF00AA", "color: :[hex~[0-9a-f]{6}]")
# [{'hex': 'FF00AA'}]

# Email-like pattern
pycomby("user@example.com", ":[email~[a-z.]+@[a-z.]+]")
# [{'email': 'user@example.com'}]
```

### Optional Holes

Make any hole optional with `?`. Matches even if the hole isn't present.

```
:[name?]              # Optional wildcard
:[name:macro?]        # Optional macro
:[name:word?]         # Optional word
:[name~regex?]        # Optional regex
```

**Example:**
```python
# Both match
pycomby("value: 42", "value: :[num:digit]:[unit:word?]")
# [{'num': '42', 'unit': None}]

pycomby("value: 42px", "value: :[num:digit]:[unit:word?]")
# [{'num': '42', 'unit': 'px'}]
```

## Whitespace Handling

Whitespace in patterns matches flexibly. A single space in the pattern matches any amount of whitespace (spaces, tabs, newlines).

**Example:**
```python
# All of these match the same text
pycomby("if ( x > 0 ) then", "if :[cond] then")
pycomby("if(x>0)then", "if :[cond] then")
pycomby("if\n  (x > 0)\nthen", "if :[cond] then")
# All return: [{'cond': '( x > 0 )'}]
```

## Replacement Templates

Use the same `:[...]` syntax in replacement patterns to substitute captured values.

### Basic Substitution

```
:[name]
```

**Example:**
```python
pycomby(
    "Hello, world!",
    "Hello, :[greeting]!",
    "Goodbye, :[greeting]!"
)
# "Goodbye, world!"
```

### Operations

Apply transformations to captured values with the `.operation` syntax.

```
:[name.operation1.operation2]
```

Operations are applied left-to-right.

#### String Operations

- `upper` – Convert to uppercase
- `lower` – Convert to lowercase
- `capitalize` – Capitalize first character
- `strip` – Remove leading/trailing whitespace

**Example:**
```python
pycomby("name: john", "name: :[n]", "NAME: :[n.upper]")
# "NAME: JOHN"

pycomby("  hello  ", ":[text]", "[:[text.strip]]")
# "[hello]"
```

#### Numeric Operations

- `inc` – Increment by 1
- `dec` – Decrement by 1

Applied to captures that parse as integers.

**Example:**
```python
pycomby("id=42", "id=:[num:digit]", "id=:[num.inc]")
# "id=43"
```

#### Path Operations

- `filename` – Filename with extension
- `basename` – Filename without extension
- `extension` – Extension without the dot

**Example:**
```python
path = "/home/user/document.txt"
pycomby(path, ":[p]", "Basename: :[p.basename]")
# "Basename: document"

pycomby(path, ":[p]", "Ext: :[p.extension]")
# "Ext: txt"

pycomby(path, ":[p]", "File: :[p.filename]")
# "File: document.txt"
```

#### Chaining Operations

**Example:**
```python
pycomby(
    "file: /path/to/data.csv",
    "file: :[path]",
    "Basename: :[path.basename.upper]"
)
# "Basename: DATA"
```

Unknown operations leave the placeholder unchanged (no error).

## Examples

### Code Refactoring

Rename a function call:
```bash
echo "result = old_api(x, y)" | pycomby \
  ':[func:word]:[args:(_)]' \
  'new_api:[args:(_)]'
# "result = new_api(x, y)"
```

### Log Parsing

Extract structured data:
```bash
echo "2024-01-15 ERROR: Connection failed" | pycomby \
  ':[date:word] :[level:word]: :[msg]' \
  '{"timestamp":":[date]","level":":[level]","message":":[msg]"}'
```

### Balanced Delimiter Matching

Match function bodies:
```python
code = "def func():\n    return 42"
pattern = "def :[name:word]:[params:(_)]:"
pycomby(code, pattern)
# [{'name': 'func', 'params': ''}]
```

### Complex Transformations

```python
pycomby(
    "Visit https://example.com/path/file.html",
    "Visit https://:[host]/:[path]/:[file]",
    "Host: :[host], Path: :[path], File: :[file.basename]"
)
# "Host: example.com, Path: path, File: file"
```

## API Reference

### Python Functions

```python
from pycomby import pycomby, pycomby_single

# Find all matches
matches = pycomby(text, pattern)
# Returns: List[Dict[str, str]]

# Find first match
first = pycomby_single(text, pattern)
# Returns: Dict[str, str]

# Replace all matches
result = pycomby(text, pattern, replacement)
# Returns: str

# Replace first match
result = pycomby_single(text, pattern, replacement)
# Returns: str
```

### Command Line

```bash
# Query mode (extract matches)
pycomby PATTERN < input.txt

# Replace mode
pycomby PATTERN REPLACEMENT < input.txt

# From file
pycomby -i input.txt PATTERN [REPLACEMENT]

# Pattern from file
pycomby -p pattern.txt REPLACEMENT < input.txt

# First match only
pycomby --first PATTERN [REPLACEMENT] < input.txt
```

Exit codes:
- `0` – Matches found
- `1` – No matches
- `2` – Error

## Tips & Best Practices

1. **Use macros for flexibility** – `:[x:word]` instead of `:[x~\w+]` if a macro exists
2. **Be specific with literals** – The more literal text in your pattern, the faster and more accurate
3. **Leverage structural macros** – Let them handle nested delimiters instead of trying with regex
4. **Test with examples** – Use the Python API to test patterns before using CLI
5. **Chain operations carefully** – Operations that fail silently leave the original placeholder

## Differences from Original Comby

- No multi-language support (language-agnostic delimiters)
- Comment/string skipping is optional context (not language-specific)
- Simpler regex syntax (Rust regex, not PCRE)
- Pure Python implementation (no external dependencies)

See [pycomby.py](pycomby.py) for implementation details.
