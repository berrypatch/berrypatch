#!/bin/bash
# Berypatch install script.
# Source: https://github.com/berrypatch/berrypatch

set -e

BERRYPATCH_ROOT=/usr/local/Berrypatch

log() {
    echo "--- $@"
}

warning() {
    echo "WARNING: $@"
}

ensure_docker() {
    log "Checking for docker ..."
    if ! [ -x "$(command -v docker)" ]; then
        log "Docker not installed, installing ..."
        curl -sSL https://get.docker.com | sh
        sudo usermod -aG docker $USER
        newgrp docker
    fi

    docker_version=`docker --version`
    if [ $? -ne 0 ]; then
        log "Docker version could not be determined"
    else
        log "Docker version ${docker_version} - great!"
    fi

    log "Testing docker ..."
    docker run hello-world 2>&1 > /dev/null
    log "Docker works!"
}

ensure_python() {
    log "Checking for python ..."
    if ! [ -x "$(command -v python3)" ]; then
        log "Python not installed, installing ..."
        sudo apt-get install -y libffi-dev libssl-dev
        sudo apt-get install -y python3 python3-pip
    fi

    if ! [ -x "$(command -v pyvenv)" ]; then
        log "python3-venv not installed, installing ..."
        sudo apt-get install -y python3-venv
    fi

    python_version=`python3 --version 2>&1`
    if [ $? -ne 0 ]; then
        log "Python3 version could not be determined"
        exit 1
    fi
    log "Python version ${python_version} - great!"
}

ensure_pipx() {
    log "Checking for pipx ..."
    if ! [ -x "$(command -v pipx)" ]; then
        log "Pipx not installed, installing ..."
        sudo pip3 install pipx
    fi
    log "Pipx installed"
}

ensure_git() {
    log "Checking for git ..."
    if ! [ -x "$(command -v git)" ]; then
        log "git not installed, installing ..."
        sudo apt-get install -y git
    fi
    log "Git installed"
}

ensure_docker_compose() {
    log "Checking for docker-compose ..."
    if ! [ -x "$(command -v docker-compose)" ]; then
        log "docker-compose not installed, installing ..."
        sudo apt-get install -y docker-compose
    fi

    docker_compose=`docker-compose --version`
    if [ $? -ne 0 ]; then
        log "docker-compose version could not be determined"
    else
        log "docker-compose version ${docker_compose} - great!"
    fi
}

ensure_all_dependencies() {
    sudo apt-get update
    ensure_docker
    ensure_python
    ensure_pipx
    ensure_git
    ensure_docker_compose
}

setup_vars() {
    DISTRO_NAME=$(lsb_release -s -i 2>/dev/null || echo -n "Unknown")

    if [ "${DISTRO_NAME}" != "Raspbian" ]; then
        warning "Berrypatch is meant to be run on Raspbian, but your distro is '${DISTRO_NAME}'"
        read -p "Proceed anyway? [y/N]: " proceed_str
        proceed_str=${proceed_str:-No}
        case "${proceed_str}" in
            [yY][eE][sS]|[yY])
                true
                ;;
            *)
                log "Exiting."
                exit 1
                ;;
        esac
    fi
}

ensure_path() {
  if ! [ -x "$(command -v bp)" ]; then
      log "bp not in path, updating ~/.bashrc ..."
      echo 'PATH=$PATH:$HOME/.local/bin' >> ~/.bashrc
      . ~/.bashrc
  fi
}

setup_rootdir() {
    if ! [ -e "${BERRYPATCH_ROOT}" ]; then
        log "Creating ${BERRYPATCH_ROOT}"
        sudo mkdir ${BERRYPATCH_ROOT}
        sudo chown $USER ${BERRYPATCH_ROOT}
    fi
}

pipx_install() {
    log "Installing the `bp` tool"
    pipx install git+https://github.com/berrypatch/berrypatch
}

fetch_apps() {
    log "Fetching the application repo"
    bp update
}

do_install() {
    setup_vars
    ensure_all_dependencies

    log "Installing ..."
    setup_rootdir
    ensure_path
    pipx install git+https://github.com/berrypatch/berrypatch
    log "Done!"
}

do_install
