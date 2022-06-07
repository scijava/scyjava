#!/bin/sh
python -m pytest tests/ -p no:faulthandler $@
