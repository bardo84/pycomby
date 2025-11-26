#!/usr/bin/env python3
"""
pycomby: A Comby-like structural search and replace engine in Python.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

def pycomby(text: str, pattern: str, replacement: Optional[str] = None) -> Union[List[Dict[str, Optional[str]]], str]:
    """
    Comby-like structural matching for all occurrences.

    :param text:        Input text to search.
    :param pattern:     Pattern string with holes of the form :[...].
    :param replacement: Optional replacement template. If provided, returns
                         the text with all matches replaced. Otherwise returns
                         a list of dicts of named captures for each match.
    """
    tokens = compile_pattern(pattern)
    
    # Empty pattern is invalid
    if not tokens:
        if replacement is None:
            return []
        else:
            return text
    
    all_captures: List[Dict[str, Optional[str]]] = []
    result_text = text
    offset = 0

    while True:
        ok, (start_in_substring, end_in_substring), captures = match_first(result_text[offset:], tokens)
        if not ok:
            break

        # Adjust positions to account for offset
        match_start = offset + start_in_substring
        match_end = offset + end_in_substring

        if replacement is None:
            all_captures.append(captures)
            # Move offset to end of match
            offset = match_end
            # If nothing was matched (empty match), move forward to avoid infinite loop
            if end_in_substring == start_in_substring:
                offset += 1
        else:
            # Replace this match
            rendered = render_template(replacement, captures)
            result_text = result_text[:match_start] + rendered + result_text[match_end:]
            # Move offset to end of replacement
            offset = match_start + len(rendered)

    if replacement is None:
        return all_captures
    else:
        return result_text


def pycomby_single(text: str, pattern: str, replacement: Optional[str] = None) -> Union[Dict[str, Optional[str]], str]:
    """
    Comby-like structural matching for the first occurrence only.

    :param text:        Input text to search.
    :param pattern:     Pattern string with holes of the form :[...].
    :param replacement: Optional replacement template. If provided, returns
                         the substituted string. Otherwise returns a dict of
                         named captures.
    """
    tokens = compile_pattern(pattern)
    
    # Empty pattern is invalid
    if not tokens:
        if replacement is None:
            return {}
        else:
            return text
    
    ok, (start, end), captures = match_first(text, tokens)
    if not ok:
        captures = {}

    if replacement is None:
        return captures
    else:
        rendered = render_template(replacement, captures)
        return text[:start] + rendered + text[end:]


# ------------------------------------------------------------
# Pattern representation
# ------------------------------------------------------------

@dataclass
class LiteralToken:
    text: str
    regex: re.Pattern


@dataclass
class HoleToken:
    name: Optional[str]          # None for anonymous
    macro: Optional[str]         # e.g. "word", "digit", "()", "{}"
    regex: Optional[re.Pattern]  # explicit ~regex constraint
    optional: bool               # trailing ?
    # For structural macros like (), {}, [] we don't need regex


Token = Union[LiteralToken, HoleToken]


# ------------------------------------------------------------
# Macros and operations
# ------------------------------------------------------------

# Regex-like macros (flat, no nesting semantics)
REGEX_MACROS: Dict[str, str] = {
    "digit": r"\d+",
    "word": r"\w+",
    "num": r"[-+]?[0-9]+(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?",
}

# Structural macros that require a stack (balanced delimiters)
STRUCTURAL_MACROS = {
    "()": ("(", ")", False),
    "[]": ("[", "]", False),
    "{}": ("{", "}", False),
    "(_)": ("(", ")", True),   # inner content only
    "[_]": ("[", "]", True),
    "{_}": ("{", "}", True),
}

# Operations usable in replacement templates :[name.op1.op2]
OPERATIONS = {
    # String operations
    "upper": str.upper,
    "lower": str.lower,
    "capitalize": str.capitalize,
    "strip": str.strip,

    # Arithmetic operations
    "inc": lambda v: str(int(v) + 1),
    "dec": lambda v: str(int(v) - 1),

    # File path operations using pathlib
    "filename": lambda p: Path(p).name,
    "basename": lambda p: Path(p).stem,
    "extension": lambda p: Path(p).suffix.lstrip("."),
}


# ------------------------------------------------------------
# Pattern compilation
# ------------------------------------------------------------

HOLE_RE = re.compile(r":\[[^\]]*\]")


def compile_pattern(pattern: str) -> List[Token]:
    """
    Parse the Comby-like pattern into a list of tokens (literals + holes).
    """
    # Support ... as synonym for :[_]
    pattern = pattern.replace("...", ":[_]")

    tokens: List[Token] = []
    pos = 0

    for m in HOLE_RE.finditer(pattern):
        # Literal segment before the hole
        if m.start() > pos:
            lit = pattern[pos:m.start()]
            tokens.append(make_literal_token(lit))
        hole_content = m.group(0)[2:-1]  # strip :[ ]
        tokens.append(parse_hole(hole_content))
        pos = m.end()

    # Trailing literal
    if pos < len(pattern):
        lit = pattern[pos:]
        tokens.append(make_literal_token(lit))

    return tokens


def make_literal_token(text: str) -> LiteralToken:
    r"""
    Create a literal token, compiling to a regex that treats spaces as \s*.
    """
    if not text:
        # Empty literal still matters for structure, but matching is trivial
        return LiteralToken(text="", regex=re.compile(""))

    escaped = re.escape(text)
    # Turn escaped spaces (\ ) into \s*
    escaped = re.sub(r"\\ +", r"\\s*", escaped)
    return LiteralToken(text=text, regex=re.compile(escaped))


def parse_hole(content: str) -> HoleToken:
    """
    Parse the inside of :[ ... ] into a HoleToken.

    Grammar (informal):
        base = content without trailing ?
        base = "_"                      -> anonymous wildcard
             | name                     -> named wildcard
             | name ":" macro           -> named macro
             | ":" macro                -> anonymous macro
             | name "~" regex           -> named regex-constrained hole
             | "~" regex                -> anonymous regex-constrained hole
    """
    optional = content.endswith("?")
    if optional:
        content = content[:-1]

    name: Optional[str] = None
    macro: Optional[str] = None
    regex_pat: Optional[str] = None

    if "~" in content:
        # name~regex or ~regex
        lhs, rhs = content.split("~", 1)
        lhs = lhs.strip()
        rhs = rhs.strip()
        if lhs and lhs != "_":
            name = lhs
        regex_pat = rhs

    elif ":" in content:
        # name:macro or :macro
        lhs, rhs = content.split(":", 1)
        lhs = lhs.strip()
        rhs = rhs.strip()
        if lhs and lhs != "_":
            name = lhs
        macro = rhs

    else:
        # Simple wildcard or named wildcard
        c = content.strip()
        if c and c != "_":
            name = c
        # macro and regex remain None

    if macro and macro not in REGEX_MACROS and macro not in STRUCTURAL_MACROS:
        raise ValueError(f"Unknown macro: {macro}")

    regex = None
    if regex_pat:
        try:
            regex = re.compile(regex_pat)
        except re.PatternError as e:
            raise ValueError(f"Invalid regex pattern in hole: {regex_pat!r} - {e}")

    return HoleToken(
        name=name,
        macro=macro,
        regex=regex,
        optional=optional,
    )


# ------------------------------------------------------------
# Matching engine (backtracking)
# ------------------------------------------------------------

def match_first(text: str, tokens: List[Token]) -> Tuple[bool, Tuple[int, int], Dict[str, Optional[str]]]:
    """
    Try to find the first match of the token sequence anywhere in text.
    Returns (ok, (start_pos, end_pos), captures).
    """
    for start in range(len(text) + 1):
        ok, end_pos, caps = match_from(text, tokens, 0, start, {})
        if ok:
            return True, (start, end_pos), caps
    return False, (0, 0), {}


def match_from(
    text: str,
    tokens: List[Token],
    ti: int,
    i: int,
    captures: Dict[str, Optional[str]],
) -> Tuple[bool, int, Dict[str, Optional[str]]]:
    """
    Recursive matcher with backtracking over holes.
    ti: index in tokens
    i:  index in text
    """
    if ti == len(tokens):
        # Reached end of pattern – success
        return True, i, captures

    token = tokens[ti]

    if isinstance(token, LiteralToken):
        # Literal must match at current position
        m = token.regex.match(text, i)
        if not m:
            return False, i, captures
        return match_from(text, tokens, ti + 1, m.end(), captures)

    # HoleToken
    hole: HoleToken = token

    # Structural macro?
    if hole.macro in STRUCTURAL_MACROS:
        open_ch, close_ch, inner_only = STRUCTURAL_MACROS[hole.macro]
        new_i, chunk = match_balanced(text, i, open_ch, close_ch, inner_only)
        if new_i is None:
            return False, i, captures
        new_caps = dict(captures)
        if hole.name:
            new_caps[hole.name] = chunk
        return match_from(text, tokens, ti + 1, new_i, new_caps)

    # Regex-based macro or explicit regex or wildcard
    # For macro/regex-constrained holes we try **greedy** (longest-first)
    # to give them a chance to consume as much as possible while still
    # allowing the rest of the pattern to match. For plain wildcards we
    # keep non-greedy (shortest-first) to avoid blowing up the search.
    if hole.macro in REGEX_MACROS or hole.regex is not None:
        end_iter = range(len(text), i, -1)  # longest-first, non-empty
    else:
        end_iter = range(i, len(text) + 1)  # shortest-first, may be empty

    for end in end_iter:
        substr = text[i:end]

        # Macro constraint
        if hole.macro in REGEX_MACROS:
            macro_re = re.compile(f"^(?:{REGEX_MACROS[hole.macro]})$")
            if not macro_re.match(substr):
                continue

        # Explicit regex constraint
        if hole.regex and not hole.regex.fullmatch(substr):
            continue

        # If neither macro nor regex: wildcard always OK
        # (substr can be empty here when using the non-greedy iterator)
        new_caps = dict(captures)
        if hole.name is not None:
            new_caps[hole.name] = substr

        ok, end_pos, cap_res = match_from(text, tokens, ti + 1, end, new_caps)
        if ok:
            return ok, end_pos, cap_res

    # If we get here, no match via consuming characters. For optional
    # holes we allow them to be skipped entirely.
    if hole.optional:
        new_caps = dict(captures)
        if hole.name is not None and hole.name not in new_caps:
            new_caps[hole.name] = None
        return match_from(text, tokens, ti + 1, i, new_caps)

    return False, i, captures


def match_balanced(
    text: str,
    i: int,
    open_ch: str,
    close_ch: str,
    inner_only: bool,
) -> Tuple[Optional[int], Optional[str]]:
    """
    Match a balanced region starting at position i with given delimiters.

    Comment- and string-aware:

    - Braces/parens/brackets are *not* counted when inside:
      - string literals delimited by double quotes (") or single quotes (')
        with backslash escaping, or
      - line comments starting with // and running to end-of-line, or
      - block comments delimited by /* ... */.

    Returns (new_i, chunk) where:
      - new_i is position after the closing delimiter
      - chunk is the matched text (including delimiters) unless inner_only,
        in which case delimiters are stripped.

    If no balanced region is found, returns (None, None).
    """
    n = len(text)
    if i >= n or text[i] != open_ch:
        return None, None

    depth = 1
    start = i
    i += 1

    in_string: Optional[str] = None  # '"' or "'"
    in_line_comment = False
    in_block_comment = False

    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        # Handle exiting comments / strings first
        if in_string is not None:
            if c == '\\':
                # Skip escaped character
                i += 2
                continue
            if c == in_string:
                in_string = None
            i += 1
            continue

        if in_line_comment:
            if c == '\n':
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if c == '*' and nxt == '/':
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        # Not in comment/string: check for entering them
        if c == '/' and nxt == '/':
            in_line_comment = True
            i += 2
            continue
        if c == '/' and nxt == '*':
            in_block_comment = True
            i += 2
            continue
        if c == '"' or c == "'":
            in_string = c
            i += 1
            continue

        # Now handle structural delimiters
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                end = i + 1
                if inner_only:
                    return end, text[start + 1 : end - 1]
                else:
                    return end, text[start:end]

        i += 1

    return None, None  # unbalanced


# ------------------------------------------------------------
# Replacement rendering
# ------------------------------------------------------------

def render_template(template: str, captures: Dict[str, Optional[str]]) -> str:
    """
    Replace :[name] or :[name.op1.op2] placeholders with capture values,
    applying optional chained operations.
    """
    def replacer(m: re.Match) -> str:
        placeholder = m.group(1)
        parts = placeholder.split(".")
        field = parts[0]
        ops = parts[1:]

        if field not in captures or captures[field] is None:
            return m.group(0)

        value = str(captures[field])
        for op_name in ops:
            func = OPERATIONS.get(op_name)
            if func is None:
                # Unknown operation: leave placeholder unchanged
                return m.group(0)
            try:
                value = func(str(value))
            except Exception:
                # On failure, keep original placeholder
                return m.group(0)
        return str(value)

    return re.sub(r":\[([^\]]+)\]", replacer, template)


# ------------------------------------------------------------
# CLI Entry point
# ------------------------------------------------------------

if __name__ == '__main__':
    from pycomby_cli import main
    main()
