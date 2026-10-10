#!/bin/sh
# Run only on the approved Linux server after reviewing deploy/README.md.
set -eu
if [ "$(id -u)" -ne 0 ]; then
    printf '%s\n' 'Run this installer as root on the approved server.' >&2
    exit 1
fi
if [ ! -d /opt/tensorforge/app ] || [ ! -f /opt/tensorforge/artifacts/manifest.json ]; then
    printf '%s\n' 'First upload/extract the release into /opt/tensorforge.' >&2
    exit 1
fi
command -v python3.11 >/dev/null
command -v caddy >/dev/null
if ! id tensorforge >/dev/null 2>&1; then
    useradd --system --home /var/lib/tensorforge --shell /usr/sbin/nologin tensorforge
fi
install -d -m 700 /etc/tensorforge
install -d -m 700 -o tensorforge -g tensorforge /var/lib/tensorforge
python3.11 -m venv /opt/tensorforge/.venv
/opt/tensorforge/.venv/bin/python -m pip install -r /opt/tensorforge/requirements-runtime-lock.txt httpx==0.28.1
for name in api demo caddy; do
    if [ ! -f "/etc/tensorforge/$name.env" ]; then
        install -m 600 "/opt/tensorforge/deploy/$name.env.example" "/etc/tensorforge/$name.env"
    fi
done
install -m 644 /opt/tensorforge/deploy/tensorforge-api.service /etc/systemd/system/tensorforge-api.service
install -m 644 /opt/tensorforge/deploy/tensorforge-demo.service /etc/systemd/system/tensorforge-demo.service
install -d /etc/systemd/system/caddy.service.d
install -m 644 /opt/tensorforge/deploy/caddy-tensorforge.conf /etc/systemd/system/caddy.service.d/tensorforge.conf
systemctl daemon-reload
printf '%s\n' 'Installed. Configure the three /etc/tensorforge/*.env files and review/install the Caddyfile before enabling services.'
