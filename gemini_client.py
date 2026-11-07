#!/usr/bin/env python3
"""
gemini_client.py — Official Gemini CLI Client with Cloud Ollama Routing.
========================================================================
Manages LLM execution using:
  1. Primary: Cloud Ollama endpoint.
  2. Fallback: Official Gemini CLI (/home/kizamladjanijebac/.npm-global/bin/gemini)
     with model `gemini-3.5-flash-lite`.
"""

import os
import sys
import time
import logging
import subprocess
import shutil
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

logger = logging.getLogger("GeminiClient")


@dataclass
class LLMResponse:
    text: str
    provider: str               # "antigravity_cli" | "ollama_cloud" | "gemini_cli"
    model: str                  # stvarni model koji je odgovorio
    account: Optional[str]      # stvarni nalog
    latency_seconds: float      # izmerena latencija
    fallback_chain: List[str]   # eventualni padovi
    exit_code: int = 0

GEMINI_BIN = os.getenv(
    "GEMINI_BIN",
    shutil.which("gemini") or "/home/kizamladjanijebac/.npm-global/bin/gemini"
)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


def query_gemini_cli(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    timeout: int = 120,
) -> str:
    """
    Executes a query via the official Gemini CLI in headless mode (-p) inside a sandbox.
    Model is strictly gemini-3.5-flash-lite.
    """
    if not os.path.exists(GEMINI_BIN):
        raise FileNotFoundError(f"Gemini CLI binarni fajl nije pronađen na {GEMINI_BIN}")

    full_prompt = f"Instrukcija: {system}\n\nZadatak: {prompt}" if system else prompt
    use_model = model or GEMINI_MODEL

    cmd = [
        GEMINI_BIN,
        "-s",
        "-p", full_prompt,
        "-y",
        "-o", "text",
        "-m", use_model,
    ]

    # Postavljanje čistog sandbox okruženja za Gemini CLI
    sandbox_env = os.environ.copy()
    sandbox_env["SANDBOX"] = "1"
    sandbox_env["GEMINI_CLI_NO_RELAUNCH"] = "true"
    sandbox_env["TERM"] = "dumb"

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd(),
            env=sandbox_env,
        )
        output = result.stdout.strip()
        if output:
            # Clean possible terminal warning lines, hook banners, and extension logs
            noise_prefixes = (
                "Warning:",
                "Skill ",
                "Skill conflict",
                "Invalid hook",
                "Hook system",
                "[cm]",
                "[ExtensionManager]",
                "Blocked dangerous",
                "MCP issues",
                "YOLO mode",
                "Cleanup timed out",
            )
            clean_lines = [
                line for line in output.splitlines()
                if not any(line.startswith(prefix) for prefix in noise_prefixes)
            ]
            cleaned_text = "\n".join(clean_lines).strip()
            if cleaned_text:
                return cleaned_text

        err = result.stderr.strip()
        raise RuntimeError(f"Gemini CLI error (code {result.returncode}): {err}")
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Gemini CLI timed out after {timeout}s")


def query_ollama_cloud(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    timeout: int = 120,
) -> str:
    """
    Executes query against Cloud Ollama endpoint.
    Falls back strictly to Gemini CLI with gemini-3.5-flash-lite if unavailable.
    """
    ollama_api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    ollama_model = model or os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")

    try:
        import httpx
        headers = {}
        ollama_key = os.getenv("OLLAMA_API_KEY")
        if ollama_key:
            headers["Authorization"] = f"Bearer {ollama_key}"

        payload: Dict[str, Any] = {
            "model": ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature}
        }
        if system:
            payload["system"] = system

        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{ollama_api_base}/api/generate",
                json=payload,
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                res = data.get("response", "").strip()
                if res:
                    logger.info(f"Ollama Cloud success | model={ollama_model}")
                    return res
    except Exception as ollama_err:
        logger.warning(f"Ollama Cloud nedostupan ({ollama_err}); prelazim na Gemini CLI ({GEMINI_MODEL})")

    # Fallback to Gemini CLI (gemini-3.5-flash-lite)
    return query_gemini_cli(
        prompt=prompt,
        system=system,
        model=GEMINI_MODEL,
        timeout=timeout
    )


