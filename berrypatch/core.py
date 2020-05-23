import logging
import os
import subprocess
import sys
import json
import shutil

from . import config
from .errors import FileNotFound, AppNotFound
import jinja2
from jinja2 import Template


logger = logging.getLogger(__name__)


if sys.version_info[0] < 3:
    raise RuntimeError("Python 3 is required.")


DEFAULT_NETWORK_NAME = "berrypatch"


COMPOSE_FOOTER = f"""
networks:
  default:
    external:
        name: "{DEFAULT_NETWORK_NAME}"
"""


class Resolver:
    """Returns `App` instances by examining local repos."""

    def __init__(self):
        self.apps_dir = os.path.abspath(os.path.expanduser(config.FARM_APPS_DIR))
        self.instances_dir = os.path.abspath(os.path.expanduser(config.INSTANCES_DIR))
        self.logger = logging.getLogger(__name__)

    def iter_apps(self):
        for filename in os.listdir(self.apps_dir):
            if filename.startswith("."):
                continue
            fullpath = os.path.join(self.apps_dir, filename)
            if not os.path.isdir(fullpath):
                continue
            if not os.path.exists(os.path.join(fullpath, "berry.json")):
                continue
            yield App.load(fullpath)

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

    def __init__(self, name, description, compose_template, variable_definitions, data_files):
        self.name = name
        self.description = description
        self.compose_template = compose_template
        self.variable_definitions = variable_definitions
        self.data_files = data_files

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

        data_files = {}
        for src_filename, dest_filename in berry_json.get("data_files", {}).items():
            with open(os.path.join(base_dir, src_filename), "r") as fp:
                file_contents = fp.read()
            data_files[dest_filename] = file_contents

        return cls(
            name=berry_json["name"],
            description=berry_json.get("description", ""),
            compose_template=compose_template,
            variable_definitions=berry_json.get("variables", {}),
            data_files=data_files,
        )

    def iter_variable_definitions(self):
        for var in self.variable_definitions:
            name = var["name"]
            description = var.get("description", "")
            default_value = var.get("default", "")
            validator = lambda v: v
            yield name, description, default_value, validator

    def iter_data_files(self):
        return self.data_files.items()

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
        return cls(berry_meta["name"], instance_dir, berry_meta["variables"])

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
        compose_data = render_template(app.compose_template, context) + COMPOSE_FOOTER
        compose_file = os.path.join(instance_dir, "docker-compose.yml")
        with open(compose_file, "w") as fp:
            logger.debug(f"Writing compose file {compose_file}")
            fp.write(compose_data)

        for relative_filename, contents in app.data_files.items():
            dest_filename = os.path.join(data_dir, relative_filename)
            os.makedirs(os.path.dirname(dest_filename), exist_ok=True)
            logger.debug(f"Installing datafile '{relative_filename}' at '{dest_filename}'")
            with open(dest_filename, "w") as fp:
                fp.write(contents)

        metadata = {
            "name": app.name,
            "variables": variables,
            "data_files": app.data_files,
        }

        berry_meta_file = os.path.join(instance_dir, "berry-meta.json")
        with open(berry_meta_file, "w") as fp:
            logger.debug(f"Writing meta file {berry_meta_file}")
            fp.write(json.dumps(metadata, indent=2))

        instance = cls.load(instance_dir)
        ensure_network(DEFAULT_NETWORK_NAME)
        instance.pull()
        return instance

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
        ensure_network(DEFAULT_NETWORK_NAME)
        result = self._run_compose("up", "-d",)
        return result.returncode == 0

    def stop(self):
        self._run_compose("down")

    def destroy(self):
        self._run_compose("rm", "-v")

    def kill(self):
        self._run_compose("kill")

    def restart(self):
        self._run_compose("restart")

    def pull(self):
        self._run_compose("pull")

    def status(self):
        result = self._run_compose("ps", "-q", capture=True)
        images = result.stdout.decode().splitlines()
        ret = []
        for image_id in images:
            raw_status = run_docker_command("inspect", image_id)
            status = json.loads(raw_status.stdout)[0]
            ret.append(
                {"image": image_id, "status": status["State"]["Status"], "name": status["Name"],}
            )
        return ret

    def _run_compose(self, *args, capture=False):
        return run_compose_command(
            self.compose_project_name, self.compose_file, *args, capture=capture,
        )


