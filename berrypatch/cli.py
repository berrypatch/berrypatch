"""The Berrypatch cli program."""

import coloredlogs
import logging
import click
from . import core
from . import errors


RESOLVER = core.Resolver()


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.pass_context
def cli(ctx, debug):
    coloredlogs.install(level="DEBUG")
    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)


@click.command()
@click.argument("name")
@click.pass_context
def install(ctx, name):
    """Installs an app"""
    click.echo(f"Installing {name} ...")
    try:
        app = RESOLVER.resolve_app(name)
    except errors.AppNotFound:
        click.echo(f'An app named "{name}" was not found')
        return
    app.create_instance({"PORT": 3000})


@click.command()
@click.argument("name")
@click.pass_context
def uninstall(ctx, name):
    """Uninstalls an app"""
    click.echo(f"Uninstalling {name} ...")


@click.command()
@click.argument("name")
@click.pass_context
def start(ctx, name):
    """Starts an app"""
    click.echo(f"Starting {name} ...")
    inst = RESOLVER.get_instance(name)
    inst.start()


@click.command()
@click.argument("name")
@click.pass_context
def stop(ctx, name):
    """Stops an app"""
    click.echo(f"Stopping {name} ...")


@click.command()
@click.argument("name")
@click.pass_context
def status(ctx, name):
    """Show the current status of an app"""
    click.echo(f"Status for {name} ...")


@click.command()
def pluck():
    """Adds a remote application to the local app repo."""
    click.echo("Not implemented")


cli.add_command(install)
cli.add_command(uninstall)
cli.add_command(start)
cli.add_command(stop)
cli.add_command(status)
cli.add_command(pluck)


if __name__ == "__main__":
    cli()
