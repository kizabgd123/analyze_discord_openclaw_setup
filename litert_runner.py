#!/usr/bin/env python3
"""
litert_runner.py — Standalone CLI Runner for On-Device LiteRT & Local Agents.
=============================================================================
Runs Antigravity agents directly on-device using local models (.litertlm)
without requiring an active Discord connection or external internet access.
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.litert_agent_service import LiteRTAgentService, LiteRTModelNotFoundError
from src.config.unified_config import config
from google.antigravity import LiteRTBackend


def print_status(service: LiteRTAgentService) -> None:
    """Prints formatted diagnostics of the local LiteRT environment."""
    status = service.check_status()
    print("=" * 65)
    print("⚡ Google AI Edge LiteRT — Lokalni Runtime Status")
    print("=" * 65)
    print(f"• Putanja do modela:       {status['model_path']}")
    print(f"• Model postoji na disku:  {'✅ DA' if status['model_exists'] else '❌ NE'}")
    if status["model_exists"]:
        print(f"• Veličina modela:         {status['model_size_mb']:.2f} MB")
    print(f"• Detektovani backend:     {status['detected_backend'].upper()}")
    print(f"• Spekulativno dekodovanje: {'Uključeno' if status['speculative_decoding'] else 'Isključeno'}")
    print(f"• CLI litert-lm dostupan:  {'✅ DA' if status['litert_cli_available'] else '❌ NE'}")
    print(f"• Registrovani modeli:     {', '.join(status['imported_models']) or '(nema registrovani modela)'}")
    print(f"• Radni prostor:           {status['workspace_dir']}")
    print(f"• Eksterni OpenAI server:  {'Omogućen' if status['local_openai_enabled'] else 'Onemogućen'} ({status['local_openai_base_url']})")
    print("=" * 65)


async def run_single_prompt(
    service: LiteRTAgentService,
    prompt: str,
    system_instructions: str = None,
    workspace_dir: str = None,
    use_external_server: bool = False,
) -> None:
    """Streams token output for a single prompt."""
    print(f"\n🚀 Pokrećem agenta za zadatak: '{prompt}'\n")
    try:
        async for token in service.chat_stream(
            prompt=prompt,
            system_instructions=system_instructions,
            workspace_dir=workspace_dir,
            use_external_server=use_external_server,
        ):
            print(token, end="", flush=True)
        print("\n")
    except LiteRTModelNotFoundError as err:
        print(f"\n❌ Greška: {err}\n", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\n❌ Neočekivana greška tokom izvršavanja: {exc}\n", file=sys.stderr)
        sys.exit(1)


async def run_interactive_loop(
    service: LiteRTAgentService,
    workspace_dir: str = None,
    use_external_server: bool = False,
) -> None:
    """Runs interactive terminal REPL with LiteRTAgent."""
    print("=" * 65)
    print("🤖 Interaktivni LiteRT Agent Terminal (unesite 'exit' ili 'quit' za izlaz)")
    print("=" * 65)

    while True:
        try:
            prompt = input("\n👤 Korisnik: ").strip()
            if not prompt:
                continue
            if prompt.lower() in ("exit", "quit", "q"):
                print("Doviđenja!")
                break

            print("\n🤖 LiteRT Agent: ", end="", flush=True)
            async for token in service.chat_stream(
                prompt=prompt,
                workspace_dir=workspace_dir,
                use_external_server=use_external_server,
            ):
                print(token, end="", flush=True)
            print()
        except (KeyboardInterrupt, EOFError):
            print("\nPrekinuto.")
            break
        except Exception as exc:
            print(f"\n❌ Greška: {exc}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Pokreni on-device Antigravity agente koristeći LiteRT ili lokalne modele."
    )
    parser.add_argument("prompt", nargs="?", default=None, help="Korisnički upit ili zadatak za agenta")
    parser.add_argument("--status", action="store_true", help="Prikaži status lokalnog LiteRT okruženja")
    parser.add_argument("--import-info", action="store_true", help="Prikaži komande za import Gemma 4 modela")
    parser.add_argument("--interactive", "-i", action="store_true", help="Pokreni interaktivni režim rada")
    parser.add_argument("--backend", choices=["auto", "gpu", "cpu", "npu"], default=None, help="Hardverski backend za inferenciju")
    parser.add_argument("--model-path", default=None, help="Putanja do .litertlm datoteke modela")
    parser.add_argument("--workspace", default=None, help="Radni direktorijum za operacije nad fajlovima")
    parser.add_argument("--external", action="store_true", help="Koristi eksterni OpenAI-kompatibilni endpoint (npr. Ollama)")

    args = parser.parse_args()

    # Configure service
    service = LiteRTAgentService()
    if args.backend:
        backend_map = {
            "auto": None,
            "gpu": LiteRTBackend.GPU,
            "cpu": LiteRTBackend.CPU,
            "npu": LiteRTBackend.NPU,
        }
        config.litert.backend = args.backend
    if args.model_path:
        config.litert.model_path = args.model_path
    if args.workspace:
        config.litert.workspace_dir = args.workspace

    if args.status:
        print_status(service)
        return

    if args.import_info:
        print(service.get_import_instructions())
        return

    if args.interactive:
        asyncio.run(run_interactive_loop(
            service=service,
            workspace_dir=args.workspace,
            use_external_server=args.external
        ))
        return

    if args.prompt:
        asyncio.run(run_single_prompt(
            service=service,
            prompt=args.prompt,
            workspace_dir=args.workspace,
            use_external_server=args.external
        ))
        return

    # Default action if no args
    print_status(service)
    print("\nSavet: Pokrenite sa 'python3 litert_runner.py \"Vaš upit\"' ili '--interactive'")


if __name__ == "__main__":
    main()
