# Database Rules

## Local Engine: SQLite3 (FTS5 Enabled)

The primary local knowledge and vector-alternative retrieval store is SQLite3 with full-text search (FTS5) located at `antigravity_rag.db`.

## Storage Locations

- **Full-Text Knowledge Store**: `antigravity_rag.db`
- **Configuration & Grounding Registry**: `openclaw.json` (Single Source of Truth)
- **Debate Runtime State**: `debate_state.json`
- **Evidence Layer & Provenance Audit**: `DECISION_RECORD_EVIDENCE_LAYER.md`

## Conventions & Rules

1. **Parameterized Queries Only**:
   Always use parameter placeholders (`?`) in SQLite queries. Never interpolate or format strings directly into SQL statements:
   ```python
   # Correct
   cursor.execute("SELECT content FROM rag_cache WHERE key = ?", (key,))
   
   # Prohibited
   cursor.execute(f"SELECT content FROM rag_cache WHERE key = '{key}'")
   ```

2. **Write-Before-Query Barrier (Security Law)**:
   Per `openclaw.json` evidence layer security contract:
   - Any state mutation or significant reasoning step must write its audit record before responding to a query or proceeding to the next turn.
   - Record retrieval mode, confidence score, and timestamp in the evidence layer.

3. **Atomic JSON State Updates**:
   To prevent corrupting `debate_state.json` during crashes or unexpected restarts:
   - Write serialized JSON to a temporary file first (`debate_state.json.tmp`).
   - Use `os.replace()` to atomically swap the file into place.
   ```python
   tmp_file = state_path.with_suffix(".tmp")
   with open(tmp_file, "w", encoding="utf-8") as f:
       json.dump(state_data, f, indent=2, ensure_ascii=False)
   tmp_file.replace(state_path)
   ```

4. **FTS5 Query Sanitization**:
   Queries passed to SQLite FTS5 MATCH expressions must be cleaned of unbalanced quotes, wildcards, or reserved operators that cause SQLite operational syntax errors.

5. **No Blind State Overwrites**:
   When updating `openclaw.json`, validate the structure against the schema before persisting. Do not alter `_comment` or `_version` metadata unless doing an explicit contract release.
