# QA: Pycomby Forward - Phase 1–3 Questions & Answers

**Status:** Living document for tracking design decisions on semantic injection roadmap  
**Last updated:** January 2025  
**Audience:** Maintainers, architects, and Phase 1 implementers

---

## Overview

This document tracks open questions, design decisions, and implementation gaps for the pycomby Forward roadmap (phases 1–3). It serves as a reference for what's been decided, what's still open, and what's blocking implementation.

---

## PHASE 1: Lightweight Lookup — Design Questions

### Q1.1: Registry Parameter Flow (CRITICAL)

**Question:** How does the `--registry` parameter flow from CLI through the codebase to `apply_operation()`?

**Current in pycomby_forward.md:**
```python
# In pycomby.py: add_operation('lookup', lambda key, registry: registry.get(key, key))
# In CLI: pycomby -p pattern.txt -r replacement.txt --registry registry.json input.txt
# In Python API: result = pycomby(text, pattern, replacement, registry={...})
```

**What's missing:**
- `pycomby_cli.py`: Where does `--registry` get parsed?
- `pycomby.py`: How is `registry` passed from `pycomby()` → `replace_matches()` → `apply_operation()`?
- Exact function signature changes needed

**Sub-questions:**
- [ ] Does `pycomby()` function signature change from `pycomby(text, pattern, replacement=None)` to `pycomby(text, pattern, replacement=None, registry=None)`?
- [ ] How does `apply_operation()` currently receive parameters? (via `extra_args` dict? class attribute?)
- [ ] Does `pycomby_cli.py` need to load the registry file and pass it as a dict?

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

### Q1.2: Registry Key Mapping Strategy (CRITICAL)

**Question:** How do capture values map to registry keys?

**Current in pycomby_forward.md:**
```python
key = f"builtin:{value}"  # or custom key logic
```

**What's missing:**
- Is `"builtin:"` a **fixed hardcoded prefix**?
- Or is it user-configurable? (e.g., `--registry-prefix builtin`)
- How does the code know to prepend `"builtin:"` to the captured value?

**Sub-questions:**
- [ ] Example: If pattern captures `:[func:word]` → `"atan"`, does it automatically:
  - [ ] Become `"builtin:atan"` for lookup?
  - [ ] Or is there a two-phase replacement like `:[func.add_prefix("builtin:").lookup]`?
- [ ] What if someone wants different prefixes for different captures in the same pattern?
- [ ] Should the key format be configurable per-pattern? Per-replacement? Per-CLI-invocation?

**Current assumption:** Prefix is fixed per-invocation (not per-capture)

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

### Q1.3: Registry Format Support (MEDIUM)

**Question:** What file formats should Phase 1 support?

**Current in pycomby_forward.md:**
- "Start with JSON (universal), add YAML wrapper if needed"
- But Phase 1 quick-start only shows JSON syntax

**What's missing:**
- Should Phase 1 support both JSON AND YAML, or just JSON initially?
- Should we support inline registries? (e.g., `--registry '{"key": "value"}'`)
- Should we support environment variables? (e.g., `--registry $PYCOMBY_REGISTRY_FILE`)

**Sub-questions:**
- [ ] CLI should accept: `--registry registry.json` only, or also inline?
- [ ] If inline: how do we parse? Shell parsing could be fragile.
- [ ] Should registry be a single file, or multiple files? (e.g., `--registry reg1.json --registry reg2.json`)

**Current assumption:** Single JSON file, file path only (not inline)

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

### Q1.4: Fallback & Error Handling (MEDIUM)

**Question:** What happens when a registry lookup fails?

**Current in pycomby_forward.md:**
```python
return registry.get(key, f"TODO_CONTEXT_{value}")
```

**What's missing:**
- Is `TODO_CONTEXT_` placeholder the right choice?
- Should we also log a warning?
- Should it be an error that stops processing, or a warning that continues?
- What if the registry file is missing/malformed?

**Sub-questions:**
- [ ] When lookup fails, should we:
  - [ ] Return `TODO_CONTEXT_atan` (silent placeholder)?
  - [ ] Return original capture + log warning to stderr?
  - [ ] Raise exception and abort?
- [ ] What if the registry JSON is malformed? (silent error? exception?)
- [ ] Should there be a strict mode (`--strict-registry`) vs. lenient mode?

