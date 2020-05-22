# Berrypatch

Berrypatch makes it easy to setup, monitor, manage, and re-create your own IOT
devices.

## Design Overview

The goal of Berrypatch is to make managing devices like Raspberry Pi as simple, reproducible, and forgettable as possible.

### Goals

* **Run everything in Docker.** Everything we want to run on our IoT devices should run within Docker. There should be no special daemons, additional packages, startup scripts, user and groups, nor permissions needed on our host OS. Service/application authors can leverage Docker registries to distribute "ready to go" builds.
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

Berrypatch creates and manages a filesystem structure. An abbreviated example is shown below:

* `apps/`
  * `local/`
    * `my-app/`
      * `berry.json`
      * `docker-compose.tmpl.yml`
  * `repo/berryfarm/apps/`
    * `another-app/`
      * `berry.json`
      * `docker-compose.tmpl.yml`
* `instances/`
  * `my-app-01/`
    * `berry-meta.json`
    * `docker-compose.yml`
    * `appdata/`

The two major data trees are `apps/` and `instances/`.

* **`apps/`** is where Berrypatch looks for and manages App definitions. Berrypatch supports pulling from a centralized app registry (`repo/berryfarm`), and you can also create and install apps locally (`local`).

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

> **🚨Warning:** Berrypatch is completely experimental right now. Don't depend on it for anything important.

### Developer setup

Clone the repo, and use Pipenv to create a local install:

```
$ cd berrypatch/
$ pipenv install
$ pipenv shell
(berrypatch) $ berrypatch version
🍓Berrypatch v0.0.1
```
