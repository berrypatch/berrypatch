import logging
import os
import subprocess
import sys
import json

from . import config
from .errors import FileNotFound, AppNotFound
import jinja2
from jinja2 import Template


logger = logging.getLogger(__name__)


if sys.version_info[0] < 3:
    raise RuntimeError("Python 3 is required.")


class Resolver:
    """Returns `App` instances by examining local repos."""

    def __init__(self):
        self.apps_dir = os.path.abspath(os.path.expanduser(config.APPS_DIR))
        self.instances_dir = os.path.abspath(os.path.expanduser(config.INSTANCES_DIR))
        self.logger = logging.getLogger(__name__)

    def resolve_app(self, app_name):
        logger.debug(f'Searching for "{app_name}" in "{self.apps_dir}"')
        app_dir = os.path.join(self.apps_dir, app_name)
        logger.debug(f'Testing "{app_dir}"')
        if not os.path.isdir(app_dir):
            raise AppNotFound
        return App.load(app_dir)

    def get_instance(self, app_name):
        app = self.resolve_app(app_name)
        app_dir = os.path.join(self.instances_dir, app_name)
        return AppInstance.load(app_dir)


class App:
    """A core, installable "thing" in berrypatch.

    An app consists of the following things, all of which must reside in
    `base_dir`:

      - `berry.json`: The application's definition file. It defines the name
        and description of the application, along with any variables and
        defaults that may appear in the template.

      - `docker-compose.tmpl.yml`: The applications docker-compose file, as a
        jinja2 template.

    Anything else in the directory is allowed, and ignored. For example, it's
    perfectly fine for a Dockerfile to be distributed along with the berry json.

    """

    def __init__(self, name, description, compose_template, variable_definitions):
        self.name = name
        self.description = description
        self.compose_template = compose_template
        self.variable_definitions = variable_definitions

    @classmethod
    def load(cls, base_dir):
        base_dir = os.path.abspath(os.path.expanduser(base_dir))
        if not os.path.isdir(base_dir):
            raise FileNotFound(base_dir)

        berry_json_file = os.path.join(base_dir, "berry.json")
        if not os.path.exists(berry_json_file):
            raise FileNotFound(berry_json_file)

        compose_tmpl_file = os.path.join(base_dir, "docker-compose.tmpl.yml")
        if not os.path.exists(compose_tmpl_file):
            raise FileNotFound(compose_tmpl_file)

        with open(berry_json_file, "r") as fp:
            berry_json = json.loads(fp.read())

        with open(compose_tmpl_file, "r") as fp:
            compose_template = fp.read()

        # TODO(mikey): Everything else in the app dir should be copied over
        # to the instance dir.

        return cls(
            name=berry_json["name"],
            description=berry_json.get("description", ""),
            compose_template=compose_template,
            variable_definitions=berry_json.get("variables", {}),
        )

    def check_instance(self, instance_dir):
        raise NotImplementedError

    def create_instance(self, variables):
        instance_dir = os.path.join(config.INSTANCES_DIR, self.name)
        return AppInstance.create(self, instance_dir, variables)


class AppInstance:
    def __init__(self, app_name, instance_dir, variables):
        self.app_name = app_name
        self.instance_dir = instance_dir
        self.variables = variables
        self.compose_file = os.path.join(self.instance_dir, "docker-compose.yml")
        self.compose_project_name = app_name

    @classmethod
    def load(cls, instance_dir):
        berry_meta_file = os.path.join(instance_dir, "berry-meta.json")
        with open(berry_meta_file, "r") as fp:
            berry_meta = json.loads(fp.read())
        return cls(berry_meta["name"], instance_dir, berry_meta["variables"],)

    @classmethod
    def create(cls, app, instance_dir, variables):
        """Builds the local (filesystem) instance.

        This creates the docker-compose.yml file from its template and
        variable declarations.
        """
        instance_dir = os.path.abspath(os.path.expanduser(instance_dir))
        if not os.path.exists(instance_dir):
            logger.debug(f"Creating instance dir {instance_dir}")
            os.makedirs(instance_dir)
        if not os.path.isdir(instance_dir):
            raise FileNotFound(instance_dir)

        data_dir = os.path.join(instance_dir, "appdata")
        if not os.path.exists(data_dir):
            logger.debug(f"Creating data dir {data_dir}")
            os.makedirs(data_dir)
        if not os.path.isdir(data_dir):
            raise FileNotFound(data_dir)

        context = {}
        context.update(variables)
        context.update(
            {"APPDATA_DIR": data_dir,}
        )
        template_data = render_template(app.compose_template, context)
        compose_file = os.path.join(instance_dir, "docker-compose.yml")
        with open(compose_file, "w") as fp:
            logger.debug(f"Writing compose file {compose_file}")
            fp.write(template_data)

        metadata = {
            "name": app.name,
            "variables": variables,
        }

        berry_meta_file = os.path.join(instance_dir, "berry-meta.json")
        with open(berry_meta_file, "w") as fp:
            logger.debug(f"Writing meta file {berry_meta_file}")
            fp.write(json.dumps(metadata, indent=2))

        return cls.load(instance_dir)

    def check(self):
        """Checks that the instance is installed and up-to-date.

        Returns `True` if everything is in order; returns `False` if `rebuild()`
        would produce changes.
        """
        raise NotImplementedError

    def rebuild(self):
        """Rebuilds the instance."""
        raise NotImplementedError

    def destroy(self):
        """Destroys the instance."""
        raise NotImplementedError

    def start(self):
        """Starts the instance with docker-compose."""
        result = self._run_compose("up", "-d",)
        return result.returncode == 0

    def stop(self):
        self._run_compose("down")

    def kill(self):
        self._run_compose("kill")

    def restart(self):
        self._run_compose("restart")

    def status(self):
        self._run_compose("ps")

    def _run_compose(self, *args, capture=False):
        return run_compose_command(
            self.compose_project_name, self.compose_file, *args, capture=capture,
        )


def run_compose_command(
    project_name, filename, command, *args, capture=True,
):
    """Executes a docker-compose command, returning a `subprocess.CompletedProcess`"""
    command = f'docker-compose -p "{project_name}" -f "{filename}" {command}'
    if args:
        command = command + " " + " ".join(args)
    logger.info("Running command: {}".format(command))
    result = subprocess.run(command, capture_output=capture, shell=True,)
    logger.debug(f"stderr={result.stderr}")
    logger.debug(f"stdout={result.stdout}")
    logger.debug(f"returncode={result.returncode}")
    return result


def validate_compose_file(filename):
    if not os.path.exists(filename):
        raise FileNotFound(filename)

    result = run_compose_command("tmp", filename, "config", "-q")
    return result.returncode == 0


def render_template(template, context):
    loader = jinja2.DictLoader({})
    env = jinja2.Environment(loader=loader, undefined=jinja2.StrictUndefined)
    t = env.from_string(template)
    return t.render(**context)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app = App.load("tmp/apps/sample")
    inst = app.create_instance("tmp/instances/sample")
    inst.create()
    inst.start()
    inst.status()
    inst.restart()
    inst.stop()
