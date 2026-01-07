#!/usr/bin/env python3
"""
Language-agnostic context detector for Phase 2.

Detects backend and scope hints from surrounding code patterns.
Supports: Rust, Python, C/C++, Go, TypeScript, etc.
"""

import re
from dataclasses import dataclass
from typing import Optional, List, Set, Dict


@dataclass
class ContextHint:
    """Represents a detected context hint."""
    backend: Optional[str] = None      # "wgpu", "host", "gpu", "cpu", etc.
    scope_type: Optional[str] = None   # "test", "fallback", "gpu_block", "cpu_block"
    attributes: List[str] = None       # ["#[wgpu_test]", "@gpu", etc.]
    confidence: float = 1.0            # 0.0 to 1.0 confidence level
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = []


class ContextDetector:
    """
    Detects backend and scope hints from surrounding code.
    Language-agnostic using pattern matching.
    """
    
    # Backend detection patterns (language-agnostic)
    WGPU_PATTERNS = [
        r'#\[wgpu[_\w]*\]',           # Rust: #[wgpu_test], #[wgpu]
        r'@wgpu',                      # Python/Java: @wgpu
        r'wgpu_test',                  # Function name prefix
        r'GPU_BACKEND_WGPU',           # C constant
        r'"wgpu"',                     # String literal
        r"'wgpu'",
    ]
    
    GPU_PATTERNS = [
        r'GpuTensor',                  # Type name
        r'gpu_tensor',                 # Variable name
        r'GpuArray',
        r'gpu_array',
        r'CUDA',                       # Framework names
        r'cudaMalloc',
        r'torch\.cuda',
        r'tf\.GpuOptions',
        r'#\[gpu[_\w]*\]',            # Rust attribute
        r'@gpu',
    ]
    
    HOST_PATTERNS = [
        r'#\[host[_\w]*\]',           # Rust: #[host], #[host_test]
        r'@host',                      # Python/Java: @host
        r'host_tensor',                # Variable names
        r'cpu_array',
        r'CPU_BACKEND',                # C constant
        r'"host"',                     # String literal
        r"'host'",
        r'"cpu"',
        r"'cpu'",
    ]
    
    TEST_PATTERNS = [
        r'#\[test\]',                 # Rust: #[test]
        r'#\[cfg\(test\)\]',          # Rust: #[cfg(test)]
        r'def test_',                  # Python: test_ prefix
        r'def test\(',
        r'TEST\(',                     # C/C++: TEST macro
        r'EXPECT_',
        r'assert',
    ]
    
    FALLBACK_PATTERNS = [
        r'if.*fallback',               # if fallback available
        r'else.*fallback',
        r'match.*fallback',
        r'try\s*{.*}.*catch',         # try-catch blocks
        r'if let.*Some',               # Rust: if let Some
    ]
    
    def __init__(self, context_window: int = 10):
        """
        Initialize context detector.
        
        :param context_window: Lines of context before/after match to scan
        """
        self.context_window = context_window
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile all regex patterns."""
        self.wgpu_re = [re.compile(p, re.IGNORECASE) for p in self.WGPU_PATTERNS]
        self.gpu_re = [re.compile(p, re.IGNORECASE) for p in self.GPU_PATTERNS]
        self.host_re = [re.compile(p, re.IGNORECASE) for p in self.HOST_PATTERNS]
        self.test_re = [re.compile(p, re.IGNORECASE) for p in self.TEST_PATTERNS]
        self.fallback_re = [re.compile(p, re.IGNORECASE) for p in self.FALLBACK_PATTERNS]
    
    def detect(
        self,
        text: str,
        match_start: int,
        match_end: int
    ) -> ContextHint:
        """
        Detect context hints from surrounding code.
        
        :param text: Full source code
        :param match_start: Start position of match
        :param match_end: End position of match
        :return: ContextHint with detected backend/scope
        """
        # Extract context window
        lines = text[:match_start].split('\n')
        context_before = '\n'.join(lines[-self.context_window:]) if lines else ''
        
        lines = text[match_end:].split('\n')
        context_after = '\n'.join(lines[:self.context_window]) if lines else ''
        
        full_context = context_before + '\n' + context_after
        
        # Scan for patterns
        return self._analyze_context(full_context, context_before)
    
    def _analyze_context(self, full_context: str, context_before: str) -> ContextHint:
        """Analyze context and return hints."""
        hints = ContextHint()
        attributes = []
        
        # Check for test context
        if self._matches_any(context_before, self.test_re):
            hints.scope_type = 'test'
        
        # Check for fallback context
        if self._matches_any(full_context, self.fallback_re):
            hints.scope_type = 'fallback'
        
        # Backend detection (in order of specificity)
        if self._matches_any(full_context, self.wgpu_re):
            hints.backend = 'wgpu'
            attributes.append('wgpu')
            hints.confidence = 0.9
        elif self._matches_any(full_context, self.gpu_re):
            hints.backend = 'gpu'
            attributes.append('gpu')
            hints.confidence = 0.8
        elif self._matches_any(full_context, self.host_re):
            hints.backend = 'host'
            attributes.append('host')
            hints.confidence = 0.85
        
        hints.attributes = attributes
        return hints
    
    def _matches_any(self, text: str, patterns: List) -> bool:
        """Check if any pattern matches in text."""
        return any(p.search(text) for p in patterns)
    
    def detect_backends(self, text: str, match_start: int, match_end: int) -> Set[str]:
        """
        Detect all possible backends for this context.
        
        Returns a set of possible backends:
          - {'wgpu'} if GPU context detected
          - {'host'} if CPU context detected
          - {'host', 'wgpu'} if fallback/dual context detected
          - set() if uncertain
        """
        hint = self.detect(text, match_start, match_end)
        
        if hint.backend == 'wgpu':
            return {'wgpu'}
        elif hint.backend in ('gpu', 'gpu_wgpu'):
            return {'wgpu'}
        elif hint.backend == 'host':
            return {'host'}
        elif hint.scope_type == 'fallback':
            return {'host', 'wgpu'}
        else:
            return set()


# Singleton instance
_detector = ContextDetector(context_window=10)


def detect_context(text: str, match_start: int, match_end: int) -> ContextHint:
    """
    Convenience function to detect context from match position.
    
    :param text: Full source code
    :param match_start: Start of match
    :param match_end: End of match
    :return: ContextHint with detected backend/scope
    """
    return _detector.detect(text, match_start, match_end)


def detect_backends(text: str, match_start: int, match_end: int) -> Set[str]:
    """
    Convenience function to get set of possible backends.
    
    :param text: Full source code
    :param match_start: Start of match
    :param match_end: End of match
    :return: Set of possible backends {'host', 'wgpu', etc.}
    """
    return _detector.detect_backends(text, match_start, match_end)
