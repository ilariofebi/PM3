#!/bin/bash

#Use: pm3_edit.sh <id or process name>

TMPFILE=$(mktemp --suffix=.json)
pm3 dump ${1} -f $TMPFILE
vi $TMPFILE
pm3 load -f $TMPFILE -r