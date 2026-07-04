"""Standalone ResumeForge features layered on the existing pipeline.

Each module here is a plain, importable function set (no LangGraph state): the
compression receipt, cold-read simulator, resume roaster, and GitHub gap-finder.
They are called from ``app/cli.py`` and can also be reused from the Gradio app.
"""
