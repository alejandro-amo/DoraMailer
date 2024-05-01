#!/bin/sh
# task_runner.sh
# helper script for running Dora mailer tasks from console or cron
# USAGE:
# task_runner.sh TASK
# where task is the name of the task config file in tasks folder, without the .py extension.
cd "$(dirname "$0")" || exit 1
python3 dora_mailer.py "$1" 2>&1 | tee "logs/$1.log"