**Current assumption:** Silent fallback to `TODO_CONTEXT_` placeholder

**Decision:** Fallback should be transparent to the user via flags controlling permitted action; produce a list of failed lookups for review later (not silent, but also not blocking)

**Decided by:** User (provided answer)  
**Date:** 2025-01-07  
**Rationale:** Makes incomplete migrations visible; allows user to choose between strict/lenient modes via flags

---

### Q1.5: Testing Strategy vs. Actual Code (MEDIUM)

**Question:** How does the proposed test actually match the current codebase?

**Current in pycomby_forward.md:**
```python
assert apply_operation("atan", "lookup", registry={"builtin:atan": "builtins::math::..."}) \
    == "builtins::math::..."
```

**What's missing:**
- What is the actual signature of `apply_operation()` in the current codebase?
- Does it accept `(value, operation, extra_args=None)`?
- Should tests also cover:
  - [ ] Key not found → TODO_CONTEXT fallback?
  - [ ] Empty registry?
  - [ ] Malformed registry?
  - [ ] Multiple lookups in one replacement?

**Current assumption:** `apply_operation(value, operation, extra_args=None)`

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

### Q1.6: Registry Key Collision (LOW)

**Question:** What if someone has both `"atan"` and `"builtin:atan"` as keys in their registry?

**Current:** Not addressed in forward.md

**Impact:** Low (unlikely but possible if registry is user-provided)

**Sub-questions:**
- [ ] Should we validate/warn about duplicate keys?
- [ ] Should we prevent certain key formats?

**Current assumption:** User's responsibility; no validation

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

## PHASE 1: Implementation & Integration

### Q1.7: Backwards Compatibility (MEDIUM)

**Question:** Does adding `--registry` parameter and `lookup` operation break existing scripts?

**Current in pycomby_forward.md:**
> "No—`lookup` is a new operation; existing patterns unaffected"

**What's missing:**
- Explicit backwards-compatibility checklist
- CLI argument parsing: does `--registry` conflict with existing flags?
- Python API: does new `registry=None` parameter break existing code? (Should be fine with default)

**Sub-questions:**
- [ ] Does anyone already use `.lookup` operation? (Unlikely)
- [ ] Does the CLI have any flag conflict?
- [ ] Can existing tests run without modification?

**Current assumption:** Fully backwards compatible

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

### Q1.8: SYNTAX.md Documentation Update (LOW)

**Question:** How should `.lookup` be documented once Phase 1 lands?

**Current:** Not addressed; forward.md mentions updating docs but doesn't specify format

**New SYNTAX.md entry would be:**
```markdown
#### `lookup`

Look up the captured value in a registry (requires --registry or registry parameter).

Example:
  Pattern: api::provider::<:[module]>::call(...)
  Replacement: runtime::maybe_provider(":[module.lookup]")?.call(...)
  Registry: {"builtin:module": "full::path::to::module"}
```

**Sub-questions:**
- [ ] Where in SYNTAX.md should this go? (New section "Registry Operations"?)
- [ ] Should we add an example to README.md about registry-based migrations?
- [ ] Should PYCOMBY_QUICK_REFERENCE.md be updated too?

**Current assumption:** Add section to SYNTAX.md, update README.md with example

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

### Q1.9: Large-Scale Migration Workflow (LOW)

**Question:** How do users apply Phase 1 to many files?

**Current:** Forward.md shows single-file examples only

**Not addressed:**
```bash
# What's the recommended workflow?
for file in src/**/*.rs; do
  pycomby -p p.txt -r r.txt --registry reg.json < "$file" > "$file.new"
  mv "$file.new" "$file"
done
```

**Sub-questions:**
- [ ] Should Phase 1 support a batch mode or glob pattern?
- [ ] Should users write their own shell script, or should pycomby provide tooling?
- [ ] Should there be a dry-run mode?

**Current assumption:** Users write their own shell scripts; pycomby handles single file

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

## PHASE 2: Context Inference — Design Questions

### Q2.1: Phase 2 Syntax is Speculative (CRITICAL)

**Question:** Is the `@hint` syntax in Phase 2 pseudocode or a real proposal?

**Current in pycomby_forward.md:**
```
Pattern:
  runmat_accelerate_api::provider::<:[module]>:::[function]
  
  @hint backend = detect_from_context(...)
```

