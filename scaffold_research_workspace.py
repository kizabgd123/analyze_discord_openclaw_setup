#!/usr/bin/env python3
"""
Scaffolds a persistent research workspace adhering to the Hermes Research Relay protocol:
Independent Discovery -> Research Relay -> Execution -> Verification -> Continuous Improvement.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates" / "research-workspace"

def scaffold_workspace(
    target_dir: Path,
    title: str,
    description: str,
    metric: str = "CV Score",
    metric_target: str = "Higher is better",
    validation: str = "5-Fold Stratified CV (Leak-Free)",
    budget: str = "Defined per task card",
    orchestrator: str = "default",
    researcher_1: str = "kiza",
    researcher_2: str = "kreten",
    experiment_engineer: str = "kiza",
    verifier: str = "kreten",
) -> None:
    target_dir = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    replacements = {
        "{{OBJECTIVE_TITLE}}": title,
        "{{OBJECTIVE_DESCRIPTION}}": description,
        "{{PRIMARY_METRIC}}": metric,
        "{{METRIC_TARGET}}": metric_target,
        "{{VALIDATION_STRATEGY}}": validation,
        "{{COMPUTE_BUDGET}}": budget,
        "{{ORCHESTRATOR}}": orchestrator,
        "{{RESEARCHERS}}": f"{researcher_1}, {researcher_2}",
        "{{EXPERIMENT_ENGINEER}}": experiment_engineer,
        "{{EVIDENCE_VERIFIER}}": verifier,
    }

    # Structure definition
    dirs = [
        target_dir / "research" / "discoveries",
        target_dir / "experiments",
        target_dir / "verification",
        target_dir / "planning",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Process files
    for root, _, files in os.walk(TEMPLATES_DIR):
        rel_root = Path(root).relative_to(TEMPLATES_DIR)
        dest_root = target_dir / rel_root
        dest_root.mkdir(parents=True, exist_ok=True)

        for f in files:
            src_file = Path(root) / f
            dest_file = dest_root / f

            if not dest_file.exists():
                text = src_file.read_text(encoding="utf-8")
                for key, val in replacements.items():
                    text = text.replace(key, str(val))
                dest_file.write_text(text, encoding="utf-8")
                print(f"[CREATED] {dest_file.relative_to(target_dir)}")
            else:
                print(f"[EXISTS]  {dest_file.relative_to(target_dir)}")

    print(f"\n✅ Research workspace successfully scaffolded at: {target_dir}")

def main():
    parser = argparse.ArgumentParser(description="Scaffold an autonomous Hermes research workspace.")
    parser.add_argument("--target-dir", required=True, type=Path, help="Target directory for the workspace")
    parser.add_argument("--title", required=True, type=str, help="Research objective title")
    parser.add_argument("--description", required=True, type=str, help="Objective description")
    parser.add_argument("--metric", default="CV Score", help="Primary evaluation metric")
    parser.add_argument("--metric-target", default="Higher is better", help="Target metric threshold")
    parser.add_argument("--validation", default="5-Fold Stratified CV (Leak-Free)", help="Validation strategy")
    parser.add_argument("--orchestrator", default="default", help="Orchestrator profile")
    parser.add_argument("--researcher-1", default="kiza", help="Researcher 1 profile")
    parser.add_argument("--researcher-2", default="kreten", help="Researcher 2 profile")
    parser.add_argument("--experiment-engineer", default="kiza", help="Experiment engineer profile")
    parser.add_argument("--verifier", default="kreten", help="Evidence verifier profile")

    args = parser.parse_args()

    scaffold_workspace(
        target_dir=args.target_dir,
        title=args.title,
        description=args.description,
        metric=args.metric,
        metric_target=args.metric_target,
        validation=args.validation,
        orchestrator=args.orchestrator,
        researcher_1=args.researcher_1,
        researcher_2=args.researcher_2,
        experiment_engineer=args.experiment_engineer,
        verifier=args.verifier,
    )

if __name__ == "__main__":
    main()
