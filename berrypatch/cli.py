"""The Berrypatch cli program."""

import coloredlogs
import logging
import click
import json
import os
from . import config as config_lib
from . import core
from . import errors
from .config import NEW_APP_DIR, FARM_BASE_ADDRESS
from .templates import NEW_APP_COMPOSE_TEMPLATE

CORE = core.Core()


def print_error(msg):
    click.echo(click.style("ERR!", fg="red") + " " + msg)


def print_progress(msg):
    click.echo(click.style("--->", fg="green") + " " + msg)


def configure_options(variable_definitions, defaults=None):
    defaults = defaults or {}
    result = {}
    for var in variable_definitions:
        name = var["name"]
        description = var.get("description", "")
        default_value = defaults.get(name, var.get("default", ""))
        validator = lambda v: v

        click.echo(click.style(f"## {name}", bold=True))
        descr_prompt = click.style("Description: ", fg="green") + description or "None provided"
        click.echo(click.wrap_text(descr_prompt))
        value = click.prompt(click.style("Enter value", fg="green"), default=default_value)
        result[name] = value
    return result


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
    if not app.variable_definitions:
        print_progress(f"No configuration required for {name}")
    else:
        print_progress(f"Entering configuration for {name}")
        confirmed = False
        while not confirmed:
            click.echo("")
            variables = configure_options(app.variable_definitions, defaults=variables)
            click.echo("")
            click.echo(click.style("## Configuration Summary", bold=True))
            for k, v in variables.items():
                click.echo(click.style(k) + "=" + click.style(str(v)))
            click.echo("")
            confirmed = click.confirm("Look good to you?", default=True)

    confirmed = click.confirm("Ready to install! Continue?", default=True)
    if not confirmed:
        raise click.Abort()
    print_progress(f"Installing {name}")
    instance = app.create_instance(variables)
    if not autostart:
        print_progress("Installed!")
        return
    print_progress(f"Launching {name} ...")
    instance.start()
    print_progress(f"Success: {name} installed and launched!")


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
@click.argument("name", required=False)
@click.pass_context
def ps(ctx, name):
    """Show the current status of all apps or a single app"""
    if name:
        inst = CORE.get_instance(name)
        if not inst:
            print_error(f"App {name} not installed")
            raise click.Abort()
        instances = [inst]
    else:
        instances = CORE.list_instances()
    for inst in instances:
        click.echo(click.style(inst.app_name, bold=True))
        services = inst.status()
        if not services:
            click.echo(click.style("  [DOWN]", fg="red", bold=True) + " No services running")
        for service in services:
            if service["status"] == "running":
                status = click.style("[UP]", fg="green", bold=True)
            else:
                status = click.style("[??]", fg="orange", bold=True)
            click.echo(f'  {status} {service["name"]} {service["status"]}')


@click.command()
@click.argument("query", required=False)
def search(query):
    """List package(s) matching a name or query"""
    apps = CORE.list_apps(query=query)
    if not apps:
        click.echo("No apps found")
        return
    app_names = sorted([(app.name, app) for app in apps])
    for name, app in app_names:
        click.echo(f"* {click.style(name, bold=True)}")
        click.echo(f"  {click.style(app.description, dim=True)}")


@click.command()
def installed():
    """Shows all installed apps"""
    instances = CORE.list_instances()
    app_names = sorted([i.app_name for i in instances])
    for name in app_names:
        click.echo(f"* {click.style(name, bold=True)}")


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


@click.group()
@click.pass_context
def dev(ctx):
    """Commands for Berrypatch developers"""
    pass


@click.command()
@click.argument("name")
def mkapp(name):
    """Create a new skeletal app"""
    print_progress(f'Creating new app "{name}"')
    location = click.prompt("Location", default=NEW_APP_DIR)
    app_dir = os.path.join(location, name)

    if os.path.exists(app_dir):
        print_error("App dir already exists; pick a new name or location and try again")
        raise click.Abort()

    service_name = click.prompt("Service name", default=name)
    base_image = click.prompt("Base docker image")
    description = click.prompt("Description", default=f"The {name} service")
    ready = click.confirm("Ready to create?")

    if not ready:
        raise click.Abort()

    print_progress(f'Building app dir "{app_dir}"')
    os.makedirs(app_dir)

    print_progress("Creating berry.json")
    data = {
        "name": name,
        "description": description,
        "variables": [],
    }
    with open(os.path.join(app_dir, "berry.json"), "w") as fp:
        fp.write(json.dumps(data, indent=4))

    print_progress("Creating compose template")
    data = NEW_APP_COMPOSE_TEMPLATE.format(**locals())
    with open(os.path.join(app_dir, "docker-compose.tmpl.yml"), "w") as fp:
        fp.write(data)
    print_progress("Done!")


@click.group()
@click.pass_context
def config(ctx):
    """View configuration info"""
    pass


@click.command()
@click.argument("name")
def show(name):
    """Show a config value."""
    val = getattr(config_lib, name.upper(), None)
    if not val:
        raise click.Abort(f"No config value named {name}")
    click.echo(val)


cli.add_command(install)
cli.add_command(installed)
cli.add_command(ps)
cli.add_command(restart)
cli.add_command(search)
cli.add_command(start)
cli.add_command(stop)
cli.add_command(uninstall)
cli.add_command(update)

cli.add_command(dev)
dev.add_command(mkapp)

cli.add_command(config)
config.add_command(show)

if __name__ == "__main__":
    cli()
