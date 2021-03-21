#!/bin/bash

# Setup python virtual environment
cd /opt/abcontrol
source bin/activate

# run script
cd /opt/abcontrol/app
tools/cli/abcontrol.py $@