**What's missing:**
- Is this **proposed syntax** or just **conceptual placeholder**?
- How would pycomby parser handle `@hint`?
- What does `detect_from_context(...)` mean?

**Sub-questions:**
- [ ] Is `@hint` a new pattern syntax that needs parser changes?
- [ ] Or is it metadata outside the pattern?
- [ ] How does `detect_from_context()` work? (external hook? built-in function?)
- [ ] When does hint detection run? (during matching? during replacement?)

**Current assumption:** Pseudocode; Phase 2 syntax not finalized

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

### Q2.2: Phase 1 vs Phase 2 Coexistence (MEDIUM)

**Question:** Can Phase 1 (registry lookup) and Phase 2 (context inference) coexist?

**Current:** Forward.md treats them as sequential phases

**Not addressed:**
- Can users mix Tier 1 + Phase 1 lookups + Phase 2 hints in the same file?
- Is Phase 2 a **replacement** of Phase 1, or an **extension**?

**Sub-questions:**
- [ ] Should `--registry` still work once Phase 2 lands?
- [ ] Can a single pattern use both `.lookup` and `@hint`?
- [ ] If Phase 2 handles 99% of cases, should Phase 1 still be maintained?

**Current assumption:** Phase 1 and Phase 2 coexist; Phase 2 extends Phase 1

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

### Q2.3: Phase 2 Blocking Condition (MEDIUM)

**Question:** Does Phase 2 require Phase 1 to be "working" first?

**Current in pycomby_forward.md:**
```
| **Phase 2** | 3–5d | +99% Tier 2 | Week 2–3 | Phase 1 working |
```

**What's missing:**
- What does "Phase 1 working" mean? (Shipped and tested in production?)
- Can Phase 2 development start in parallel?
- What if Phase 1 takes longer than 1–2 days?

**Current assumption:** Phase 1 must be fully implemented & tested before Phase 2 starts

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

## PHASE 3: Semantic Pipeline — Design Questions

### Q3.1: Resolver Plugin API (HIGH)

**Question:** What does the semantic resolver plugin interface look like?

**Current in pycomby_forward.md:**
```python
class RunMatBuiltinResolver(SemanticResolver):
    def resolve(self, context, capture_dict):
        module = capture_dict["module"]
        function = capture_dict["function"]
        backend = self.infer_backend(context)
        return self.builtin_context_map.get((function, backend))
```

**What's missing:**
- Base class `SemanticResolver`: what methods are required?
- What is `context`? (lines of surrounding code? AST?)
- How is `context` passed to the resolver?
- How do resolvers register themselves?

**Sub-questions:**
- [ ] Is resolver a class or a callable?
- [ ] Should there be a resolver registry/factory pattern?
- [ ] How are multiple resolvers chained? (first-match? vote?)

**Current assumption:** Class-based resolver with `resolve(context, capture_dict)` method

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

### Q3.2: Execution Context Scoping (MEDIUM)

**Question:** What does "scoped execution context" mean for Phase 3?

**Current in pycomby_forward.md:**
```python
match = pycomby.match(
    text, 
    pattern, 
    semantic_resolver=RunMatBuiltinResolver(),
    context_window=10  # lines of context before/after match
)
```

**What's missing:**
- What is `context_window=10`? (lines before/after?)
- How is context extracted? (full file? AST nodes?)
- What data structure is passed to resolver.resolve()?

**Sub-questions:**
- [ ] Should context be raw text lines or parsed AST?
- [ ] How much context is needed for backend detection? (10 lines? 100?)
- [ ] Should context window be configurable per-resolver?

**Current assumption:** Context window is configurable; data passed as dict/object

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

### Q3.3: Phase 3 Timeline & Effort (LOW)

**Question:** Is "1–2 weeks" realistic for Phase 3?

**Current in pycomby_forward.md:**
```
| **Phase 3** | 1–2w | Generic engine | Month 2 | Phase 2 working |
```

**Not addressed:**
- Does this assume Phase 1 + 2 are complete first?
- What if resolver plugins are complex?
- Should Phase 3 be multiple sub-phases?

**Current assumption:** 1–2 weeks for basic resolver plugin system

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

## CROSS-PHASE: Strategic Questions

