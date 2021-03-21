#!/bin/bash

# Setup python virtual environment
cd /opt/abcontrol
source bin/activate

# run script
cd /opt/abcontrol/app
python3 -u tools/cli/periodic.py
