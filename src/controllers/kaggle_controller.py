#!/usr/bin/env python3
"""
kaggle_controller.py — Dedicated Admin-Only Kaggle Workflow Controller.
======================================================================
Strict Security and Isolation Rules:
  - Admin access is checked via unified_config.admin_user_id with NO hardcoded fallback.
  - Fail-closed: if admin_user_id is None, all calls are rejected.
  - The check runs in the slash command AND inside every UI component callback (View/Button).
  - Validates competition slug with regex ^[a-zA-Z0-9_-]+$.
  - Does NOT execute arbitrary shell commands or submit without explicit user confirmation.
  - Fully decoupled from /debate and !debate flows.
"""

import os
import asyncio
import logging
import discord
from discord import ui, app_commands
from typing import Optional
from pathlib import Path

from src.config.unified_config import unified_config
from src.services.kaggle_service import kaggle_service, KaggleCLIError

logger = logging.getLogger("KaggleController")


def check_admin_auth(user_or_interaction) -> bool:
    """Verifies that caller is the configured admin with zero fallback."""
    admin_id = getattr(unified_config.discord, "admin_user_id", None) if unified_config.discord else None
    if admin_id is None:
        logger.warning("Admin authorization failed: unified_config.discord.admin_user_id is unset.")
        return False

    if hasattr(user_or_interaction, "user"):
        caller_id = getattr(user_or_interaction.user, "id", None)
    elif hasattr(user_or_interaction, "author"):
        caller_id = getattr(user_or_interaction.author, "id", None)
    else:
        caller_id = getattr(user_or_interaction, "id", None)

    if caller_id is None or str(caller_id) != str(admin_id):
        logger.warning(
            f"Admin authorization rejected: caller {caller_id} != configured admin {admin_id}"
        )
        return False

    return True


