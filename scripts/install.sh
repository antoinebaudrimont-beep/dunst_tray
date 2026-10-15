#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
app_dir="$HOME/.local/opt/dunst-tray"
bin_dir="$HOME/.local/bin"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/dunst-tray"
data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/dunst-tray"
autostart_dir="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"

missing=""
for command_name in python3 dunst dunstctl; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        missing="$missing $command_name"
    fi
done
if ! python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gio, Gtk' >/dev/null 2>&1; then
    missing="$missing python3-gi/gir1.2-gtk-3.0"
fi
if [ -n "$missing" ]; then
    echo "Missing required components:$missing" >&2
    echo "On Debian/MX Linux: sudo apt install dunst python3-gi gir1.2-gtk-3.0" >&2
    exit 1
fi

install -d -m 755 "$app_dir" "$app_dir/src/dunst_tray" "$app_dir/assets" "$app_dir/docs"
install -d -m 755 "$bin_dir" "$config_dir" "$autostart_dir"
install -d -m 700 "$data_dir"

for source_file in "$project_dir"/src/dunst_tray/*.py; do
    install -m 644 "$source_file" "$app_dir/src/dunst_tray/"
done
install -m 644 "$project_dir/pyproject.toml" "$app_dir/pyproject.toml"
install -m 644 "$project_dir/README.md" "$app_dir/README.md"
install -m 644 "$project_dir/CHANGELOG.md" "$app_dir/CHANGELOG.md"
install -m 644 "$project_dir/assets/default-config.ini" "$app_dir/assets/default-config.ini"
install -m 644 "$project_dir/docs/dunst-integration.conf" "$app_dir/docs/dunst-integration.conf"
install -m 755 "$project_dir/assets/dunst-tray.in" "$bin_dir/dunst-tray"

if [ ! -e "$config_dir/config.ini" ]; then
    install -m 600 "$project_dir/assets/default-config.ini" "$config_dir/config.ini"
fi

escaped_bin_dir=$(printf '%s' "$bin_dir" | sed 's/[&|]/\\&/g')
sed "s|@BINDIR@|$escaped_bin_dir|g" "$project_dir/assets/dunst-tray.desktop" \
    > "$autostart_dir/dunst-tray.desktop"
chmod 644 "$autostart_dir/dunst-tray.desktop"

echo "Installed dunst-tray in $app_dir"
echo "Configuration: $config_dir/config.ini"
echo "Autostart: $autostart_dir/dunst-tray.desktop"
echo "Start now with: $bin_dir/dunst-tray"
echo "The existing Dunst configuration was not changed."

