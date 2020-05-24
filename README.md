# Berrypatch

Berrypatch makes it easy to setup, monitor, manage, and re-create your own IOT
devices.

![render1590349877577](https://user-images.githubusercontent.com/390829/82763930-15f40880-9dd9-11ea-9202-ee895b3cece8.gif)


> **🚨Warning:** Berrypatch is completely experimental right now and changing fast. Don't depend on it for anything important!

### Why Berrypatch?

Raspberry Pi's are fun little devices. There's a great community of enthusiast tinkerers building apps for them: Airplane trackers, home automation systems, privacy engines, and the list goes on.

The problem: The way to set up and run these services is fragmented. It often involves manually running `apt-get`; chasing down forum posts to write a config; and other tedium. Yet devices and customizations really don't change all that much. _Can't we make this simpler?_


## Installing Berrypatch

For a quick start, run our simple install script by pasting the following
command into your Raspbian system:


```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/berrypatch/berrypatch/master/install.sh)"
```

The installer will take care of the next steps.

You can see what applications are available with `bp search`:

```
$ bp search
* airconnect
* grafana
* influxdb
* mosquitto
* telegraf
```

Install and automatically launch an application with `bp install`. If the app has configuration options, you'll be prompted to set them.

```
$ bp install grafana
---> Installing grafana
---> Entering configuration for grafana

## PORT
Description: The main port Grafana will run on. The Grafana HTTP
service will be exposed on this port.
Enter value [3000]:

## Configuration Summary
PORT=3000

Look good to you? [Y/n]:
Ready to install! Continue? [Y/n]:
---> Installing grafana
Pulling grafana ... done
---> Launching grafana ...
Creating grafana ... done
---> Success: grafana installed and launched!
```

Check on status of all apps with `bp ps`, and use `bp stop` and `bp start` to manage them later. 

See all available commands with `bp --help`, and get help on any command with `bp <command> --help`.

### What is it doing?

Ultimately what Berrypatch does is create and manage a `docker-compose.yml` file, and wraps the `docker-compose` program through it with a simplified interface.

All Berrypatch state and outputs are stored in a place called `BERRYPATCH_ROOT`. You can use `bp` to find that directory name:

```
$ bp config show BERRYPATCH_ROOT        
/usr/local/Berrypatch
```

See what Berrypatch created for the `grafana` app:
```
$ ls /usr/local/Berrypatch/instances/grafana
appdata
berry-meta.json
docker-compose.yml
```

See what Berrypatch is doing by adding `--debug` to any command, eg `bp --debug install grafana`.


## Internals & Design Overview

The goal of Berrypatch is to make managing devices like Raspberry Pi as simple, reproducible, and forgettable as possible.

### Goals

* **A `homebrew`-like simplicity for distributing and installing services.** Make an install command that _just works_ for a wide variety of applications folks are building for these IoT devices. Support the most common points of configuration and customization.
* **...running everything in Docker.** Everything we want to run on our IoT devices should run within Docker. There should be no special daemons, additional packages, startup scripts, user and groups, nor permissions or tinkering needing on the host OS. Service/application authors can leverage Docker registries to distribute "ready to go" builds.
* **Let `docker-compose` manage everything.** Don't reinvent yet another orchestration tool for starting, stopping, and monitoring sets of services. Let `docker-compose` do the heavy lifting, making the runtime familiar and debuggable for advanced users.
* **Follow "the unix way".** Berrypatch is a low-level tool that should be composable and pluggable into higher-level systems. For example, we could later build a UI or a remote control system atop Berrypatch. 

To achieve this goal, Berrypatch leverages Docker and `docker-compose` heavily. 


### Key concepts

Here are some of the key concepts used within Berrypatch.

* **App**: An app is an installable service or set of services. Each service must be something that can run in Docker, and the set of services must be expressed as a docker-compose file.

* **Instance**: A local installation of an App. Multiple instances of the same App can be installed on a single device, although running more than one instance may not be common.

* **`berry.json`**: A metadata file that describes an installable App. An application author distributes it along with a template docker-compose file. The Berrypatch system uses both to create an _Instance_.

* **`docker-compose.tmpl.yml`**: Just like a normal `docker-compose.yml` file, but supports template substitutions. Any variable declared in `berry.json` can be substituted in when you install an App.


### Filesystem structure

Berrypatch creates and manages a filesystem structure, by default at `/usr/local/Berrypatch` though this can be overridden by specifying `BERRYPATCH_ROOT` in env.

End users should never need to view or manage this tree directly. You can think of this as the private data of the `bp` command, and the place state for installed applications is stored.

An abbreviated example is shown below:

* `sources/`
  * `github.com/berrypatch/berryfarm`
    * `apps`
      * `grafana/`
        * `berry.json`
        * `docker-compose.tmpl.yml`
        * `grafana.conf`
      * `influxdb/`
        * `berry.json`
        * `docker-compose.tmpl.yml`
      * `...`
  * `local/`
    * `apps/`
      * `my-app/`
        * `berry.json`
        * `docker-compose.tmpl.yml`
* `instances/`
  * `my-app-01/`
    * `berry-meta.json`
    * `docker-compose.yml`
    * `appdata/`

The two major data trees are `sources/` and `instances/`.

* **`sources/`** is where Berrypatch looks for and manages App definitions. Berrypatch supports pulling from a centralized app registry (`github.com/berrypatch/berryfarm`), and developers can also create and install app definitions locally (`local`).

* **`instances/`** is where Berrypatch creates applications. Each folder in here corresponds to an instance, and will have a hydrated `docker-compose.yml` within it, as well as a metadata file with information about the install. While you should not _need_ to, you can step inside any instance directory and run `docker-compose` commands just like you may be used to without Berrypatch.

### Variable Definitions

Within a `berry.json` file, an application author may define variables that can be substituted into the docker-compose file when an application is installed. By defining variables explicitly, Berrypatch tools can ensure a valid compose file is generated.

Variable definitions are objects with the following fields:

* `name`: The variable name that will be used in the compose template. This should be a value beginning with a letter and containing only alphanumeric characters and underscores. Example: `USB_DEVICE_NAME`
* `description`: Help text for this variable name. This is a free-form string that will be shown in the berrypatch UI.
* `required`: A boolean indicating whether the user is required to specify this variable.
* `default`: The default value for this variable, if the user does not specify it.
* `type`: The type of the variable value, for basic type check. Options: `string` (default), `boolean`, `number`.

## Getting Started

### Developer setup

Clone the repo, and use Pipenv to create a local install:

```
$ cd berrypatch/
$ pipenv install
$ pipenv shell
(berrypatch) $ berrypatch version
🍓Berrypatch v0.0.1
```
