"""
baton_manager.py — KGMON Framework Project Memory & Baton Handoff Manager
==========================================================================
Maintains authoritative state files across sessions:
  - plan.md: Planned experiments and falsifiable hypotheses.
  - progress.md: Complete table of experiments with CV/LB scores and fold differences.
  - discoveries.md: Empirically verified findings and successful feature engineering.
  - closed_ideas.md: Explicit blacklist of failed/blocked ideas with deciding reasons.
  - artifacts/kaggle/cookbooks/: Reusable, vetted templates from past competitions.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("Kaggle2.BatonManager")

COOKBOOKS_DIR = Path("artifacts/kaggle/cookbooks")
SYNTHETIC_COOKBOOK_PATH = COOKBOOKS_DIR / "synthetic_features_cookbook.py"
KGMON_RECIPES_PATH = COOKBOOKS_DIR / "kgmon_playbook_recipes.py"

VETTED_COOKBOOK_CODE = '''"""
synthetic_features_cookbook.py — Vetted Feature Engineering Recipes for S6E11
==============================================================================
Provides leak-free, production-grade feature engineering functions.
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold


def extract_digit_trie_features(df: pd.DataFrame, amount_col: str = "amount_usd") -> pd.DataFrame:
    """Extracts discrete integer and fractional trie components without leakage."""
    amt = df[amount_col].astype(float)
    df = df.copy()
    df["cents"] = (amt % 1 * 100).round().astype(int)
    df["int_amount"] = amt.astype(int)
    df["scaled_int"] = (amt * 10).astype(int)
    return df


def oof_target_encode_smooth(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    cat_col: str,
    target_series: pd.Series,
    smoothing: float = 10.0,
    n_splits: int = 5,
    random_state: int = 42
) -> tuple[pd.Series, pd.Series]:
    """Applies strict M-estimate target encoding using nested inner KFold."""
    train_out = pd.Series(index=train_df.index, dtype=float)
    global_mean = target_series.mean()

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    for in_tr_idx, in_val_idx in skf.split(train_df, target_series):
        in_tr_cat = train_df.iloc[in_tr_idx][cat_col]
        in_tr_target = target_series.iloc[in_tr_idx]

        stats = in_tr_target.groupby(in_tr_cat).agg(["count", "mean"])
        counts = stats["count"]
        means = stats["mean"]
        smoothed = (counts * means + smoothing * global_mean) / (counts + smoothing)

        in_val_cat = train_df.iloc[in_val_idx][cat_col]
        train_out.iloc[in_val_idx] = in_val_cat.map(smoothed).fillna(global_mean)

    full_stats = target_series.groupby(train_df[cat_col]).agg(["count", "mean"])
    full_smoothed = (full_stats["count"] * full_stats["mean"] + smoothing * global_mean) / (full_stats["count"] + smoothing)
    val_out = val_df[cat_col].map(full_smoothed).fillna(global_mean)

    return train_out, val_out