class Core:
    def __init__(self):
        self.resolver = Resolver()
        self.instances_dir = config.INSTANCES_DIR

    def list_apps(self, query=None):
        """List all apps the system knows how to install.
        
        If `query` is specified, limit the results to apps with names matching it.
        """
        all_apps = list(self.resolver.iter_apps())
        if query:
            filtered_results = []
            for app in all_apps:
                if query in app.name:
                    filtered_results.append(app)
            return filtered_results
        return all_apps

    def get_app(self, name):
        """Get a single specific App. Returns an `App`, or `None` if not found."""
        all_apps = self.list_apps(query=name)
        for app in all_apps:
            if app.name == name:
                return app
        return None

    def install_app(self, app, variables, instance_id=None):
        """Install a single app."""
        instance_id = self._get_instance_id(instance_id)
        instance_dir = self._get_instance_dir(app, instance_id)
        instance = AppInstance.create(app, instance_dir, variables)
        return instance

    def list_instances(self, query=None, app=None):
        """List all instances, whether or not they are running.

        If `app` is specified, limit the results to apps matching it.
        """
        items = os.listdir(self.instances_dir)
        items = [i for i in items if not i.startswith(".")]
        items = [os.path.join(self.instances_dir, i) for i in items]
        items = [i for i in items if os.path.exists(os.path.join(i, "berry-meta.json"))]
        instances = [AppInstance.load(base_dir) for base_dir in items]
        return instances

    def get_instance(self, app_name, instance_id=None):
        """Gets a specific app instance, or `None` if not found.

        If `instance_id` is specified, look for this specific instance. If unspecified,
        the default instance id will be sought."""
        instances = self.list_instances()
        for instance in instances:
            if instance.app_name == app_name:
                return instance
        return None

    def remove_instance(self, instance):
        """Remove a single instance."""
        instance.stop()
        instance.destroy()
        shutil.rmtree(instance.instance_dir)

    def update(self):
        os.makedirs(config.FARM_ROOT, exist_ok=True)
        git_tree = os.path.join(config.FARM_ROOT, ".git")
        if os.path.exists(git_tree):
            subprocess.run("git pull", cwd=config.FARM_ROOT, capture_output=False, shell=True)
        else:
            subprocess.run(
                f"git clone {config.FARM_GIT_CLONE_URL} {config.FARM_ROOT}",
                cwd=config.FARM_ROOT,
                capture_output=False,
                shell=True,
            )

    def _get_instance_dir(self, app, instance_id):
        instance_id = self._get_instance_id(instance_id)
        return os.path.join(self.instances_dir, f"{app.name}:{instance_id}")

    def _get_instance_id(instance_id):
        if instance_id is None:
            return "default"
        return instance_id


def run_compose_command(
    project_name, filename, command, *args, capture=True,
):
    """Executes a docker-compose command, returning a `subprocess.CompletedProcess`"""
    command = f'docker-compose -p "{project_name}" -f "{filename}" {command}'
    if args:
        command = command + " " + " ".join(args)
    logger.debug("Running command: {}".format(command))
    result = subprocess.run(command, capture_output=capture, shell=True,)
    logger.debug(f"stderr={result.stderr}")
    logger.debug(f"stdout={result.stdout}")
    logger.debug(f"returncode={result.returncode}")
    return result


def run_docker_command(
    command, *args, capture=True,
):
    """Executes a docker-compose command, returning a `subprocess.CompletedProcess`"""
    command = f"docker {command}"
    if args:
        command = command + " " + " ".join(args)
    logger.debug("Running command: {}".format(command))
    result = subprocess.run(command, capture_output=capture, shell=True,)
    logger.debug(f"stderr={result.stderr}")
    logger.debug(f"stdout={result.stdout}")
    logger.debug(f"returncode={result.returncode}")
    return result


def ensure_network(name):
    result = run_docker_command("network", "inspect", name)
    if result.returncode == 0:
        return
    logger.debug(f"Creating network {name}")
    run_docker_command("network", "create", "--driver=bridge", name)


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
