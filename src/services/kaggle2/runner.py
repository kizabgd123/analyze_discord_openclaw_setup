"""
runner.py — Isolated Firejail Execution Runner for S6E11 Multi-Agent System.
=============================================================================
Executes generated code through strict subprocess execution in a Firejail sandbox:
  - Working directory restricted to artifacts/kaggle/s6e11/<run_id>/
  - Minimal explicit environment (env -i style: PATH, LANG, HOME set to run_dir, nothing else)
  - Default-deny filesystem: $HOME hidden via --whitelist:
      * Run directory: whitelisted read-write
      * Data directory: whitelisted read-only (--read-only)
      * Venv directory: whitelisted read-only (--read-only)
      * Sensitive paths: ~/.gemini, ~/.config, ~/.bash_history, other projects, .env DENIED
      * /run/user/ blacklisted (--blacklist=/run/user)
  - Hard containment: --nonewprivs, --caps.drop=all, --seccomp, --noroot, --private-tmp, --quiet, --net=none
  - Fail-closed: Wrong firejail path aborts immediately with no unsandboxed fallback.
  - Process group isolation with hard SIGKILL termination capability.
  - Optional Kaggle kernel submission for heavy compute.
"""

import os
import sys
import json
import signal
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("Kaggle2.Runner")


class LocalRunner:
    """Subprocess runner executing code strictly inside a firejail sandbox."""

    def __init__(
        self,
        run_dir: Path,
        timeout_seconds: int = 600,
        data_dir: Optional[Path] = None,
        venv_dir: Optional[Path] = None,
        folds_file: Optional[Path] = None,
        firejail_path: str = "/usr/bin/firejail",
    ):
        self.run_dir = Path(run_dir)
        self.timeout_seconds = timeout_seconds
        self.data_dir = Path(data_dir) if data_dir else Path("/home/kizamladjanijebac/Desktop/discord-openclaw/artifacts/kaggle/s6e11/data")
        self.venv_dir = Path(venv_dir) if venv_dir else Path("/home/kizamladjanijebac/Desktop/discord-openclaw/runner_venv")
        self.folds_file = Path(folds_file) if folds_file else (self.run_dir / "folds.json")
        self.firejail_path = firejail_path
        self.current_process: Optional[asyncio.subprocess.Process] = None
        self.current_pid: Optional[int] = None
        self._killed_manually: bool = False

    async def execute_script(
        self,
        script_path: Path,
        args: Optional[List[str]] = None,
        verify_oof: bool = True
    ) -> Dict[str, Any]:
        """
        Executes a Python script in a detached process group inside Firejail sandbox.
        Captures output, measures elapsed time, and evaluates verified out-of-fold metrics.
        Fails closed if Firejail is unavailable.
        """
        self.run_dir.mkdir(parents=True, exist_ok=True)
        script_path = Path(script_path)
        if not script_path.is_file():
            return {
                "status": "FAILED",
                "exit_code": 1,
                "cv_score": None,
                "error": f"Script file not found: {script_path}",
                "stdout": "",
                "stderr": f"FileNotFoundError: {script_path}",
                "elapsed_seconds": 0.0
            }

        # FAIL-CLOSED CHECK: Ensure firejail exists and is executable
        firejail_bin = Path(self.firejail_path)
        if not firejail_bin.is_file() or not os.access(firejail_bin, os.X_OK):
            error_msg = (
                f"SecurityError: Firejail executable not found or not executable at '{self.firejail_path}'. "
                f"Unsandboxed execution is strictly prohibited (fail-closed)."
            )
            logger.error(f"[LocalRunner] {error_msg}")
            return {
                "status": "FAILED",
                "exit_code": 127,
                "cv_score": None,
                "error": error_msg,
                "stdout": "",
                "stderr": error_msg,
                "elapsed_seconds": 0.0
            }

        # Determine python executable inside venv or sys.executable
        # Note: Do NOT resolve symlink, so python preserves venv prefix and loads venv site-packages
        if (self.venv_dir / "bin" / "python3").is_file():
            python_bin = str(self.venv_dir / "bin" / "python3")
        elif (self.venv_dir / "bin" / "python").is_file():
            python_bin = str(self.venv_dir / "bin" / "python")
        else:
            python_bin = sys.executable

        # Build Firejail containment command vector (argument vector only, no shell)
        cmd = [
            str(firejail_bin.resolve()),
            "--quiet",
            "--noprofile",
            "--net=none",
            "--nonewprivs",
            "--caps.drop=all",
            "--seccomp",
            "--noroot",
            "--private-tmp",
            "--blacklist=/run/user",
            f"--whitelist={self.run_dir.resolve()}",
        ]

        # Whitelist data directory read-only if it exists
        if self.data_dir.exists():
            cmd.append(f"--whitelist={self.data_dir.resolve()}")
            cmd.append(f"--read-only={self.data_dir.resolve()}")

        # Whitelist venv directory read-only if it exists
        if self.venv_dir.exists():
            cmd.append(f"--whitelist={self.venv_dir.resolve()}")
            cmd.append(f"--read-only={self.venv_dir.resolve()}")

        # Append Python executable, script path, and arguments
        cmd.extend([python_bin, str(script_path.resolve())] + (args or []))

        # Minimal explicit environment (env -i style)
        # PATH, LANG, HOME set to the run folder, nothing else.
        clean_env = {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "LANG": "C.UTF-8",
            "HOME": str(self.run_dir.resolve()),
        }

        log_file = self.run_dir / "execution.log"
        start_time = asyncio.get_event_loop().time()
        self._killed_manually = False

        logger.info(f"[LocalRunner] Sandboxed execution of {script_path.name} in {self.run_dir} (timeout={self.timeout_seconds}s)")

        try:
            # preexec_fn=os.setsid enables killing the entire process group
            self.current_process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.run_dir),
                env=clean_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setsid
            )
            self.current_pid = self.current_process.pid

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    self.current_process.communicate(),
                    timeout=self.timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.warning(f"[LocalRunner] Process {self.current_pid} timed out after {self.timeout_seconds}s. Killing...")
                await self.kill()
                elapsed = asyncio.get_event_loop().time() - start_time
                return {
                    "status": "FAILED",
                    "exit_code": -9,
                    "cv_score": None,
                    "error": f"Execution timed out after {self.timeout_seconds} seconds (SIGKILL applied)",
                    "stdout": "",
                    "stderr": "TimeoutExpired: Process exceeded execution budget",
                    "elapsed_seconds": elapsed
                }

            elapsed = asyncio.get_event_loop().time() - start_time
            stdout_text = stdout_bytes.decode("utf-8", errors="replace")
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")

            # Write combined log
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n--- EXECUTION RUN: {datetime.now(timezone.utc).isoformat()} ---\n")
                f.write(f"STDOUT:\n{stdout_text}\n")
                f.write(f"STDERR:\n{stderr_text}\n")

            stdout_lines = stdout_text.splitlines()
            stderr_lines = stderr_text.splitlines()
            last_stdout = "\n".join(stdout_lines[-50:]) if stdout_lines else ""
            last_stderr = "\n".join(stderr_lines[-50:]) if stderr_lines else ""
            exit_code = self.current_process.returncode if self.current_process else 1
            signal_num = -exit_code if (exit_code is not None and exit_code < 0) else None

            if self._killed_manually:
                return {
                    "status": "FAILED",
                    "exit_code": -9,
                    "signal": 9,
                    "cv_score": None,
                    "fold_scores": {},
                    "error": "Process was terminated manually by Stop signal",
                    "stdout": stdout_text,
                    "stderr": stderr_text or "Process killed by operator",
                    "last_stdout": last_stdout,
                    "last_stderr": last_stderr,
                    "elapsed_seconds": elapsed
                }

            if exit_code != 0:
                err_summary = stderr_text.strip() or stdout_text.strip() or f"Script exited with code {exit_code}"
                return {
                    "status": "FAILED",
                    "exit_code": exit_code,
                    "signal": signal_num,
                    "cv_score": None,
                    "fold_scores": {},
                    "error": err_summary,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "last_stdout": last_stdout,
                    "last_stderr": last_stderr,
                    "elapsed_seconds": elapsed
                }

            if not verify_oof:
                return {
                    "status": "PASSED",
                    "exit_code": exit_code,
                    "signal": None,
                    "cv_score": None,
                    "fold_scores": {},
                    "error": None,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "last_stdout": last_stdout,
                    "last_stderr": last_stderr,
                    "elapsed_seconds": elapsed
                }

            # Score Integrity: Evaluator runs outside sandbox, validates OOF predictions artifact,
            # verifies fold isolation (leakage check), and computes ground-truth ROC AUC deterministically.
            # STDOUT IS COMPLETELY IGNORED FOR SCORING.
            eval_res = await self._evaluate_oof_harness()
            if eval_res.get("status") != "PASSED":
                harness_err = eval_res.get("error", "ScoreIntegrityError: OOF predictions verification failed")
                stdout_errs = [l.strip() for l in stdout_lines if any(k in l.lower() for k in ("error", "exception", "failed", "not found"))]
                combined_err = f"{harness_err} [Stdout notice: {'; '.join(stdout_errs[-3:])}]" if (stdout_errs and not stderr_text.strip()) else harness_err
                return {
                    "status": "FAILED",
                    "exit_code": 1,
                    "signal": None,
                    "cv_score": None,
                    "fold_scores": {},
                    "error": combined_err,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "last_stdout": last_stdout,
                    "last_stderr": last_stderr,
                    "elapsed_seconds": elapsed
                }

            return {
                "status": "PASSED",
                "exit_code": exit_code,
                "signal": None,
                "cv_score": eval_res.get("cv_score"),
                "fold_scores": eval_res.get("fold_scores", {}),
                "error": None,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "last_stdout": last_stdout,
                "last_stderr": last_stderr,
                "elapsed_seconds": elapsed
            }

        except Exception as exc:
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.error(f"[LocalRunner] Unexpected runner error: {exc}")
            return {
                "status": "FAILED",
                "exit_code": 1,
                "cv_score": None,
                "fold_scores": {},
                "error": f"Runner failure: {type(exc).__name__}: {exc}",
                "stdout": "",
                "stderr": str(exc),
                "elapsed_seconds": elapsed
            }
        finally:
            self.current_process = None
            self.current_pid = None

    async def _evaluate_oof_harness(self) -> Dict[str, Any]:
        """
        Executes the fixed out-of-sandbox evaluation harness using runner_venv python.
        Validates OOF predictions, checks fold isolation, and computes ROC AUC directly.
        Completely ignores agent stdout.
        """
        python_bin = str(self.venv_dir / "bin" / "python3")
        if not Path(python_bin).is_file():
            python_bin = sys.executable

        eval_script = Path(__file__).parent / "evaluator.py"
        cmd = [
            python_bin,
            str(eval_script),
            "evaluate",
            "--run-dir", str(self.run_dir),
            "--data-dir", str(self.data_dir),
        ]
        if self.folds_file and Path(self.folds_file).is_file():
            cmd.extend(["--folds-file", str(self.folds_file)])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err_text = stderr.decode(errors="replace").strip() or stdout.decode(errors="replace").strip()
                return {
                    "status": "FAILED",
                    "cv_score": None,
                    "fold_scores": {},
                    "error": f"Evaluator failure (exit {proc.returncode}): {err_text}"
                }
            res = json.loads(stdout.decode(errors="replace").strip())
            return res
        except Exception as exc:
            return {
                "status": "FAILED",
                "cv_score": None,
                "fold_scores": {},
                "error": f"Evaluator execution exception: {exc}"
            }

    async def kill(self) -> bool:
        """Kills the active process group and verifies no leftover PID."""
        if self.current_process and self.current_pid:
            self._killed_manually = True
            pid = self.current_pid
            try:
                pgid = os.getpgid(pid)
                os.killpg(pgid, signal.SIGKILL)
                logger.info(f"[LocalRunner] Sent SIGKILL to process group {pgid} (PID: {pid})")
            except ProcessLookupError:
                pass
            except Exception as e:
                logger.warning(f"Error killing process group {pid}: {e}")

            # Verification: wait briefly and check ps
            await asyncio.sleep(0.2)
            is_dead = not self._check_pid_exists(pid)
            return is_dead
        return True

    @staticmethod
    def _check_pid_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, OSError):
            return False




