"""Entry point for the fylle CLI."""

import click

from fylle_cli.commands import (  # noqa: E402
    validate_cmd,
    inspect_cmd,
    pack_cmd,
    unpack_cmd,
    init_cmd,
    migrate_cmd,
)


@click.group()
@click.version_option(package_name="fylle")
def cli():
    """fylle -- Move AI agents between frameworks without rewriting them."""


cli.add_command(validate_cmd, "validate")
cli.add_command(inspect_cmd, "inspect")
cli.add_command(pack_cmd, "pack")
cli.add_command(unpack_cmd, "unpack")
cli.add_command(init_cmd, "init")
cli.add_command(migrate_cmd, "migrate")
