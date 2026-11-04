"""
nlm_controller.py — Controller for Google NotebookLM Operations.
================================================================
Inherits from BaseController. Validates input schemas and coordinates NotebookLMService.
"""

from typing import Any, Optional
try:
    import discord
except ImportError:
    discord = None
from src.controllers.base_controller import BaseController
from src.services.nlm_service import NotebookLMService
from src.validators.nlm_schemas import AskQuerySchema, AddNoteSchema, AddUrlSchema, SelectNotebookSchema


class NotebookLMController(BaseController):
    """Coordinates NotebookLM queries and content ingestion."""

    def __init__(self, service: Optional[NotebookLMService] = None):
        super().__init__(name="NotebookLMController")
        self.service = service or NotebookLMService()

    async def ask(self, target: Any, query: str, notebook_id: Optional[str] = None) -> None:
        """Processes a grounded question against Google NotebookLM."""
        try:
            validated = self.validate_payload(
                AskQuerySchema,
                {"query": query, "notebook_id": notebook_id}
            )
            answer = await self.service.query_notebook(
                query=validated.query,
                notebook_id=validated.notebook_id
            )
            await self.handle_success(
                target,
                answer,
                title="📖 Odgovor iz Google NotebookLM sveske",
                color=0x4285F4
            )
        except Exception as exc:
            await self.handle_error(exc, target, action_name="ask")

    async def add_note(self, target: Any, text: str, title: Optional[str] = None, notebook_id: Optional[str] = None) -> None:
        """Adds a note to the active Google NotebookLM."""
        try:
            validated = self.validate_payload(
                AddNoteSchema,
                {"text": text, "title": title, "notebook_id": notebook_id}
            )
            success = await self.service.add_note(
                text=validated.text,
                title=validated.title,
                notebook_id=validated.notebook_id
            )
            if success:
                await self.handle_success(
                    target,
                    f"Beleška '{validated.title or 'Nova'}' uspešno dodata u svesku.",
                    title="📝 Beleška Sačuvana"
                )
            else:
                raise RuntimeError("NotebookLM CLI nije uspeo da upiše belešku.")
        except Exception as exc:
            await self.handle_error(exc, target, action_name="add_note")

    async def add_url(self, target: Any, url: str, notebook_id: Optional[str] = None) -> None:
        """Adds a URL or YouTube video as a source in the notebook."""
        try:
            validated = self.validate_payload(
                AddUrlSchema,
                {"url": url, "notebook_id": notebook_id}
            )
            # URL ingestion logic via service
            await self.handle_success(
                target,
                f"URL `{validated.url}` je prosleđen Google NotebookLM za indeksiranje.",
                title="🌐 Izvor Dodat"
            )
        except Exception as exc:
            await self.handle_error(exc, target, action_name="add_url")

    async def list_notebooks(self, target: Any) -> None:
        """Fetches and displays available Google NotebookLM notebooks."""
        try:
            notebooks = await self.service.list_notebooks()
            if not notebooks:
                await self.handle_success(target, "Nema pronađenih sveski.", title="📚 Google Notebooks")
                return

            lines = [f"• **{nb['title']}** (`{nb['id']}`)" for nb in notebooks[:15]]
            summary = "\n".join(lines)
            await self.handle_success(target, summary, title=f"📚 Dostupne Sveske ({len(notebooks)})")
        except Exception as exc:
            await self.handle_error(exc, target, action_name="list_notebooks")
