# Pycomby Readiness (General API Migration)

## Tier 1 – Structural injection

1. Capture the existing literal (module, identifier, ..) using macros such as `:[module]` inside the matched pattern.
2. Feed the literal into the replacement string so each rewritten call references the same signature.
3. This workflow needs no semantic analysis; it works when the necessary literal already resides near the old API call.
   ```python
   pycomby(
       before,
       "legacy_api::provider::<:[module]>::call",
       'shared_guard::maybe_provider(":[module]")?.call'
   )
   ```
   The `:[module]` capture becomes the literal that now drives the helper invocation.

## Tier 2 – Derived literals and helpers

When the replacement needs metadata that does not appear verbatim in the input:

1. Run pycomby in multiple passes so a later pass can reuse a derived literal produced earlier.
2. Or couple pycomby with a tiny script (Python, shell, etc.) that computes the literal and supplies it to the replacement string.
3. Seen as the next evolution of pycomby, `pycomby_forward.md` sketches future semantic helpers for Tier 2 and Tier 3 scenarios.

## Tier 3 – Semantic pipelines (Future)

Tier 3 migrations require richer tooling (type inference, symbol tables, or history tracking) when the helper context cannot be extracted from the matched text alone. The roadmap in `pycomby_forward.md` documents ongoing work toward those semantic pipelines.

## Quick adoption checklist

1. Define the helper or guard you are migrating toward and describe its required arguments.
2. Identify the literal embedded in the source call (module path, guard label, etc.).
3. Use pycomby structural macros to capture that literal and inject it into the new helper invocation.
4. Rerun the relevant tests (integration, boundary guards, workspace suites) to ensure the rewritten sites behave identically after the migration.

For the broader roadmap, see [`pycomby_forward.md`](pycomby_forward.md). Keep this document as the Tier 1 quick reference.
