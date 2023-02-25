#!/bin/bash
# Quick script to clean up file system

OPWD=$(cd $(dirname $0)/..;pwd)

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

function cleanFolder(){
  if [ "$(ls -A $1)" ]; then
    do_command "rm -rv $1"
  else
    echo "$1 is empty"
  fi
}

do_log "********** Starting Cleaning **********"
do_log "cleaning data..."
cleanFolder "${OPWD}/data/*"

do_log "cleaning charts..."
cleanFolder "${OPWD}/scripts/static/charts/*"

do_log "cleaning images..."
cleanFolder "${OPWD}/scripts/static/images/*"

do_log "********** Cleaning Done **********"

