# Installation & Setup

## Install as Package

### Option 1: Development Install (editable)
```bash
git clone https://github.com/bardo84/pycomby.git
cd pycomby
pip install -e .
```

This installs `pycomby` in editable mode, so changes to the source code are immediately reflected.

### Option 2: Regular Install
```bash
git clone https://github.com/bardo84/pycomby.git
cd pycomby
pip install .
```

## Usage After Installation

Once installed, you can use the `pycomby` command directly:

```bash
# Query mode (extract matches)
echo "John is 30" | pycomby ':[name:word] is :[age:digit]'

# Replace mode
echo "John is 30" | pycomby ':[name:word] is :[age:digit]' 'NAME: :[name.upper]'

# From file
pycomby -i input.txt ':[pattern]' ':[replacement]'

# Get help
pycomby --help
```

## Usage Without Installation

If you don't want to install, run directly from the repository:

```bash
python -m pycomby ':[pattern]' < input.txt
```

## Development

Run tests:
```bash
python -m unittest discover -p "*test*.py" -v
```

Run a specific test:
```bash
python pycomby_test.py -v
python test_cli.py -v
```

## Python API

Use as a library in your code:

```python
from pycomby import pycomby, pycomby_single

# Extract matches
matches = pycomby("Hello, world!", "Hello, :[greeting:word]!")
# [{'greeting': 'world'}]

# Replace text
result = pycomby_single(
    "foo bar",
    ":[x] :[y]",
    ":[y] :[x]"
)
# "bar foo"
```

See README.md for full API documentation.