class KaggleControlView(ui.View):
    """Action Row for Kaggle Workflow with mandatory admin check on every callback."""

    def __init__(self, competition: str, timeout: float = 1800.0):
        super().__init__(timeout=timeout)
        self.competition = competition

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Enforces admin authorization for every button, menu or modal interaction."""
        if not check_admin_auth(interaction):
            msg = "⛔ Pristup odbijen: Samo autorizovani administrator može upravljati Kaggle tokom."
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
            return False
        return True

    @ui.button(label="Osveži Telemetriju", style=discord.ButtonStyle.secondary, emoji="📊", custom_id="kaggle_refresh")
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            ctx = await kaggle_service.get_competition_context(self.competition)
            embed = discord.Embed(
                title=f"📊 KAGGLE TELEMETRIJA: {self.competition}",
                description=ctx.summary_markdown,
                color=0x20BEFF,
            )
            embed.set_footer(text=f"Preostalo danas: {ctx.remaining_today} • Verified CLI")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Greška pri osvežavanju: {e}", ephemeral=True)

    @ui.button(label="Zaustavi Tok", style=discord.ButtonStyle.danger, emoji="🛑", custom_id="kaggle_stop")
    async def stop_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            f"🛑 Kaggle workflow za `{self.competition}` je zaustavljen od strane administratora.",
            ephemeral=False,
        )
        self.stop()


class KaggleActionView(ui.View):
    """Interactive control for remote validation and submission."""

    def __init__(
        self,
        competition: str,
        code_path: str,
        kernel_slug: Optional[str] = None,
        timeout: float = 3600.0,
    ):
        super().__init__(timeout=timeout)
        self.competition = competition
        self.code_path = code_path
        self.kernel_slug = kernel_slug or f"openclaw-{competition}-validation".replace("_", "-")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not check_admin_auth(interaction):
            msg = "⛔ Pristup odbijen: Samo autorizovani administrator može pokrenuti Kaggle akcije."
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
            return False
        return True

    @ui.button(label="Pokreni Validaciju na Kaggle", style=discord.ButtonStyle.primary, emoji="🚀", custom_id="kaggle_run_val")
    async def run_validation_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=False)
        from src.services.kaggle_kernel_service import kaggle_kernel_service, generate_kernel_metadata
        from pathlib import Path
        import json

        try:
            # 1. Check GPU quota
            quota = await kaggle_kernel_service.get_quota()
            gpu_remaining = quota.get("GPU", {}).get("remaining", 0.0)
            if gpu_remaining < 0.5:
                await interaction.followup.send(
                    f"⚠️ **Nedovoljno GPU kvote**: Preostalo samo `{gpu_remaining:.2f}h` GPU vremena. Potrebno je bar 0.5h.",
                    ephemeral=False,
                )
                return

            # 2. Prepare kernel directory and metadata
            comp_dir = Path(self.code_path).parent
            meta = generate_kernel_metadata(
                competition=self.competition,
                kernel_slug=self.kernel_slug,
                code_file=Path(self.code_path).name,
                gpu_type="NvidiaTeslaT4",
            )
            meta_file = comp_dir / "kernel-metadata.json"
            meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

            # 3. Push to Kaggle
            push_res = await kaggle_kernel_service.push_kernel(comp_dir)

            # 4. Notify on Discord
            embed = discord.Embed(
                title=f"🚀 Pokrenuta Kaggle Validacija: {self.kernel_slug}",
                description=(
                    f"📡 **Kernel:** `{meta['id']}`\n"
                    f"⚙️ **GPU Tip:** `{meta['machine_shape']}`\n"
                    f"⏳ **GPU Kvota:** `{gpu_remaining:.2f}h` preostalo ove nedelje\n"
                    f"🌐 **Internet:** `OFFLINE` (striktno pravilo takmičenja)\n\n"
                    f"OpenClaw prati izvršavanje u pozadini..."
                ),
                color=0x20BEFF,
            )
            await interaction.followup.send(embed=embed)

            # 5. Start background watcher task
            asyncio.create_task(
                self._monitor_kernel_lifecycle(interaction.channel, self.competition, self.kernel_slug, comp_dir)
            )

            button.disabled = True
            if hasattr(interaction, "message") and interaction.message:
                await interaction.message.edit(view=self)

        except Exception as exc:
            logger.error(f"Failed to launch Kaggle validation: {exc}", exc_info=True)
            await interaction.followup.send(
                f"❌ Greška pri pokretanju validacije na Kaggle: {exc}", ephemeral=False
            )

    @ui.button(label="Proveri Status", style=discord.ButtonStyle.secondary, emoji="🔍", custom_id="kaggle_status_check")
    async def check_status_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        from src.services.kaggle_kernel_service import kaggle_kernel_service

        try:
            status = await kaggle_kernel_service.get_kernel_status(self.kernel_slug)
            await interaction.followup.send(
                f"📊 **Status kernela `{self.kernel_slug}`:** `{status}`", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Neuspešna provera statusa: {e}", ephemeral=True)

    async def _monitor_kernel_lifecycle(self, channel, competition: str, kernel_slug: str, comp_dir: Path):
        """Monitors running Kaggle kernel until completion, then presents submit action."""
        from src.services.kaggle_kernel_service import kaggle_kernel_service

        max_polls = 60  # 30 minutes at 30s interval
        poll_count = 0

        while poll_count < max_polls:
            await asyncio.sleep(30)
            poll_count += 1
            try:
                status = await kaggle_kernel_service.get_kernel_status(kernel_slug)
                logger.info(f"Polled kernel {kernel_slug}: {status} (attempt {poll_count})")

                if "COMPLETE" in status:
                    output_dir = comp_dir / "output"
                    await kaggle_kernel_service.get_kernel_output(kernel_slug, output_dir)

                    sub_file = output_dir / "submission.parquet"
                    if sub_file.exists():
                        embed = discord.Embed(
                            title=f"✅ Kaggle Validacija Završena: {kernel_slug}",
                            description=(
                                f"🎉 **Izvršavanje uspešno završeno!**\n"
                                f"📁 Izlaz preuzet: `{sub_file}`\n"
                                f"📊 Spreman za zvaničnu submisiju na takmičenje.\n\n"
                                f"Kliknite na dugme ispod za potvrdu submisije."
                            ),
                            color=0x34A853,
                        )
                        submit_view = KaggleSubmitView(
                            competition=competition,
                            kernel_slug=kernel_slug,
                            submission_path=str(sub_file),
                        )
                        await channel.send(embed=embed, view=submit_view)
                    else:
                        await channel.send(
                            f"⚠️ Kernel `{kernel_slug}` je završio, ali `submission.parquet` nije pronađen u `{output_dir}`."
                        )
                    break

                elif "ERROR" in status or "FAILED" in status:
                    await channel.send(f"❌ Kaggle Kernel `{kernel_slug}` je pao sa greškom: `{status}`.")
                    break

            except Exception as err:
                logger.warning(f"Polling error for {kernel_slug} (attempt {poll_count}): {err}")


class KaggleSubmitView(ui.View):
    """Requires explicit admin confirmation before final submission to Kaggle."""

    def __init__(self, competition: str, kernel_slug: str, submission_path: str, timeout: float = 1800.0):
        super().__init__(timeout=timeout)
        self.competition = competition
        self.kernel_slug = kernel_slug
        self.submission_path = submission_path

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not check_admin_auth(interaction):
            msg = "⛔ Pristup odbijen: Samo autorizovani administrator može potvrditi submisiju."
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
            return False
        return True

    @ui.button(label="Potvrdi Submisiju na Kaggle", style=discord.ButtonStyle.success, emoji="🏆", custom_id="kaggle_confirm_submit")
    async def confirm_submit_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=False)
        import hashlib
        from pathlib import Path
        from src.services.kaggle_service import kaggle_service
        from src.services.kaggle_kernel_service import kaggle_kernel_service

        try:
            limits = await kaggle_service.get_submission_limits(self.competition)
            if limits.remaining <= 0:
                await interaction.followup.send(
                    f"⚠️ **Iskorišćen dnevni limit**: Preostalo `0` submisija danas za `{self.competition}`.",
                    ephemeral=False,
                )
                return

            sub_p = Path(self.submission_path)
            if not sub_p.exists():
                await interaction.followup.send(
                    f"❌ Fajl `{self.submission_path}` ne postoji.", ephemeral=False
                )
                return

            sha256 = hashlib.sha256(sub_p.read_bytes()).hexdigest()
            msg = kaggle_kernel_service.sanitize_message(f"OpenClaw {self.kernel_slug} {sha256[:8]}")

            proc = await asyncio.create_subprocess_exec(
                kaggle_kernel_service.kaggle_bin,
                "competitions",
                "submit",
                "-c",
                self.competition,
                "-f",
                str(sub_p),
                "-m",
                msg,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            out_str = stdout.decode().strip() or stderr.decode().strip()

            if proc.returncode != 0:
                raise RuntimeError(f"Submission failed (code {proc.returncode}): {out_str}")

            updated_ctx = await kaggle_service.get_competition_context(self.competition)

            embed = discord.Embed(
                title=f"🎉 Uspešno Podneta Submisija: {self.competition}",
                description=(
                    f"🏆 **Poruka submisije:** `{msg}`\n"
                    f"🔑 **SHA-256:** `{sha256}`\n"
                    f"📋 **Kaggle Odgovor:**\n```{out_str}```\n\n"
                    f"📊 **Ažurirana telemetrija:**\n"
                    f"• Preostalo danas: `{updated_ctx.remaining_today}`\n"
                    f"• Ukupno submisija: `{updated_ctx.total_submissions}`"
                ),
                color=0x34A853,
            )
            await interaction.followup.send(embed=embed)
            button.disabled = True
            if hasattr(interaction, "message") and interaction.message:
                await interaction.message.edit(view=self)

        except Exception as exc:
            logger.error(f"Failed to submit: {exc}", exc_info=True)
            await interaction.followup.send(f"❌ Greška pri submisiji: {exc}", ephemeral=False)


class KaggleController:
    """Manages the lifecycle of /kaggle slash commands."""

    def __init__(self):
        pass

    async def handle_kaggle_start(
        self, interaction: discord.Interaction, competition: str
    ):
        """Initiates the competition debate workflow under strict admin gate."""
        # 1. Slug Validation
        try:
            comp = kaggle_service.validate_slug(competition)
        except ValueError as val_err:
            await interaction.response.send_message(
                f"⚠️ Nevalidan naziv takmičenja: {val_err}", ephemeral=True
            )
            return

        # 2. Admin Check
        if not check_admin_auth(interaction):
            await interaction.response.send_message(
                "⛔ Pristup odbijen: Niste autorizovani admin za /kaggle komande.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        # 3. Live Telemetry Fetch
        try:
            ctx = await kaggle_service.get_competition_context(comp)
        except KaggleCLIError as cli_err:
            await interaction.followup.send(
                f"❌ Greška pri čitanju Kaggle CLI telemetrije: {cli_err}",
                ephemeral=True,
            )
            return

        # 4. Construct Overview Embed
        embed = discord.Embed(
            title=f"🏆 KAGGLE WORKFLOW: {comp}",
            description=(
                f"📊 **Kaggle Telemetrija za `{comp}`**\n"
                f"• Ukupno prethodnih rešenja: `{ctx.total_submissions}`\n"
                f"• Najbolji LB skor: `{ctx.best_score if ctx.best_score is not None else 'Nema'}` "
                f"(datum: `{ctx.best_date or 'N/A'}`)\n"
                f"• Poslednji LB skor: `{ctx.latest_score if ctx.latest_score is not None else 'Nema'}` "
                f"(datum: `{ctx.latest_date or 'N/A'}`)\n"
                f"• Preostalo submisija danas: `{ctx.remaining_today}`\n\n"
                f"⚖️ **Pravilo evaluacije**: Predlog mora biti proveren kroz validaciju, "
                f"ili izričito označen kao `[EKSPERIMENT: <hipoteza>]`.\n\n"
                f"🤖 **Status agenata**: Spremno za pokretanje debate sa filtriranim NotebookLM izvorima."
            ),
            color=0x20BEFF,
        )
        embed.set_footer(text="OpenClaw Kaggle Engine • Admin: Authorized • Zero Mock")

        view = KaggleControlView(competition=comp)
        await interaction.followup.send(embed=embed, view=view)

        # 5. Launch asynchronous grounded debate
        asyncio.create_task(self._run_debate_task(interaction.channel, comp))

    async def handle_kaggle_start_prefix(self, ctx, competition: str):
        """Initiates the competition debate workflow via prefix command (!kaggle start) under strict admin gate."""
        try:
            comp = kaggle_service.validate_slug(competition)
        except ValueError as val_err:
            await ctx.send(f"⚠️ Nevalidan naziv takmičenja: {val_err}")
            return

        if not check_admin_auth(ctx):
            await ctx.send("⛔ Pristup odbijen: Niste autorizovani admin za !kaggle komande.")
            return

        status_msg = await ctx.send(f"⏳ Učitavam Kaggle telemetriju za `{comp}`...")

        try:
            ctx_data = await kaggle_service.get_competition_context(comp)
        except KaggleCLIError as cli_err:
            await ctx.send(f"❌ Greška pri čitanju Kaggle CLI telemetrije: {cli_err}")
            return

        embed = discord.Embed(
            title=f"🏆 KAGGLE WORKFLOW: {comp}",
            description=(
                f"📊 **Kaggle Telemetrija za `{comp}`**\n"
                f"• Ukupno prethodnih rešenja: `{ctx_data.total_submissions}`\n"
                f"• Najbolji LB skor: `{ctx_data.best_score if ctx_data.best_score is not None else 'Nema'}` "
                f"(datum: `{ctx_data.best_date or 'N/A'}`)\n"
                f"• Poslednji LB skor: `{ctx_data.latest_score if ctx_data.latest_score is not None else 'Nema'}` "
                f"(datum: `{ctx_data.latest_date or 'N/A'}`)\n"
                f"• Preostalo submisija danas: `{ctx_data.remaining_today}`\n\n"
                f"⚖️ **Pravilo evaluacije**: Predlog mora biti proveren kroz validaciju, "
                f"ili izričito označen kao `[EKSPERIMENT: <hipoteza>]`.\n\n"
                f"🤖 **Status agenata**: Spremno za pokretanje debate sa filtriranim NotebookLM izvorima."
            ),
            color=0x20BEFF,
        )
        embed.set_footer(text="OpenClaw Kaggle Engine • Admin: Authorized • Zero Mock")

        view = KaggleControlView(competition=comp)
        await status_msg.edit(content=None, embed=embed, view=view)

        asyncio.create_task(self._run_debate_task(ctx.channel, comp))

    async def handle_kaggle_push(self, interaction: discord.Interaction, competition: str):
        """Pushes current pipeline code directly to Kaggle remote compute without running debate."""
        try:
            comp = kaggle_service.validate_slug(competition)
        except ValueError as val_err:
            await interaction.response.send_message(
                f"⚠️ Nevalidan naziv takmičenja: {val_err}", ephemeral=True
            )
            return

        if not check_admin_auth(interaction):
            await interaction.response.send_message(
                "⛔ Pristup odbijen: Niste autorizovani admin za /kaggle push.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=False)
        from src.services.kaggle_kernel_service import kaggle_kernel_service, generate_kernel_metadata
        import json

        comp_dir = Path("/home/kizamladjanijebac/Desktop/discord-openclaw/artifacts/kaggle") / comp
        pipeline_file = comp_dir / "pipeline.py"

        if not pipeline_file.exists():
            await interaction.followup.send(
                f"❌ Pipeline fajl `{pipeline_file}` ne postoji. Prvo pokrenite ili sačuvajte kod.",
                ephemeral=False,
            )
            return

        try:
            quota = await kaggle_kernel_service.get_quota()
            gpu_remaining = quota.get("GPU", {}).get("remaining", 0.0)

            kernel_slug = f"openclaw-{comp}-validation".replace("_", "-")
            meta = generate_kernel_metadata(
                competition=comp,
                kernel_slug=kernel_slug,
                code_file="pipeline.py",
                gpu_type="NvidiaTeslaT4",
            )
            # Ensure local competition sources are clean
            meta["dataset_sources"] = []
            meta["model_sources"] = []

            meta_file = comp_dir / "kernel-metadata.json"
            meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

            push_res = await kaggle_kernel_service.push_kernel(comp_dir)

            action_view = KaggleActionView(competition=comp, code_path=str(pipeline_file), kernel_slug=kernel_slug)

            embed = discord.Embed(
                title=f"🚀 PUSHOVANO NA KAGGLE TRENING/VALIDACIJU: {comp}",
                description=(
                    f"🔗 **URL:** https://www.kaggle.com/code/{meta['id']}\n"
                    f"⚙️ **GPU Akcelerator:** `{meta['machine_shape']}`\n"
                    f"⏳ **GPU Kvota:** `{gpu_remaining:.2f}h` preostalo\n"
                    f"🌐 **Internet:** `OFFLINE` (Pravilo takmičenja)\n\n"
                    f"📡 Status: **KernelWorkerStatus.RUNNING**\n"
                    f"OpenClaw prati izvršavanje u pozadini i ponudiće submisiju kada završi."
                ),
                color=0x20BEFF,
            )
            embed.set_footer(text="OpenClaw Kaggle Engine • Live Compute • Zero Mock")
            await interaction.followup.send(embed=embed, view=action_view)

            asyncio.create_task(
                action_view._monitor_kernel_lifecycle(interaction.channel, comp, kernel_slug, comp_dir)
            )

        except Exception as exc:
            logger.error(f"Kaggle push failed: {exc}", exc_info=True)
            await interaction.followup.send(f"❌ Greška pri pushovanju na Kaggle: {exc}", ephemeral=False)

    async def handle_kaggle_push_prefix(self, ctx, competition: str):
        """Prefix command (!kaggle push) variant for direct push to Kaggle remote compute."""
        try:
            comp = kaggle_service.validate_slug(competition)
        except ValueError as val_err:
            await ctx.send(f"⚠️ Nevalidan naziv takmičenja: {val_err}")
            return

        if not check_admin_auth(ctx):
            await ctx.send("⛔ Pristup odbijen: Niste autorizovani admin za !kaggle push.")
            return

        status_msg = await ctx.send(f"⏳ Pripremam i pushujem kernel za `{comp}` na Kaggle compute...")
        from src.services.kaggle_kernel_service import kaggle_kernel_service, generate_kernel_metadata
        import json

        comp_dir = Path("/home/kizamladjanijebac/Desktop/discord-openclaw/artifacts/kaggle") / comp
        pipeline_file = comp_dir / "pipeline.py"

        if not pipeline_file.exists():
            await status_msg.edit(content=f"❌ Pipeline fajl `{pipeline_file}` ne postoji.")
            return

        try:
            quota = await kaggle_kernel_service.get_quota()
            gpu_remaining = quota.get("GPU", {}).get("remaining", 0.0)

            kernel_slug = f"openclaw-{comp}-validation".replace("_", "-")
            meta = generate_kernel_metadata(
                competition=comp,
                kernel_slug=kernel_slug,
                code_file="pipeline.py",
                gpu_type="NvidiaTeslaT4",
            )
            meta["dataset_sources"] = []
            meta["model_sources"] = []

            meta_file = comp_dir / "kernel-metadata.json"
            meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

            push_res = await kaggle_kernel_service.push_kernel(comp_dir)

            action_view = KaggleActionView(competition=comp, code_path=str(pipeline_file), kernel_slug=kernel_slug)

            embed = discord.Embed(
                title=f"🚀 PUSHOVANO NA KAGGLE TRENING/VALIDACIJU: {comp}",
                description=(
                    f"🔗 **URL:** https://www.kaggle.com/code/{meta['id']}\n"
                    f"⚙️ **GPU Akcelerator:** `{meta['machine_shape']}`\n"
                    f"⏳ **GPU Kvota:** `{gpu_remaining:.2f}h` preostalo\n"
                    f"🌐 **Internet:** `OFFLINE` (Pravilo takmičenja)\n\n"
                    f"📡 Status: **KernelWorkerStatus.RUNNING**\n"
                    f"OpenClaw prati izvršavanje u pozadini i ponudiće submisiju kada završi."
                ),
                color=0x20BEFF,
            )
            embed.set_footer(text="OpenClaw Kaggle Engine • Live Compute • Zero Mock")
            await status_msg.edit(content=None, embed=embed, view=action_view)

            asyncio.create_task(
                action_view._monitor_kernel_lifecycle(ctx.channel, comp, kernel_slug, comp_dir)
            )

        except Exception as exc:
            logger.error(f"Kaggle push failed: {exc}", exc_info=True)
            await status_msg.edit(content=f"❌ Greška pri pushovanju na Kaggle: {exc}")

    async def _run_debate_task(self, channel, comp: str):
        """Executes grounded debate pipeline and posts round-by-round progress to Discord."""
        from src.services.kaggle_debate_service import kaggle_debate_service

        async def on_event(author: str, text: str):
            color = 0x9333EA if "Moderator" in author else 0x20BEFF
            max_chunk = 3800
            chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)] if text else ["(Prazno)"]
            for idx, chunk in enumerate(chunks):
                title = f"🤖 {author}" if idx == 0 else f"🤖 {author} ({idx+1}/{len(chunks)})"
                event_embed = discord.Embed(
                    title=title,
                    description=chunk,
                    color=color,
                )
                event_embed.set_footer(text=f"Kaggle Grounded Debate • {comp}")
                try:
                    await channel.send(embed=event_embed)
                except Exception as e:
                    logger.warning(f"Discord send failed: {e}")

        try:
            res = await kaggle_debate_service.run_debate(comp, on_event_callback=on_event)
            code_path = res.get("code_path")
            if code_path and os.path.exists(code_path):
                file_to_send = discord.File(code_path, filename=f"{comp}_pipeline.py")
                action_view = KaggleActionView(competition=comp, code_path=code_path)
                final_embed = discord.Embed(
                    title=f"✅ Generisan Pipeline Kod za {comp}",
                    description=(
                        f"🔑 **SHA-256:** `{res.get('sha256')}`\n"
                        f"📊 **Status validacije:** `{res.get('status')}`\n"
                        f"🏷️ **Oznaka:** `[EKSPERIMENT]` (čeka pokretanje na Kaggle compute)\n\n"
                        f"Fajl je sačuvan i priložen u poruci.\n"
                        f"Administrator može jednim klikom pokrenuti validaciju na daljinskom Kaggle workeru."
                    ),
                    color=0x34A853,
                )
                await channel.send(embed=final_embed, file=file_to_send, view=action_view)
        except Exception as exc:
            logger.error(f"Kaggle debate workflow error: {exc}", exc_info=True)
            err_embed = discord.Embed(
                title=f"❌ Greška u Kaggle Debati ({comp})",
                description=f"```{str(exc)[:3800]}```",
                color=0xEA4335,
            )
            try:
                await channel.send(embed=err_embed)
            except Exception:
                pass


kaggle_controller = KaggleController()
