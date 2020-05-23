"""The Berrypatch cli program."""

import coloredlogs
import logging
import click
from . import config
from . import core
from . import errors


CORE = core.Core()


def print_error(msg):
    click.echo(click.style("ERR!", fg="red") + " " + msg)


def print_progress(msg):
    click.echo(click.style("--->", fg="green") + " " + msg)


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.pass_context
def cli(ctx, debug):
    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug
    coloredlogs.install(level="DEBUG" if debug else "INFO")


@click.command()
@click.pass_context
def update(ctx):
    """Pulls latest app definitions"""
    print_progress(f"Updating sources from {config.FARM_BASE_ADDRESS} ...")
    CORE.update()
    print_progress("Done!")


@click.command()
@click.argument("name")
@click.option("--autostart/--no-autostart", default=True)
@click.pass_context
def install(ctx, name, autostart):
    """Installs an app"""
    app = CORE.get_app(name)
    print_progress(f"Installing {name}")
    if not app:
        print_error(f'An app named "{name}" was not found')
        raise click.Abort()

    variables = {}
    print_progress(f"Configuring {name} ...")
    for variable_config in app.iter_variable_definitions():
        name, description, default_value, validator = variable_config
        click.echo(f'{name}: {description or "No description"}')
        value = click.prompt("Enter value", default=default_value)
        variables[name] = value

    click.echo(f"Ready to install {name}.")
    for k, v in variables.items():
        click.echo(f"  {k}: {v}")
    confirmed = click.confirm("Continue?")
    if not confirmed:
        raise click.Abort()
    instance = app.create_instance(variables)
    print_progress("Installed!")
    if not autostart:
        return
    instance.start()


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
    inst = CORE.get_instance(name)
    inst.start()


@click.command()
@click.argument("name")
@click.pass_context
def stop(ctx, name):
    """Stops an app"""
    click.echo(f"Stopping {name} ...")
    inst = CORE.get_instance(name)
    inst.stop()


@click.command()
@click.argument("name")
@click.pass_context
def restart(ctx, name):
    """Restarts an app"""
    click.echo(f"restarting {name} ...")
    inst = CORE.get_instance(name)
    inst.restart()


@click.command()
@click.argument("name")
@click.pass_context
def status(ctx, name):
    """Show the current status of an app"""
    inst = CORE.get_instance(name)
    services = inst.status()
    if not services:
        print_error("No services running")
        return
    for service in services:
        click.echo(f'{service["name"]} - {service["status"]}')


@click.command()
def instances():
    """Shows all installed apps"""
    instances = CORE.list_instances()
    for instance in instances:
        click.echo(f"{instance.app_name}")


@click.command()
@click.argument("name")
def uninstall(name):
    """Uninstall an instance"""
    print_progress(f"Removing instance {name}")
    inst = CORE.get_instance(name)
    if not inst:
        print_error("Not installed")
        raise click.Abort()
    CORE.remove_instance(inst)
    print_progress(f"Uninstalled")


cli.add_command(update)
cli.add_command(install)
cli.add_command(uninstall)
cli.add_command(start)
cli.add_command(stop)
cli.add_command(restart)
cli.add_command(status)
cli.add_command(instances)


if __name__ == "__main__":
    cli()
