#!/bin/sh
set -eu

purge=false
if [ "${1:-}" = "--purge" ]; then
    purge=true
elif [ "$#" -gt 0 ]; then
    echo "Usage: $0 [--purge]" >&2
    exit 2
fi

app_dir="$HOME/.local/opt/dunst-tray"
launcher="$HOME/.local/bin/dunst-tray"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/dunst-tray"
data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/dunst-tray"
autostart="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/dunst-tray.desktop"
runtime_dir="${XDG_RUNTIME_DIR:-/tmp}"
lock_file="$runtime_dir/dunst-tray-$(id -u).lock"

if [ -r "$lock_file" ]; then
    tray_pid=$(sed -n '1p' "$lock_file")
    case "$tray_pid" in
        *[!0-9]*|'') tray_pid='' ;;
    esac
    if [ -n "$tray_pid" ] && [ -r "/proc/$tray_pid/cmdline" ]; then
        if tr '\0' ' ' < "/proc/$tray_pid/cmdline" | grep -q 'dunst_tray'; then
            kill -TERM "$tray_pid" 2>/dev/null || true
        fi
    fi
fi

rm -f -- "$launcher" "$autostart" "$lock_file"
if [ "$app_dir" = "$HOME/.local/opt/dunst-tray" ]; then
    rm -rf -- "$app_dir"
fi

if [ "$purge" = true ]; then
    rm -rf -- "$config_dir" "$data_dir"
    echo "Removed application, configuration, and notification history."
else
    echo "Removed application and autostart entry."
    echo "Preserved configuration in $config_dir"
    echo "Preserved private history in $data_dir"
    echo "Run '$0 --purge' to remove those files too."
fi
echo "Dunst was not modified."

