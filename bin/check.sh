#!/bin/sh

case "$CONDA_PREFIX" in
  */scyjava-dev)
    ;;
  *)
    echo "Please run 'make setup' and then 'mamba activate scyjava-dev' first."
    exit 1
    ;;
esac
