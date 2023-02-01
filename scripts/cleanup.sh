#!/bin/bash
# Quick script to clean up file system

OPWD=$(cd $(dirname $0);pwd)

# log message to stdout
do_log () {
current_datetime=`date`
echo "$current_datetime - $program - $1"
}

do_command () {
do_log "$1"
eval $1
error_code=$?
if [ $error_code -ne 0 ]; then
  do_log "*** ERROR ***, CODE: $error_code in $1"
  exit $error_code
fi
}

do_log "********** Starting Cleaning **********"
do_log "cleaning data..."
do_command "rm -rv ${OPWD}/data/*"
do_log "cleaning charts..."
do_command "rm -rv ${OPWD}/scrips/static/charts/*"
do_log "********** Cleaning Done **********"

