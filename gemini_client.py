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
import logging
import subprocess
import shutil
from typing import Optional, Dict, Any

logger = logging.getLogger("GeminiClient")

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


def query_llm(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    timeout: int = 120,
    prefer_cloud_ollama: bool = True,
) -> str:
    """
    Unified LLM call:
    - Other agents call Cloud Ollama with fallback to Gemini CLI (gemini-3.5-flash-lite).
    """
    if prefer_cloud_ollama:
        return query_ollama_cloud(
            prompt=prompt,
            system=system,
            model=model,
            temperature=temperature,
            timeout=timeout
        )
    return query_gemini_cli(
        prompt=prompt,
        system=system,
        model=model or GEMINI_MODEL,
        timeout=timeout
    )


if __name__ == "__main__":
    print(f"Gemini CLI bin: {GEMINI_BIN}")
    print(f"Model: {GEMINI_MODEL}")
