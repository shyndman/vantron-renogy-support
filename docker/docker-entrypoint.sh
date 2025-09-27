#!/usr/bin/env bash

set -e

# Cycle Bluetooth power, which helps with connection issues
bluetoothctl power off
bluetoothctl power on

uv run add_discovery_topics
uv run run_renogy_publisher