### QX.1: Tier 2 Coverage Gap After Phase 1 (MEDIUM)

**Question:** Why does Phase 1 only cover ~70% of Tier 2, not 99%?

**Current in pycomby_forward.md:**
```
| **Tier 2 (Phase 1)** | Design done | 1–2d | None | +70% coverage |
| **Tier 2 (Phase 2)** | Planned | 3–5d | Phase 1 | +99% coverage |
```

**What's missing:**
- What are the remaining 30% of Tier 2 cases that Phase 1 doesn't cover?
- Are they context-inference cases? Or something else?
- Should users document which migrations can't use Phase 1?

**Sub-questions:**
- [ ] Can we get a concrete list of "Phase 1 supported" vs. "Phase 2 needed" migration types?
- [ ] Should the 70% estimate be verified with real code samples?

**Current assumption:** ~70% based on simple registry lookups; 30% need backend inference

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

### QX.2: Alternative to Registry: External Script (MEDIUM)

**Question:** Should we document an alternative to Phase 1: post-process with a script?

**Current:** Forward.md doesn't mention alternatives

**Alternative approach:**
```bash
pycomby -p p.txt -r r.txt < input.rs > temp.rs
python3 post_process.py temp.rs reg.json > output.rs
```

**Sub-questions:**
- [ ] Should Phase 1 support this workflow?
- [ ] Or is it out-of-scope for pycomby?
- [ ] Should we document it anyway?

**Current assumption:** Phase 1 is the recommended approach; alternatives are user's responsibility

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

### QX.3: Success Metrics (LOW)

**Question:** How will we measure Phase 1–3 success?

**Current in pycomby_forward.md:**
```
### Phase 1 (Lightweight Lookup):
- ✅ Registry parameter accepted by CLI and Python API
- ✅ `lookup` operation resolves correctly in replacements
- ✅ Fallback (TODO_CONTEXT) works when key not in registry
- ✅ At least 5 RunMat migration patterns unblocked
```

**What's missing:**
- Are these criteria testable/measurable?
- Should we add performance metrics?
- Should we track adoption (how many users try Phase 1)?

**Sub-questions:**
- [ ] Should success criteria include "passes all regression tests"?
- [ ] Should we measure time-to-implement?
- [ ] Should we get user feedback after implementation?

**Current assumption:** Criteria as stated are sufficient

**Decision:** _______________  
**Decided by:** _______________  
**Date:** _______________

---

## DECISION LOG

### Decision Record Template

```
**Decision ID:** QX.Y  
**Question:** [What was decided?]  
**Resolution:** [How was it resolved?]  
**Decided by:** [Name/role]  
**Date:** [YYYY-MM-DD]  
**Rationale:** [Why this decision?]  
**Impacts:** [What changes?]  
**Blocks:** [What does this unblock?]  
```

---

## Implementation Checklist

Once questions are answered, use this checklist to track Phase 1 implementation:

- [ ] Q1.1 answered: Registry parameter flow defined
- [ ] Q1.2 answered: Key mapping strategy decided
- [ ] Q1.3 answered: Registry format support scoped
- [ ] Q1.4 answered: Fallback behavior documented
- [ ] Q1.5 answered: Tests match actual API
- [ ] Q1.7 verified: Backwards compatibility confirmed
- [ ] Code: `apply_operation()` updated with lookup
- [ ] Code: `pycomby_cli.py` updated with `--registry` flag
- [ ] Code: Registry loading implemented
- [ ] Tests: Unit tests for lookup operation pass
- [ ] Tests: Integration tests with sample code pass
- [ ] Tests: Regression tests pass
- [ ] Docs: SYNTAX.md updated
- [ ] Docs: README.md updated
- [ ] Docs: PYCOMBY_QUICK_REFERENCE.md updated
- [ ] Review: Code review passed
- [ ] Release: Phase 1 released

---

## Notes for Future Updates

**When to update this doc:**
- When a design question is answered
- When implementation hits an unexpected issue
- When user feedback changes priorities
- When Phase 2/3 work begins

**How to update:**
- Fill in decision fields once answered
- Add new questions as they arise
- Move answered questions to Decision Log
- Keep this doc as the source of truth

---

**Document owner:** [_____________]  
**Last reviewed by:** [_____________]  
**Next review date:** [_____________]
