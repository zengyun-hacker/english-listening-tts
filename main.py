#!/usr/bin/env python3
"""
English Listening Exam TTS — Command Line Interface

Usage examples:
  # Convert a single script file using edge-tts (free, default)
  python main.py convert examples/dialogue.txt

  # Specify output path
  python main.py convert examples/dialogue.txt -o output/unit3.mp3

  # Use OpenAI TTS (requires OPENAI_API_KEY in .env)
  python main.py convert examples/dialogue.txt --provider openai

  # Convert all .txt files in a folder
  python main.py batch examples/ -o output/

  # List available edge-tts voices
  python main.py voices

  # Preview parsed script structure (no audio generated)
  python main.py preview examples/dialogue.txt
"""

import asyncio
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────
# Provider factory
# ─────────────────────────────────────────────

def _make_provider(provider_name: str, model: str = "tts-1-hd", speed: float = 0.95):
    if provider_name == "openai":
        from tts.openai_provider import get_provider
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            click.echo("Error: OPENAI_API_KEY not found. Set it in .env file.", err=True)
            sys.exit(1)
        return get_provider(api_key=api_key, model=model, speed=speed)
    else:
        from tts.edge_provider import get_provider
        return get_provider()


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

@click.group()
def cli():
    """English Listening Exam TTS — convert exam scripts to audio."""
    pass


@cli.command()
@click.argument("script_file", type=click.Path(exists=True))
@click.option("-o", "--output", default=None, help="Output audio file path.")
@click.option(
    "--provider", default=os.getenv("TTS_PROVIDER", "edge"),
    type=click.Choice(["edge", "openai"]),
    show_default=True,
    help="TTS provider: edge (free) or openai.",
)
@click.option("--model", default="tts-1-hd", show_default=True,
              help="OpenAI model: tts-1 or tts-1-hd.")
@click.option("--speed", default=0.95, show_default=True,
              help="Speech speed (OpenAI only, 0.25–4.0).")
@click.option("--voice-a", default=None, help="Voice for first speaker.")
@click.option("--voice-b", default=None, help="Voice for second speaker.")
def convert(script_file, output, provider, model, speed, voice_a, voice_b):
    """Convert a single exam script file to audio."""
    from parser.script_parser import parse_file
    from audio.processor import render_audio

    script = parse_file(script_file)

    # Default output: same name as input, .mp3 extension
    if not output:
        output = str(Path(script_file).with_suffix(".mp3"))
        # Put in output/ directory
        out_dir = Path(os.getenv("OUTPUT_DIR", "output"))
        out_dir.mkdir(exist_ok=True)
        output = str(out_dir / Path(script_file).stem) + ".mp3"

    voice_overrides = {}
    if voice_a:
        voice_overrides["a"] = voice_a
    if voice_b:
        voice_overrides["b"] = voice_b

    tts = _make_provider(provider, model=model, speed=speed)

    click.echo(f"Script:   {script_file}")
    click.echo(f"Title:    {script.title}")
    click.echo(f"Type:     {script.script_type}")
    click.echo(f"Speakers: {script.speakers or ['narrator']}")
    click.echo(f"Provider: {provider}")
    click.echo(f"Output:   {output}")
    click.echo()

    with click.progressbar(length=len(script.segments), label="Synthesizing") as bar:
        last = [0]
        def progress(cur, tot, spk):
            bar.update(cur - last[0])
            last[0] = cur

        asyncio.run(render_audio(script, tts, output, voice_overrides, progress))

    click.echo(f"\nDone! Audio saved to: {output}")


@cli.command()
@click.argument("scripts_dir", type=click.Path(exists=True))
@click.option("-o", "--output-dir", default=None, help="Output directory.")
@click.option(
    "--provider", default=os.getenv("TTS_PROVIDER", "edge"),
    type=click.Choice(["edge", "openai"]),
    show_default=True,
)
@click.option("--model", default="tts-1-hd", show_default=True)
@click.option("--speed", default=0.95, show_default=True)
def batch(scripts_dir, output_dir, provider, model, speed):
    """Convert all .txt script files in a directory."""
    from parser.script_parser import parse_file
    from audio.processor import render_batch

    scripts_path = Path(scripts_dir)
    txt_files = sorted(scripts_path.glob("*.txt"))

    if not txt_files:
        click.echo(f"No .txt files found in {scripts_dir}")
        return

    out_dir = Path(output_dir or os.getenv("OUTPUT_DIR", "output"))
    out_dir.mkdir(parents=True, exist_ok=True)

    tts = _make_provider(provider, model=model, speed=speed)

    pairs = []
    for f in txt_files:
        script = parse_file(str(f))
        out_path = out_dir / (f.stem + ".mp3")
        pairs.append((script, out_path))
        click.echo(f"  {f.name} → {out_path.name}")

    click.echo(f"\nConverting {len(pairs)} files with {provider}...\n")

    def progress(title, cur, tot, spk):
        click.echo(f"  [{title}] {cur}/{tot} — {spk}")

    asyncio.run(render_batch(pairs, tts, progress_callback=progress))
    click.echo(f"\nAll done! Files saved to: {out_dir}")


@cli.command()
@click.argument("script_file", type=click.Path(exists=True))
def preview(script_file):
    """Show parsed structure of a script without generating audio."""
    from parser.script_parser import parse_file

    script = parse_file(script_file)
    click.echo(f"Title:    {script.title}")
    click.echo(f"Type:     {script.script_type}")
    click.echo(f"Speakers: {script.speakers or ['narrator']}")
    click.echo(f"Segments: {len(script.segments)}")
    click.echo()
    click.echo("─" * 60)
    for i, seg in enumerate(script.segments, 1):
        if seg.is_question_marker:
            click.echo(f"  [{i:3d}] *** {seg.text} ***")
        else:
            spk = f"[{seg.speaker}]" if seg.speaker else "[narrator]"
            preview_text = seg.text[:70] + "…" if len(seg.text) > 70 else seg.text
            click.echo(f"  [{i:3d}] {spk:<14} {preview_text}")


@cli.command()
@click.option("--accent", default="us",
              type=click.Choice(["us", "uk", "au", "all"]),
              help="Filter voices by accent.")
def voices(accent):
    """List available edge-tts English voices."""
    async def _list():
        from tts.edge_provider import EdgeTTSProvider
        p = EdgeTTSProvider()
        all_voices = await p.list_voices()
        locale_map = {"us": "en-US", "uk": "en-GB", "au": "en-AU"}
        prefix = locale_map.get(accent, "en-")
        filtered = [v for v in all_voices if v["Locale"].startswith(prefix)]
        click.echo(f"{'Voice Name':<35} {'Locale':<10} {'Gender'}")
        click.echo("─" * 60)
        for v in filtered:
            click.echo(f"{v['ShortName']:<35} {v['Locale']:<10} {v['Gender']}")

    asyncio.run(_list())


if __name__ == "__main__":
    cli()
