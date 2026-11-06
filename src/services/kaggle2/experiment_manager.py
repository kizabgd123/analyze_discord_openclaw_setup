"""
experiment_manager.py — Immutable Experiment Storage & Manifest Integrity Manager
==================================================================================
Manages immutable experiment directories, atomic writes, cryptographic manifests,
and prevents historical artifact overwrites.
"""

import os
import sys
import json
import shutil
import hashlib
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


def sha256_file(path: Path) -> str:
    """Computes SHA-256 hex digest for a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    """Computes SHA-256 hex digest for a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_atomic(dest_path: Path, content: str) -> None:
    """Writes content to a file atomically via a temporary file."""
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = dest_path.parent
    with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
        tf.write(content)
        temp_path = Path(tf.name)
    shutil.move(temp_path, dest_path)


class ExperimentManager:
    """Manages immutable experiment workspaces and cryptographically verified manifests."""

    def __init__(self, base_artifacts_dir: Optional[Path] = None):
        self.base_dir = Path(base_artifacts_dir) if base_artifacts_dir else (
            Path(__file__).resolve().parent.parent.parent.parent / "artifacts" / "kaggle" / "s6e11"
        )
        self.baseline_dir = self.base_dir / "exp0_baseline"

    def get_repo_commit(self) -> str:
        """Retrieves current git commit hash."""
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(self.base_dir.parent.parent.parent),
                check=False
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return "UNKNOWN_COMMIT"

    def create_experiment_workspace(self, run_id: str, exp_id: str) -> Path:
        """
        Creates a unique, isolated experiment workspace.
        Fails if experiment already completed (immutable storage).
        """
        exp_dir = self.base_dir / run_id / f"exp_{exp_id}"
        if (exp_dir / "manifest.json").is_file() and (exp_dir / "oof.parquet").is_file():
            raise FileExistsError(f"ImmutableStorageViolation: Experiment {exp_dir} has already completed and cannot be overwritten.")
        
        # If targeting baseline directly or exp_id references baseline, raise PermissionError
        if (
            exp_dir.resolve() == self.baseline_dir.resolve()
            or "baseline" in str(exp_dir).lower()
            or "exp0" in str(exp_dir).lower()
            or "baseline" in str(exp_id).lower()
            or str(exp_id) in ("0", "exp0", "0_baseline")
        ):
            raise PermissionError("BaselineModificationError: Exp 0 Baseline is immutable and cannot be overwritten by experiments.")

        exp_dir.mkdir(parents=True, exist_ok=True)
        return exp_dir

    def create_manifest(
        self,
        exp_dir: Path,
        run_id: str,
        exp_id: str,
        parent_exp: str,
        model_script_path: Path,
        folds_file: Path,
        train_data_path: Path,
        config: Dict[str, Any],
        model_identity: str = "LightGBM",
        random_seeds: Optional[List[int]] = None
    ) -> Path:
        """Creates an immutable manifest for an experiment run."""
        exp_dir = Path(exp_dir)
        manifest_file = exp_dir / "manifest.json"
        
        if manifest_file.is_file():
            raise FileExistsError(f"ManifestAlreadyExists: Cannot overwrite manifest at {manifest_file}")

        script_sha = sha256_file(model_script_path) if model_script_path.is_file() else "MISSING"
        folds_sha = sha256_file(folds_file) if folds_file.is_file() else "MISSING"
        train_sha = sha256_file(train_data_path) if train_data_path.is_file() else "MISSING"
        config_sha = sha256_text(json.dumps(config, sort_keys=True))

        manifest = {
            "run_id": run_id,
            "exp_id": exp_id,
            "parent_experiment": parent_exp,
            "repo_commit": self.get_repo_commit(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_code_sha256": script_sha,
            "dataset_identity_hash": train_sha,
            "fold_definition_hash": folds_sha,
            "config_hash": config_sha,
            "random_seeds": random_seeds or [42],
            "model_identity": model_identity,
            "execution_environment": {
                "python_version": sys.version,
                "platform": sys.platform,
                "sandbox": "firejail"
            },
            "status": "INITIALIZED",
            "artifacts": {}
        }

        write_atomic(manifest_file, json.dumps(manifest, indent=2))
        return manifest_file

    def update_manifest_completion(
        self,
        exp_dir: Path,
        exit_status: str,
        exit_code: int,
        artifact_paths: Dict[str, Path]
    ) -> Dict[str, Any]:
        """Updates manifest with completion telemetry and verified artifact hashes."""
        exp_dir = Path(exp_dir)
        manifest_file = exp_dir / "manifest.json"
        if not manifest_file.is_file():
            raise FileNotFoundError(f"ManifestNotFound: {manifest_file}")

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
        manifest["status"] = exit_status
        manifest["exit_code"] = exit_code

        # Record artifact hashes
        art_dict = {}
        for name, p in artifact_paths.items():
            path_obj = Path(p)
            if path_obj.is_file():
                art_dict[name] = {
                    "path": str(path_obj),
                    "size_bytes": path_obj.stat().st_size,
                    "sha256": sha256_file(path_obj)
                }
            else:
                art_dict[name] = {
                    "path": str(path_obj),
                    "size_bytes": 0,
                    "sha256": None,
                    "status": "MISSING"
                }

        manifest["artifacts"] = art_dict
        write_atomic(manifest_file, json.dumps(manifest, indent=2))
        return manifest

    def verify_manifest_integrity(self, exp_dir: Path) -> Dict[str, Any]:
        """
        Verifies that all files declared in the manifest exist on disk and match
        their cryptographic SHA-256 hashes.
        """
        manifest_file = Path(exp_dir) / "manifest.json"
        if not manifest_file.is_file():
            return {"status": "INVALID", "error": "Manifest file missing"}

        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except Exception as e:
            return {"status": "INVALID", "error": f"Manifest JSON corruption: {e}"}

        artifacts = manifest.get("artifacts", {})
        for name, meta in artifacts.items():
            expected_sha = meta.get("sha256")
            actual_path = Path(meta.get("path", ""))
            if not actual_path.is_file():
                return {
                    "status": "INVALID",
                    "error": f"ArtifactMissing: {name} at {actual_path} does not exist"
                }
            if expected_sha and sha256_file(actual_path) != expected_sha:
                return {
                    "status": "INVALID",
                    "error": f"ArtifactHashMismatch: {name} hash does not match manifest"
                }

        return {"status": "PASSED", "manifest": manifest}
