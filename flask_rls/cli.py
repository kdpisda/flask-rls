"""The ``flask rls`` command group."""

from __future__ import annotations

import click
from flask import current_app
from flask.cli import AppGroup

rls_cli = AppGroup("rls", help="flask-rls management commands.")


@rls_cli.command("sql")
@click.option("--table", default=None, help="Only emit DDL for this table.")
def sql_command(table: str | None) -> None:
    """Print the RLS DDL (ENABLE / FORCE / CREATE POLICY) for registered policies."""
    ext = current_app.extensions.get("rls")
    if ext is None:
        raise click.ClickException("flask-rls is not initialized on this application.")

    statements = list(ext.registry.ddl(table))
    if not statements:
        click.echo("-- No RLS policies registered. Use rls.register(table, policy).")
        return
    for statement in statements:
        click.echo(statement)
