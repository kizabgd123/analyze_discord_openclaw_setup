#!/usr/bin/env python3
"""
OpenClaw Commit Sanity Verifier
═══════════════════════════════
Duboka semantička provera: "Da li ovo što je agent uradio ima smisla?"

Proverava:
  1. Da li se svi moduli importuju korektno (ne samo kompilacija, nego stvarni import)
  2. Da li su DEFAULT_PERSONAS validni sa svim obaveznim poljima
  3. Da li su notebook ID-jevi UUID format
  4. Da li su notebook ID-jevi ISTI kroz sve izvore istine
  5. Da li NLM CLI komande koriste ispravan redosled argumenata
  6. Da li debate_state.json nema "zombi" sesija
  7. Da li openclaw.json šema odgovara očekivanom formatu

Pokretanje:
  python3 .githooks/verify_sanity.py          # iz projekta
  python3 .githooks/verify_sanity.py --strict  # blokira na upozorenja
"""

import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_DIR = Path(__file__).resolve().parent.parent
ERRORS: List[str] = []
WARNINGS: List[str] = []

UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')

# ── Helpers ──────────────────────────────────────────────────────────────────
def error(msg: str):
    ERRORS.append(msg)
    print(f"  ❌ {msg}")

def warn(msg: str):
    WARNINGS.append(msg)
    print(f"  ⚠️  {msg}")

def ok(msg: str):
    print(f"  ✅ {msg}")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Python Import Chain — da li se svi moduli ZAISTA importuju
