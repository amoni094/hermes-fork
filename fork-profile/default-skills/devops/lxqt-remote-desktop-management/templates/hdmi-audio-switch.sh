#!/bin/bash
# /usr/local/bin/hdmi-audio-switch.sh
# Auto-switch PipeWire audio output between HDMI (TV) and analog (laptop speakers)
# based on current HDMI connection state.
#
# Called by hdmi-display-setup.sh on every HDMI plug/unplug udev event.
# Requires: wpctl (wireplumber), pw-cli (pipewire-bin)
# Does NOT require pactl (not installed on Galina's machine).
#
# Profile index reference (HDA Intel PCH, alsa_card.pci-0000_00_1b.0):
#   1 = analog-stereo+input:analog-stereo  (laptop speakers, default)
#   3 = output:hdmi-stereo+input:analog-stereo  (TV via HDMI)
# Index 3 works even when WirePlumber marks it 'available: no'.

HDMI_STATUS=$(cat /sys/class/drm/card0-HDMI-A-1/status 2>/dev/null || echo disconnected)

GALINA_UID=$(id -u galina)
export XDG_RUNTIME_DIR=/run/user/$GALINA_UID
export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus

run_as_galina() {
    sudo -u galina XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS "$@"
}

# Get wpctl status as plain ASCII (strip UTF-8 box-drawing chars that break awk)
get_status() {
    run_as_galina wpctl status 2>/dev/null | LC_ALL=C sed 's/[^[:print:] ]//g'
}

# Isolate only the Audio Sinks block (stops at Sources: to avoid cross-section leakage)
get_sinks_block() {
    get_status | awk '/^Audio/{in_audio=1} in_audio && /Sinks:/{in_sinks=1; next} in_sinks && /Sources:/{exit} in_sinks{print}'
}

# Get the Built-in Audio card device ID from the Devices section
get_card_id() {
    get_status | awk '/^Audio/{in_audio=1} in_audio && /Devices:/{in_dev=1; next} in_dev && /Sinks:/{exit} in_dev{print}' \
        | grep 'Built-in Audio' | grep -oP '^\s+\K[0-9]+' | head -1
}

get_hdmi_sink_id() {
    get_sinks_block | grep -i 'HDMI' | grep -oP '[*\s]+\K[0-9]+' | head -1
}

get_analog_sink_id() {
    get_sinks_block | grep -i 'Analog Stereo' | grep -oP '[*\s]+\K[0-9]+' | head -1
}

if [ "$HDMI_STATUS" = "connected" ]; then
    echo "HDMI connected -- switching to HDMI audio profile"

    CARD_ID=$(get_card_id)
    echo "Card device ID: $CARD_ID"

    if [ -n "$CARD_ID" ]; then
        run_as_galina wpctl set-profile "$CARD_ID" 3
        sleep 1
    fi

    HDMI_SINK=$(get_hdmi_sink_id)
    echo "HDMI sink ID: $HDMI_SINK"

    if [ -n "$HDMI_SINK" ]; then
        run_as_galina wpctl set-default "$HDMI_SINK"
        run_as_galina wpctl set-volume "$HDMI_SINK" 1.0
        echo "Audio default set to HDMI sink $HDMI_SINK"
    else
        echo "Warning: HDMI sink not found after profile switch"
    fi

else
    echo "HDMI disconnected -- switching to analog audio"

    CARD_ID=$(get_card_id)
    echo "Card device ID: $CARD_ID"

    if [ -n "$CARD_ID" ]; then
        run_as_galina wpctl set-profile "$CARD_ID" 1
        sleep 1
    fi

    ANALOG_SINK=$(get_analog_sink_id)
    echo "Analog sink ID: $ANALOG_SINK"

    if [ -n "$ANALOG_SINK" ]; then
        run_as_galina wpctl set-default "$ANALOG_SINK"
        echo "Audio default set to analog sink $ANALOG_SINK"
    else
        echo "Warning: Analog sink not found after profile switch"
    fi
fi
