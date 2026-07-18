#!/bin/bash

# Start a child sleeping in the background to see what happens when parent is
# terminated.

[ $# -ne 1 ] && echo "Usage: $0 sleep-seconds" && exit 1

sleep "$1" &

echo "Child PID is $!"

echo "Parent is waiting"
wait
echo "Child has finished sleeping - parent exits"