# ═══════════════════════════════════════════════════════════════════════════════
def check_imports():
    print("\n1️⃣  Python Import Chain (stvarni import, ne samo py_compile)")
    sys.path.insert(0, str(PROJECT_DIR))

    modules = ["judge_guard", "brain_core", "debate_engine"]
    for mod_name in modules:
        try:
            mod = __import__(mod_name)
            ok(f"{mod_name}.py — importuje se")
        except Exception as e:
            error(f"{mod_name}.py — IMPORT GREŠKA: {e}")

    # discord_bot requires discord library — test via AST instead
    bot_file = PROJECT_DIR / "discord_bot.py"
    if bot_file.exists():
        try:
            tree = ast.parse(bot_file.read_text(encoding="utf-8"))
            ok("discord_bot.py — AST parsira se (puna import provera preskočena zbog discord dep)")
        except SyntaxError as e:
            error(f"discord_bot.py — SINTAKSNA GREŠKA: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DEFAULT_PERSONAS validacija
# ═══════════════════════════════════════════════════════════════════════════════
def check_personas():
    print("\n2️⃣  DEFAULT_PERSONAS Struktura & Validacija")

    try:
        from debate_engine import DEFAULT_PERSONAS
    except ImportError:
        error("Ne mogu importovati DEFAULT_PERSONAS iz debate_engine.py")
        return

    REQUIRED_FIELDS = {"id", "name", "role", "default_notebook_id", "notebook_title", "system_prompt", "color", "avatar_url"}
    REQUIRED_ROLES = {"moderator", "architect", "critic", "strategist", "evaluator"}

    found_roles = set()
    notebook_ids: Dict[str, str] = {}

    for i, persona in enumerate(DEFAULT_PERSONAS):
        pid = persona.get("id", f"[index={i}]")
        found_roles.add(pid)

        # Check required fields
        missing = REQUIRED_FIELDS - set(persona.keys())
        if missing:
            error(f"Persona '{pid}' — nedostaju obavezna polja: {missing}")
        else:
            ok(f"Persona '{pid}' — sva obavezna polja prisutna")

        # Check notebook ID is valid UUID
        nb_id = persona.get("default_notebook_id", "")
        if not UUID_RE.match(nb_id):
            error(f"Persona '{pid}' — notebook ID '{nb_id}' nije validan UUID!")
        else:
            notebook_ids[pid] = nb_id

        # Check system_prompt is non-empty
        sp = persona.get("system_prompt", "")
        if len(sp) < 50:
            warn(f"Persona '{pid}' — system_prompt prekratak ({len(sp)} < 50 char)")

    # Check all 5 roles exist
    missing_roles = REQUIRED_ROLES - found_roles
    if missing_roles:
        error(f"Nedostaju persone za uloge: {missing_roles}")
    else:
        ok("Svih 5 persona prisutno (moderator, architect, critic, strategist, evaluator)")

    return notebook_ids


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Cross-File Notebook ID Konzistentnost
# ═══════════════════════════════════════════════════════════════════════════════
def check_id_consistency(persona_ids: Dict[str, str]):
    print("\n3️⃣  Cross-File Notebook ID Konzistentnost")

    # Source 1: openclaw.json
    config_file = PROJECT_DIR / "openclaw.json"
    if config_file.exists():
        config = json.loads(config_file.read_text(encoding="utf-8"))
        config_personas = config.get("personas", {})
        for role, persona_data in config_personas.items():
            config_nb = persona_data.get("notebook_id", "")
            engine_nb = persona_ids.get(role, "")
            if config_nb and engine_nb and config_nb != engine_nb:
                error(f"ID mismatch za '{role}': openclaw.json={config_nb[:12]}... vs debate_engine.py={engine_nb[:12]}...")
            elif config_nb and engine_nb:
                ok(f"'{role}' — openclaw.json ↔ debate_engine.py sinhronizovani")
    else:
        warn("openclaw.json ne postoji")

    # Source 2: .env
    env_file = PROJECT_DIR / ".env"
    if env_file.exists():
        env_text = env_file.read_text(encoding="utf-8")
        match = re.search(r'NLM_NOTEBOOK_ID="?([^"\n]+)"?', env_text)
        if match:
            env_nb = match.group(1).strip()
            mod_nb = persona_ids.get("moderator", "")
            if env_nb and mod_nb and env_nb != mod_nb:
                error(f".env NLM_NOTEBOOK_ID={env_nb[:12]}... ≠ moderator ID {mod_nb[:12]}...")
            else:
                ok(".env NLM_NOTEBOOK_ID ↔ moderator persona sinhronizovani")

    # Source 3: souls/*.md
    souls_dir = PROJECT_DIR / "souls"
    if souls_dir.exists():
        role_to_soul = {"moderator": "moderator.md", "architect": "architect.md",
                        "strategist": "strategist.md", "critic": "critic.md", "evaluator": "evaluator.md"}
        for role, soul_file in role_to_soul.items():
            soul_path = souls_dir / soul_file
            if soul_path.exists():
                soul_text = soul_path.read_text(encoding="utf-8")
                uuids_in_soul = re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', soul_text)
                expected_nb = persona_ids.get(role, "")
                if expected_nb and uuids_in_soul and expected_nb not in uuids_in_soul:
                    error(f"souls/{soul_file} — sadrži UUID {uuids_in_soul[0][:12]}... ali se očekuje {expected_nb[:12]}...")
                elif expected_nb and expected_nb in uuids_in_soul:
                    ok(f"souls/{soul_file} — notebook ID sinhronizovan")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. NLM CLI Komandne Provere (AST analiza)
# ═══════════════════════════════════════════════════════════════════════════════
def check_nlm_commands():
    print("\n4️⃣  NLM CLI Komandna Sintaksa (AST analiza)")

    py_files = list(PROJECT_DIR.glob("*.py"))
    bad_pattern = re.compile(r'''["']query["']\s*,\s*["']notebook["']''')
    good_pattern = re.compile(r'''["']notebook["']\s*,\s*["']query["']''')

    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        if "nlm" not in content:
            continue

        bad_matches = bad_pattern.findall(content)
        good_matches = good_pattern.findall(content)

        if bad_matches:
            error(f"{py_file.name} — Stara NLM sintaksa 'query', 'notebook' detektovana ({len(bad_matches)}x)! Treba 'notebook', 'query'")
        if good_matches:
            ok(f"{py_file.name} — NLM sintaksa ispravna ('notebook', 'query') ({len(good_matches)}x)")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. debate_state.json Integritet
# ═══════════════════════════════════════════════════════════════════════════════
def check_debate_state():
    print("\n5️⃣  debate_state.json Integritet")

    state_file = PROJECT_DIR / "debate_state.json"
    if not state_file.exists():
        warn("debate_state.json ne postoji")
        return

    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        error(f"debate_state.json — neispravan JSON: {e}")
        return

    if not isinstance(data, dict):
        error(f"debate_state.json — root nije dict (tip: {type(data).__name__})")
        return

    if len(data) == 0:
        ok("debate_state.json — čist (nema aktivnih sesija)")
        return

    for ch_id, session in data.items():
        if not isinstance(session, dict):
            error(f"Sesija {ch_id} — nije dict")
            continue

        status = session.get("status", "unknown")
        turns = session.get("turns", [])

        if status in ("stuck", "error", "crashed"):
            warn(f"Sesija {ch_id} — status '{status}' — moguća zombi sesija")
        if len(turns) > 100:
            warn(f"Sesija {ch_id} — {len(turns)} turnova (>100) — moguć bloat")

        # Verify turn structure
        for i, turn in enumerate(turns):
            if not isinstance(turn, dict):
                error(f"Sesija {ch_id}, turn {i} — nije dict")
                break
            if not turn.get("persona_id"):
                error(f"Sesija {ch_id}, turn {i} — nema persona_id")
                break

    ok(f"debate_state.json — {len(data)} sesija provereno")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. openclaw.json Šema Validacija
# ═══════════════════════════════════════════════════════════════════════════════
def check_config_schema():
    print("\n6️⃣  openclaw.json Šema Validacija")

    config_file = PROJECT_DIR / "openclaw.json"
    if not config_file.exists():
        warn("openclaw.json ne postoji")
        return

    try:
        config = json.loads(config_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        error(f"openclaw.json — neispravan JSON: {e}")
        return

    REQUIRED_SECTIONS = ["channels", "agents", "evidenceLayer", "actionGates", "personas"]
    for section in REQUIRED_SECTIONS:
        if section not in config:
            error(f"openclaw.json — nedostaje sekcija '{section}'")
        else:
            ok(f"openclaw.json — sekcija '{section}' prisutna")

    # Validate personas section has all 5 roles
    personas = config.get("personas", {})
    EXPECTED_ROLES = {"moderator", "architect", "critic", "strategist", "evaluator"}
    missing = EXPECTED_ROLES - set(personas.keys())
    if missing:
        error(f"openclaw.json personas — nedostaju uloge: {missing}")
    else:
        ok("openclaw.json personas — svih 5 uloga prisutno")

    # Verify each persona has notebook_id
    for role, p_data in personas.items():
        nb = p_data.get("notebook_id", "")
        if not UUID_RE.match(nb):
            error(f"openclaw.json personas.{role}.notebook_id '{nb}' — nije validan UUID")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    print("═══ OpenClaw Commit Sanity Verifier ═══")
    print(f"Projekat: {PROJECT_DIR}")

    check_imports()
    persona_ids = check_personas() or {}
    check_id_consistency(persona_ids)
    check_nlm_commands()
    check_debate_state()
    check_config_schema()

    # ── Verdikt ──
    strict = "--strict" in sys.argv
    print("\n═══════════════════════════════════════════")
    if ERRORS:
        print(f"❌ NEUSPEŠNO: {len(ERRORS)} grešaka, {len(WARNINGS)} upozorenja")
        for e in ERRORS:
            print(f"   → {e}")
        sys.exit(1)
    elif WARNINGS and strict:
        print(f"⚠️  BLOKIRANO (--strict): {len(WARNINGS)} upozorenja")
        for w in WARNINGS:
            print(f"   → {w}")
        sys.exit(1)
    else:
        if WARNINGS:
            print(f"✅ PROŠLO sa {len(WARNINGS)} upozorenjima")
        else:
            print("✅ SVE PROVERE PROŠLE — Agent je obavio posao ispravno!")
        sys.exit(0)


if __name__ == "__main__":
    main()
