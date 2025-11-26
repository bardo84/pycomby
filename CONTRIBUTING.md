# Contributing to pycomby

Thank you for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/pycomby.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Install in development mode: `pip install -e .`

## Development

### Running Tests

```bash
# Run all tests
python -m unittest discover -p "*test*.py" -v

# Run specific test file
python pycomby_test.py -v
python test_cli.py -v
```

### Code Style

- Follow PEP 8
- Use type hints where possible
- Add docstrings to functions
- Keep functions focused and testable

### Making Changes

1. Make your changes in a feature branch
2. Add tests for new functionality
3. Ensure all tests pass: `python -m unittest discover -p "*test*.py"`
4. Commit with clear messages: `git commit -m "Add feature: description"`
5. Push to your fork and open a Pull Request

## Project Structure

```
pycomby/
├── pycomby.py           # Core engine (pattern compilation, matching, replacement)
├── pycomby_cli.py       # CLI wrapper (argument parsing, I/O, formatting)
├── __main__.py          # Entry point for `python -m pycomby`
├── pycomby_test.py      # Core engine unit tests
├── test_cli.py          # CLI integration tests
├── test_edge_cases.py   # Edge case validation
├── setup.py             # Package configuration
├── README.md            # Documentation
└── LICENSE              # MIT License
```

## Issues and Discussions

- Report bugs using GitHub Issues
- Suggest features in Discussions
- Ask questions in Discussions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
