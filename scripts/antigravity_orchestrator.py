"""
antigravity_orchestrator.py — Layer A Antigravity Agent Manager Orchestration Engine
==================================================================================
Manages development-layer agents, file ownership enforcement, directory isolation,
and concurrent development task locks.

Layer A Development Agents:
  - frontend-agent
  - backend-agent
  - intercom-agent
  - memory-agent
  - quality-guard

Strict Boundary:
Layer A agents govern repository code and development tasks. They must NEVER
tamper with or overwrite Layer B Kaggle experiment execution artifacts (such as
the frozen Exp 0 baseline or frozen fold assignments).
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

logger = logging.getLogger("Antigravity.Orchestrator")


class AgentPoolManager:
    """Enforces Layer A development agent manifests, file scopes, and coordination locks."""

    def __init__(self, config_path: Optional[Path] = None, stale_lock_seconds: int = 3600):
        self.repo_root = Path(__file__).resolve().parent.parent
        self.config_path = config_path or (self.repo_root / "config" / "antigravity_agent_pool.json")
        self.stale_lock_seconds = stale_lock_seconds
        self.manifest = self._load_manifest()
        self.lock_dir = self.repo_root / self.manifest.get("coordination", {}).get("lock_dir", ".locks")
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def _load_manifest(self) -> Dict[str, Any]:
        if not self.config_path.is_file():
            raise FileNotFoundError(f"Agent pool manifest not found at {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "agents" not in data:
            raise ValueError(f"Invalid manifest: missing 'agents' section in {self.config_path}")
        return data

    def get_agent_names(self) -> List[str]:
        return list(self.manifest.get("agents", {}).keys())

    def validate_file_access(self, agent_name: str, target_paths: List[str]) -> Tuple[bool, List[str]]:
        """
        Validates whether target_paths are allowed for the given Layer A agent.
        Returns (is_valid, list_of_violations).
        """
        agents = self.manifest.get("agents", {})
        if agent_name not in agents:
            return False, [f"Unknown agent: '{agent_name}'. Must be one of {list(agents.keys())}"]

        agent_cfg = agents[agent_name]
        allowed = [p.rstrip("/") for p in agent_cfg.get("allowed_paths", [])]
        forbidden = [p.rstrip("/") for p in agent_cfg.get("forbidden_paths", [])]

        violations = []
        for path_str in target_paths:
            norm_path = os.path.normpath(path_str).lstrip("./")

            # Check explicit forbidden paths first
            is_forbidden = False
            for f_prefix in forbidden:
                if norm_path == f_prefix or norm_path.startswith(f_prefix + "/"):
                    violations.append(f"FORBIDDEN: Path '{path_str}' is explicitly forbidden for agent '{agent_name}' (rule: '{f_prefix}')")
                    is_forbidden = True
                    break

            if is_forbidden:
                continue

            # Check allowed paths
            is_allowed = False
            for a_prefix in allowed:
                if norm_path == a_prefix or norm_path.startswith(a_prefix + "/"):
                    is_allowed = True
                    break

            if not is_allowed:
                violations.append(f"UNAUTHORIZED: Path '{path_str}' is outside allowed scope for agent '{agent_name}'")

        return len(violations) == 0, violations

    def detect_path_collisions(self, agent_a: str, paths_a: List[str], agent_b: str, paths_b: List[str]) -> List[str]:
        """Detects single-writer path collisions between two concurrently operating agents."""
        set_a = {os.path.normpath(p).lstrip("./") for p in paths_a}
        set_b = {os.path.normpath(p).lstrip("./") for p in paths_b}
        common = set_a.intersection(set_b)
        return [f"Collision detected on path '{p}' between '{agent_a}' and '{agent_b}'" for p in sorted(common)]

    def acquire_lock(self, agent_name: str, resource_name: str) -> bool:
        """Acquires a coordination lock for an agent on a specific resource, auto-recovering stale locks."""
        safe_res = resource_name.replace("/", "_").replace("\\", "_")
        lock_file = self.lock_dir / f"{safe_res}.lock"

        if lock_file.exists():
            try:
                # Check for stale lock
                mtime = lock_file.stat().st_mtime
                age = time.time() - mtime
                if age > self.stale_lock_seconds:
                    logger.warning(f"Recovering stale lock on '{resource_name}' (age: {age:.1f}s > {self.stale_lock_seconds}s)")
                    lock_file.unlink()
                else:
                    current_holder = lock_file.read_text(encoding="utf-8").strip()
                    if current_holder != agent_name:
                        logger.warning(f"Lock contention: resource '{resource_name}' held by '{current_holder}', requested by '{agent_name}'")
                        return False
            except Exception as e:
                logger.error(f"Error checking lock {lock_file}: {e}")

        lock_data = {
            "agent": agent_name,
            "resource": resource_name,
            "acquired_at": time.time()
        }
        lock_file.write_text(agent_name, encoding="utf-8")
        return True

    def release_lock(self, agent_name: str, resource_name: str) -> bool:
        """Releases a coordination lock if held by the agent."""
        safe_res = resource_name.replace("/", "_").replace("\\", "_")
        lock_file = self.lock_dir / f"{safe_res}.lock"
        if not lock_file.exists():
            return True
        current_holder = lock_file.read_text(encoding="utf-8").strip()
        if current_holder == agent_name:
            lock_file.unlink()
            return True
        logger.warning(f"Cannot release lock: resource '{resource_name}' held by '{current_holder}', not '{agent_name}'")
        return False

    def verify_hooks(self, agent_name: str) -> Dict[str, Any]:
        """Verifies configured pre/post hooks for an agent."""
        agent_cfg = self.manifest.get("agents", {}).get(agent_name, {})
        hooks = agent_cfg.get("verification_hooks", [])
        return {
            "agent": agent_name,
            "hooks": hooks,
            "ready": len(hooks) > 0
        }


def main():
    parser = argparse.ArgumentParser(description="Antigravity Agent Manager Orchestrator")
    parser.add_argument("--check-access", nargs=2, metavar=("AGENT", "PATH"), help="Check if AGENT has access to PATH")
    parser.add_argument("--list-agents", action="store_true", help="List all registered Layer A agents")
    args = parser.parse_args()

    manager = AgentPoolManager()
    if args.list_agents:
        for name in manager.get_agent_names():
            print(f"- {name}: {manager.manifest['agents'][name]['role']}")
        return

    if args.check_access:
        agent, path = args.check_access
        valid, violations = manager.validate_file_access(agent, [path])
        if valid:
            print(f"ACCESS_GRANTED: Agent '{agent}' authorized for '{path}'")
            sys.exit(0)
        else:
            print(f"ACCESS_DENIED: {violations[0]}")
            sys.exit(1)


if __name__ == "__main__":
    main()