class KernelRunner:
    """Kaggle Kernel compute runner for heavy GPU jobs."""

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)

    async def push_and_wait(self, kernel_slug: str, poll_interval: int = 15, max_wait: int = 3600) -> Dict[str, Any]:
        """Pushes kernel folder to Kaggle and monitors status until complete."""
        push_cmd = ["kaggle", "kernels", "push", "-p", str(self.run_dir)]
        proc = await asyncio.create_subprocess_exec(*push_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            return {"status": "FAILED", "error": stderr.decode().strip() or stdout.decode().strip()}

        logger.info(f"[KernelRunner] Pushed {kernel_slug}. Polling status...")
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < max_wait:
            status_cmd = ["kaggle", "kernels", "status", kernel_slug]
            sproc = await asyncio.create_subprocess_exec(*status_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            s_out, _ = await sproc.communicate()
            status_text = s_out.decode().strip()

            if "complete" in status_text.lower():
                output_dir = self.run_dir / "output"
                output_dir.mkdir(parents=True, exist_ok=True)
                out_cmd = ["kaggle", "kernels", "output", kernel_slug, "-p", str(output_dir)]
                await asyncio.create_subprocess_exec(*out_cmd)
                return {"status": "PASSED", "message": status_text, "output_dir": str(output_dir)}
            elif "error" in status_text.lower():
                return {"status": "FAILED", "error": f"Kernel execution failed: {status_text}"}

            await asyncio.sleep(poll_interval)

        return {"status": "FAILED", "error": f"Kernel execution timed out after {max_wait}s"}
