#!/usr/bin/env sh

set -e -o errexit

uv build

LATEST_VERSION=$(basename $(ls -rt dist/*.whl | tail -n 1))

function run_on_pod() {
  if [ $# -lt 1 ]; then
    echo "Usage: run_on_pod <command>"
    return 1
  fi
  if [ $# -eq 1 ]; then
    ssh ubo-development-pod "sudo XDG_RUNTIME_DIR=/run/user/\$(id -u ubo) -u ubo bash -c 'source \$HOME/.profile && source /etc/profile && source /opt/ubo/env/bin/activate && $1'"
    return 0
  fi
  return 1
}

scp dist/$LATEST_VERSION ubo-development-pod:/tmp/

run_on_pod "pip install --upgrade --force-reinstall --no-deps /tmp/$LATEST_VERSION"
