#!/bin/bash

#
# Do basic installation/upgrade/checks
#

HOME=/opt/abcontrol

# Activate venv
cd $HOME
source bin/activate

# todo: check config file

# todo: if becs enabled, check php modules

# todo: check if ablib is installed

# todo: check if emmgr is installed

echo
echo +----------------------------------------------------------------------------+
echo ! Install dependencies                                                       !
echo +----------------------------------------------------------------------------+
cd $HOME
pip3 install -q -r requirements.txt -r docs/requirements.txt

echo
echo +----------------------------------------------------------------------------+
echo ! Perform migrations                                                         !
echo +----------------------------------------------------------------------------+
cd $HOME/app
./manage.py migrate

echo
echo +----------------------------------------------------------------------------+
echo ! Build documentation, make sure this is done before collectstatic           !
echo +----------------------------------------------------------------------------+
cd $HOME/docs
make html

echo
echo +----------------------------------------------------------------------------+
echo ! Collect static files                                                       !
echo +----------------------------------------------------------------------------+
cd $HOME/app
./manage.py collectstatic --no-input

echo
echo +----------------------------------------------------------------------------+
echo ! All done                                                                   !
echo +----------------------------------------------------------------------------+
cd $HOME
