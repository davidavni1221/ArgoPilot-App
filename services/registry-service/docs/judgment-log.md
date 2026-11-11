# Judgment log

Each entry records a suggestion from the coding agent, what was decided, and why.

---

## 1. Latency measurement scope

- **Suggested by the agent:** measure only the farm and plot GET routes, list and by id.
- **Suggested by the user:** check everything, not only what was first measured.
- **Decided:** measure all ten GET routes in one run, including the catalogues.
- **Why:** NFR-1.1 says "GET list and GET by id" without naming resources, so all GET routes fall under it. Measuring them in one run keeps the conditions identical.
- **Result:** every route has p95 between 11 ms and 13 ms, with 0 errors.

## 2. Automated test suite: 64 tests

- **Question from the user:** why 64 tests?
- **Answer:** 64 is not a target. It is the number pytest reports when every rule has a success case and its failure cases. Parametrized cases count once per value.
- **Proof requested by the user:** print the full test run.
- **Done:** the full verbose run printed `64 passed`, with every test marked `PASSED`.
