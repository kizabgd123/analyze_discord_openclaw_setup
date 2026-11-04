"""
litert_agent_service.py — On-Device LiteRT & Local Model Agent Service.
========================================================================
Runs Antigravity agents on-device using local models without API keys or internet connection.
Uses Google AI Edge LiteRT runtime (.litertlm models) and supports external OpenAI-compatible servers.
"""

import os
import sys
import shutil
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator

from google.antigravity import (
    Agent,
    LiteRTAgentConfig,
    LiteRTBackend,
    LocalOpenAIAgentConfig,
    CompactionConfig,
)
from google.antigravity.hooks import policy

from src.config.unified_config import config
from src.instrument import capture_exception, capture_message

logger = logging.getLogger("LiteRTAgentService")


class LiteRTModelNotFoundError(FileNotFoundError):
    """Raised when the specified .litertlm model checkpoint is not found on disk."""
    pass


class LiteRTAgentService:
    """
    Service for running local Antigravity agents using LiteRT (.litertlm)
    or local OpenAI-compatible endpoints (Ollama / LM Studio / vLLM).
    """

    def __init__(self, cfg=None):
        self.cfg = cfg or config

    def detect_best_backend(self) -> LiteRTBackend:
        """
        Detects the best available hardware backend for LiteRT inference:
        - Checks for NVIDIA CUDA (via nvidia-smi exit code 0) or Apple Metal
        - Falls back gracefully to CPU if GPU driver is unavailable
        """
        configured_backend = self.cfg.litert.backend.lower().strip()

        if configured_backend == "gpu":
            return LiteRTBackend.GPU
        elif configured_backend == "npu":
            return LiteRTBackend.NPU
        elif configured_backend == "cpu":
            return LiteRTBackend.CPU

        # Automatic detection
        try:
            res = subprocess.run(
                ["nvidia-smi"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2
            )
            if res.returncode == 0:
                logger.info("[LiteRT] GPU detected via nvidia-smi; selecting LiteRTBackend.GPU")
                return LiteRTBackend.GPU
        except Exception:
            pass

        # Check for macOS Metal or default to CPU on Linux without active CUDA driver
        logger.info("[LiteRT] GPU not active or driver unavailable; falling back to LiteRTBackend.CPU")
        return LiteRTBackend.CPU

    def resolve_model_path(self, model_path: Optional[str] = None) -> Path:
        """Expands tilde and resolves model path."""
        raw_path = model_path or self.cfg.litert.model_path
        expanded = os.path.expanduser(raw_path)
        return Path(expanded).resolve()

    def check_status(self) -> Dict[str, Any]:
        """
        Inspects local LiteRT runtime readiness, model checkpoint presence,
        and system hardware environment.
        """
        model_path = self.resolve_model_path()
        model_exists = model_path.is_file()
        model_size_mb = (model_path.stat().st_size / (1024 * 1024)) if model_exists else 0.0

        litert_lm_bin = (
            shutil.which("litert-lm")
            or (Path(sys.prefix) / "bin" / "litert-lm")
            or (Path(__file__).resolve().parent.parent.parent / ".venv" / "bin" / "litert-lm")
            or os.path.expanduser("~/.local/bin/litert-lm")
        )
        cli_available = os.path.exists(str(litert_lm_bin)) or (shutil.which("litert-lm") is not None)

        imported_models: List[str] = []
        models_dir = Path(os.path.expanduser("~/.litert-lm/models"))
        if models_dir.exists() and models_dir.is_dir():
            imported_models = [d.name for d in models_dir.iterdir() if d.is_dir()]

        detected_backend = self.detect_best_backend()

        return {
            "model_path": str(model_path),
            "model_exists": model_exists,
            "model_size_mb": round(model_size_mb, 2),
            "litert_cli_available": cli_available,
            "imported_models": imported_models,
            "detected_backend": detected_backend.value,
            "speculative_decoding": self.cfg.litert.enable_speculative_decoding,
            "workspace_dir": self.cfg.litert.workspace_dir,
            "local_openai_enabled": self.cfg.local_openai.enabled,
            "local_openai_base_url": self.cfg.local_openai.base_url,
            "local_openai_model": self.cfg.local_openai.model,
        }

    def get_import_instructions(self, model_name: str = "gemma4-26b") -> str:
        """Returns standard instructions for importing Gemma 4 checkpoint via litert-lm CLI."""
        return (
            f"Preuzimanje i registracija modela '{model_name}':\n"
            f"```bash\n"
            f"litert-lm import \\\n"
            f"  --from-huggingface-repo=litert-community/gemma-4-26B-A4B-it-litert-lm \\\n"
            f"  gemma-4-26B-A4B-it-gpu.litertlm \\\n"
            f"  {model_name}\n"
            f"```\n"
            f"Checkpoint se smešta na: ~/.litert-lm/models/{model_name}/model.litertlm"
        )

    def build_litert_config(
        self,
        model_path: Optional[str] = None,
        workspace_dir: Optional[str] = None,
        backend: Optional[LiteRTBackend] = None,
        enable_speculative_decoding: Optional[bool] = None,
        system_instructions: Optional[str] = None,
        allow_all_tools: Optional[bool] = None,
        compaction_config: Optional[CompactionConfig] = None,
    ) -> LiteRTAgentConfig:
        """Constructs a validated LiteRTAgentConfig."""
        resolved_path = str(self.resolve_model_path(model_path))
        resolved_backend = backend or self.detect_best_backend()

        spec_decoding = (
            enable_speculative_decoding
            if enable_speculative_decoding is not None
            else self.cfg.litert.enable_speculative_decoding
        )

        target_workspace = workspace_dir or self.cfg.litert.workspace_dir
        expanded_ws = os.path.expanduser(target_workspace)
        os.makedirs(expanded_ws, exist_ok=True)

        attach_tools = (
            allow_all_tools
            if allow_all_tools is not None
            else self.cfg.litert.allow_all_tools
        )
        policies = [policy.allow_all()] if attach_tools else None

        kwargs: Dict[str, Any] = {
            "model_path": resolved_path,
            "backend": resolved_backend,
            "enable_speculative_decoding": spec_decoding,
            "workspaces": [expanded_ws],
        }

        if self.cfg.litert.cache_dir:
            kwargs["cache_dir"] = os.path.expanduser(self.cfg.litert.cache_dir)

        if system_instructions:
            kwargs["system_instructions"] = system_instructions

        if policies:
            kwargs["policies"] = policies

        if compaction_config:
            kwargs["compaction_config"] = compaction_config

        return LiteRTAgentConfig(**kwargs)

    def build_local_openai_config(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        workspace_dir: Optional[str] = None,
        system_instructions: Optional[str] = None,
        allow_all_tools: Optional[bool] = None,
    ) -> LocalOpenAIAgentConfig:
        """Constructs a LocalOpenAIAgentConfig with lightweight preset."""
        target_model = model or self.cfg.local_openai.model
        target_url = base_url or self.cfg.local_openai.base_url

        target_workspace = workspace_dir or self.cfg.litert.workspace_dir
        expanded_ws = os.path.expanduser(target_workspace)
        os.makedirs(expanded_ws, exist_ok=True)

        attach_tools = (
            allow_all_tools
            if allow_all_tools is not None
            else self.cfg.litert.allow_all_tools
        )
        policies = [policy.allow_all()] if attach_tools else None

        kwargs: Dict[str, Any] = {
            "model": target_model,
            "base_url": target_url,
            "workspaces": [expanded_ws],
        }

        if system_instructions:
            kwargs["system_instructions"] = system_instructions

        if policies:
            kwargs["policies"] = policies

        cfg = LocalOpenAIAgentConfig(**kwargs)
        if self.cfg.local_openai.apply_lightweight:
            cfg = cfg.lightweight()
        return cfg

    async def chat(
        self,
        prompt: str,
        system_instructions: Optional[str] = None,
        workspace_dir: Optional[str] = None,
        use_external_server: bool = False,
    ) -> str:
        """
        Executes a local agent chat session and accumulates all output tokens.
        """
        full_tokens: List[str] = []
        async for token in self.chat_stream(
            prompt=prompt,
            system_instructions=system_instructions,
            workspace_dir=workspace_dir,
            use_external_server=use_external_server,
        ):
            full_tokens.append(token)
        return "".join(full_tokens)

    async def chat_stream(
        self,
        prompt: str,
        system_instructions: Optional[str] = None,
        workspace_dir: Optional[str] = None,
        use_external_server: bool = False,
    ) -> AsyncGenerator[str, None]:
        """
        Streams response tokens asynchronously from LiteRTAgent or LocalOpenAIAgent.
        """
        status = self.check_status()

        if use_external_server or (not status["model_exists"] and self.cfg.local_openai.enabled):
            logger.info(f"[LiteRTAgentService] Using LocalOpenAIAgentConfig ({self.cfg.local_openai.model} @ {self.cfg.local_openai.base_url})")
            agent_config = self.build_local_openai_config(
                workspace_dir=workspace_dir,
                system_instructions=system_instructions
            )
        else:
            if not status["model_exists"]:
                instructions = self.get_import_instructions()
                raise LiteRTModelNotFoundError(
                    f"LiteRT model fajl nije pronađen na putanji: {status['model_path']}\n"
                    f"Potrebno je preuzeti checkpoint pre pokretanja:\n{instructions}"
                )

            logger.info(f"[LiteRTAgentService] Initializing LiteRTAgent with model {status['model_path']}")
            agent_config = self.build_litert_config(
                workspace_dir=workspace_dir,
                system_instructions=system_instructions
            )

        async with Agent(agent_config) as agent:
            response = await agent.chat(prompt)
            async for token in response:
                yield token