def query_llm_with_lineage(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    timeout: int = 130,
    prefer_agy: bool = True,
    prefer_cloud_ollama: bool = False,
    account: Optional[str] = None,
) -> LLMResponse:
    """
    Unified LLM call returning rich lineage metadata:
      - Tracks actual provider used ('antigravity_cli', 'ollama_cloud', 'gemini_cli')
      - Tracks actual model and account used
      - Measures latency and logs any fallback occurrences
    """
    t0 = time.time()
    fallback_chain: List[str] = []
    use_model = model or "claude-sonnet-4-6"
    selected_account = account or os.getenv("AGY_ACCOUNT", "999@mrcleanervracar.com")

    # Primary: Antigravity CLI (agy)
    if prefer_agy and not prefer_cloud_ollama:
        try:
            from agy_client import query_agy_cli
            res = query_agy_cli(
                prompt=prompt,
                system=system,
                model=use_model,
                account=selected_account,
                timeout=timeout,
            )
            if res and len(res.strip()) > 0:
                latency = round(time.time() - t0, 3)
                logger.info(f"[query_llm_with_lineage] Antigravity agy success | model={use_model} | account={selected_account}")
                return LLMResponse(
                    text=res,
                    provider="antigravity_cli",
                    model=use_model,
                    account=selected_account,
                    latency_seconds=latency,
                    fallback_chain=fallback_chain,
                    exit_code=0
                )
        except Exception as agy_err:
            fallback_chain.append(f"antigravity_cli failed: {agy_err}")
            logger.warning(f"[query_llm_with_lineage] Antigravity agy failed ({agy_err}), falling back to Cloud Ollama...")

    # Fallback 1: Cloud Ollama
    ollama_api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    ollama_model = model if (model and any(k in model.lower() for k in ("gemma", "llama", "qwen", "mistral"))) else os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
    try:
        import httpx
        headers = {}
        ollama_key = os.getenv("OLLAMA_API_KEY")
        if ollama_key:
            headers["Authorization"] = f"Bearer {ollama_key}"

        payload: Dict[str, Any] = {
            "model": ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature}
        }
        if system:
            payload["system"] = system

        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{ollama_api_base}/api/generate",
                json=payload,
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                res = data.get("response", "").strip()
                if res:
                    latency = round(time.time() - t0, 3)
                    logger.info(f"Ollama Cloud success | model={ollama_model}")
                    return LLMResponse(
                        text=res,
                        provider="ollama_cloud",
                        model=ollama_model,
                        account=None,
                        latency_seconds=latency,
                        fallback_chain=fallback_chain,
                        exit_code=0
                    )
    except Exception as ollama_err:
        fallback_chain.append(f"ollama_cloud failed: {ollama_err}")
        logger.warning(f"[query_llm_with_lineage] Ollama failed ({ollama_err}), falling back to Gemini CLI...")

    # Fallback 2: Gemini CLI
    actual_gemini_model = model if (model and "gemini" in model.lower()) else GEMINI_MODEL
    gemini_res = query_gemini_cli(
        prompt=prompt,
        system=system,
        model=actual_gemini_model,
        timeout=timeout,
    )
    latency = round(time.time() - t0, 3)
    return LLMResponse(
        text=gemini_res,
        provider="gemini_cli",
        model=actual_gemini_model,
        account=None,
        latency_seconds=latency,
        fallback_chain=fallback_chain,
        exit_code=0
    )


def query_llm(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    timeout: int = 130,
    prefer_agy: bool = True,
    prefer_cloud_ollama: bool = False,
    account: Optional[str] = None,
) -> str:
    """
    Unified LLM call:
    - Primary: Antigravity CLI (`agy`) using `claude-sonnet-4-6` and account `999@mrcleanervracar.com`.
    - Fallback 1: Cloud Ollama endpoint.
    - Fallback 2: Official Gemini CLI (gemini-3.5-flash-lite).
    """
    resp = query_llm_with_lineage(
        prompt=prompt,
        system=system,
        model=model,
        temperature=temperature,
        timeout=timeout,
        prefer_agy=prefer_agy,
        prefer_cloud_ollama=prefer_cloud_ollama,
        account=account,
    )
    return resp.text


if __name__ == "__main__":
    print(f"Gemini CLI bin: {GEMINI_BIN}")
    print(f"Model: {GEMINI_MODEL}")
