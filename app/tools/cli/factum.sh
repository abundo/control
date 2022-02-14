#!/bin/bash

# Setup python virtual environment
cd /opt/factum
source venv/bin/activate

# run script
cd /opt/factum/app
tools/cli/factum.py $@
