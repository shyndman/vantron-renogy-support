#!/usr/bin/env bash

set -e

source /venv/bin/activate

bluetoothctl power off
bluetoothctl power on

add_discovery_topics
run_renogy_publisher