'''


class BatonManager:
    def __init__(self, run_dir: Path, competition: str = "playground-series-s6e11"):
        self.run_dir = Path(run_dir)
        self.competition = competition

    @property
    def plan_file(self) -> Path:
        return self.run_dir / "plan.md"

    @property
    def progress_file(self) -> Path:
        return self.run_dir / "progress.md"

    @property
    def discoveries_file(self) -> Path:
        return self.run_dir / "discoveries.md"

    @property
    def closed_ideas_file(self) -> Path:
        return self.run_dir / "closed_ideas.md"

    def initialize_cookbooks(self) -> Path:
        """Initializes shared cookbooks repository with vetted recipes."""
        COOKBOOKS_DIR.mkdir(parents=True, exist_ok=True)
        if not SYNTHETIC_COOKBOOK_PATH.exists():
            SYNTHETIC_COOKBOOK_PATH.write_text(VETTED_COOKBOOK_CODE, encoding="utf-8")
            logger.info(f"[BatonManager] Vetted features cookbook initialized at {SYNTHETIC_COOKBOOK_PATH}")
        return SYNTHETIC_COOKBOOK_PATH

    def update_progress(self, state: Dict[str, Any]) -> Dict[str, str]:
        """Alias for update_baton to maintain compatibility with test suites and runners."""
        return self.update_baton(state)

    def update_baton(self, state: Dict[str, Any]) -> Dict[str, str]:
        """Regenerates all authoritative Baton markdown files deterministically."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.initialize_cookbooks()

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        experiments = state.get("experiments", [])
        blocked_hyps = state.get("blocked_hypotheses", [])
        failures = state.get("failures", [])
        folds_info = state.get("folds_info", "StratifiedKFold (n_splits=5) — FROZEN")
        auth_hash = state.get("authoritative_fold_hash", "bb6cda09006260033590976687e28c1f73ec418812ce5240988f12cd207c1db3")

        # 1. progress.md
        prog_lines = [
            f"# 📊 KGMON Progress Report — {self.competition}",
            f"* **Run ID:** `{state.get('run_id')}` | **Poslednje ažuriranje:** `{now}`",
            f"* **Autoritativni Folds Heš:** `{auth_hash}`",
            f"* **Folds Konfiguracija:** `{folds_info}`",
            "",
            "## Tabela Izvedenih Eksperimenata",
            "| Exp # | Hipoteza | Skeptic Verdict | CV ROC-AUC | Verdict vs Exp 0 | Status | Runner Vreme |",
            "| :---: | :--- | :---: | :---: | :---: | :---: | :---: |"
        ]
        for exp in experiments:
            cv = f"{exp.get('cv_score'):.5f}" if exp.get("cv_score") is not None else "N/A"
            v_vs_b = exp.get("verdict_vs_base", "N/A")
            status = exp.get("status", "UNKNOWN")
            timing = f"{exp.get('phase_timings', {}).get('runner_seconds', 0.0):.1f}s"
            hyp = exp.get("hypothesis", "").replace("\n", " ")[:80] + "..."
            prog_lines.append(f"| {exp.get('exp_no')} | {hyp} | `{exp.get('skeptic_verdict')}` | **`{cv}`** | `{v_vs_b}` | `{status}` | {timing} |")

        self.progress_file.write_text("\n".join(prog_lines) + "\n", encoding="utf-8")

        # 2. closed_ideas.md
        closed_lines = [
            f"# 🚫 Lista Zatvorenih Ideja (Closed Ideas) — {self.competition}",
            "*Eksplicitna crna lista pristupa koji su odbačeni tokom debate ili pali na testovima kako se ne bi ponavljali.*",
            "",
            "## Blokirani i Neuspešni Pristupi",
            "| Tip | Naziv / Hipoteza | Razlog Odbacivanja / Greška | Timestamp |",
            "| :--- | :--- | :--- | :--- |"
        ]
        for f in failures:
            closed_lines.append(f"| `{f.get('type')}` | {f.get('title')} | `{str(f.get('raw_error', ''))[:100]}` | `{f.get('timestamp')}` |")
        for b in blocked_hyps:
            closed_lines.append(f"| `BLOCKED_HYPOTHESIS` | {str(b)[:80]}... | Odbijeno od strane Skeptika / Policy Gate-a | `{now}` |")

        self.closed_ideas_file.write_text("\n".join(closed_lines) + "\n", encoding="utf-8")

        # 3. discoveries.md
        disc_lines = [
            f"# 💡 Verifikovana Otkrića (Discoveries) — {self.competition}",
            "*Signali i tehnike koji su empirijski potvrdili dobitak na CV ROC-AUC metrici.*",
            ""
        ]
        passed_exps = [e for e in experiments if e.get("status") == "PASSED" and e.get("cv_score") is not None]
        for e in passed_exps:
            disc_lines.extend([
                f"### Exp #{e.get('exp_no')} [CV: {e.get('cv_score'):.5f}] — {e.get('verdict_vs_base', 'VERIFIED')}",
                f"* **Hipoteza:** {e.get('hypothesis')}",
                f"* **Deciding Reason:** {e.get('deciding_reason')}",
                f"* **Out-of-Fold SHA-256:** `{e.get('oof_sha256')}`",
                f"* **Model Part SHA-256:** `{e.get('script_sha256')}`",
                ""
            ])
        self.discoveries_file.write_text("\n".join(disc_lines) + "\n", encoding="utf-8")

        # 4. plan.md
        current_leg = "Leg 1 (Baselines & Initial Duel)"
        if len(experiments) >= 10:
            current_leg = "Leg 3 (4-Level Stacking & Final Meta-Ensemble)"
        elif len(experiments) >= 3:
            current_leg = "Leg 2 (Feature Engineering & Synthetic Artifact Exploitation)"

        plan_lines = [
            f"# 📋 KGMON Plan Istraživanja (Research Plan) — {self.competition}",
            f"* **Run ID:** `{state.get('run_id')}` | **Status:** `ACTIVE`",
            f"* **Aktivna Štafeta (Relay Leg):** `{current_leg}`",
            f"* **Zamrznuti Split:** `{folds_info}`",
            "",
            "## Hijerarhija Štafete i 19 Pomoćnih Agenata (Helper Swarm)",
            "- **Leg 1:** Baselines, 1-na-1 duel (Strategist vs Skeptic), postavljanje 5-fold OOF.",
            "- **Leg 2:** KGMON Feature Engine (Snap, Decimals, Benford Law, cKDTree Anchors, Nested TE).",
            "- **Leg 3:** 4-Nivojski Stak (Nivo 1-4) sa L2 Logit Meta-Learnerom.",
            "- **Helper Swarm:** 13 Documentation Helpers (istorija/cookbooks) + 6 Code Review Helpers (leakage/AST).",
            "",
            "## Redosled Istraživačkih Faza (KGMON Playbook 2026)",
            "1. **01_EDA:** Detekcija generator šuma, Benford odstupanja i korelacija.",
            "2. **02_Feature_Engineering:** Snap funkcije, decimalni trie, nested M-estimate target kodiranje.",
            "3. **03_Build_Baselines:** 5 GBDT biblioteka (XGB, LGBM, CatBoost, YDF, RF) + RealMLP/TabM.",
            "4. **04_Screening:** 1-Feature CPU brzi skrining pre skupih GPU obuka.",
            "5. **05_Stacking:** 4-Nivojski Logit Stack sa L2 penalizacijom.",
            "6. **06_Submission_Masking:** Upside-down predikcije (1 - p) radi zaštite konkurentske prednosti.",
            "",
            "## Trenutni Status:",
            f"* **Završeno eksperimenata:** {len(experiments)}",
            f"* **Blokiranih ideja u crnoj listi:** {len(blocked_hyps) + len(failures)}"
        ]
        self.plan_file.write_text("\n".join(plan_lines) + "\n", encoding="utf-8")

        return {
            "plan": str(self.plan_file),
            "progress": str(self.progress_file),
            "discoveries": str(self.discoveries_file),
            "closed_ideas": str(self.closed_ideas_file),
            "cookbooks": str(SYNTHETIC_COOKBOOK_PATH),
            "kgmon_recipes": str(KGMON_RECIPES_PATH)
        }
