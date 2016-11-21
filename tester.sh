#!/bin/bash

LOG="$(mktemp)"
make test 2>&1 >$LOG
cat $LOG
grep TOTAL $LOG | awk '{ print "TOTAL: "$4; }'
rm $LOG
