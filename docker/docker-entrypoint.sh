#!/usr/bin/env bash

set -e

# Cycle Bluetooth power, which helps with connection issues
bluetoothctl power off
bluetoothctl power on

uv run broadcast_renogy_to_mqtt
