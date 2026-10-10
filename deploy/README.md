# HTTPS deployment without Docker

This is a prepared **native-source deployment**, not an executed deployment and
not proof of the competition's required identical Docker image. It can provide
a working HTTPS API/demo while Docker verification is deferred. Final same-image
verification remains a later requirement.

Requires an approved Linux server with Python 3.11, systemd, Caddy, a persistent
disk, and two real DNS names pointing to it. No hosting account/server/domain
has been provided and no remote changes were made.

1. Transfer the source release to `/opt/tensorforge` on that server. Keep the
   artifact and manifest together; compare release-manifest SHA256 values.
2. Install Python 3.11/venv and Caddy using the hosting OS's supported packages.
   Caddy's [official service instructions](https://caddyserver.com/docs/running)
   cover systemd setup. This installer assumes those commands already exist.
3. Review and run `sudo sh /opt/tensorforge/deploy/install_native.sh`.
4. Edit `/etc/tensorforge/api.env`, `demo.env`, and `caddy.env` on the server.
   Keep each mode 600. Put API_KEY into the two server-side API/demo env files;
   set a different DEMO_PASSWORD. Set real API_DOMAIN and DEMO_DOMAIN in caddy.env.
   Never paste the evaluation key into this repository or frontend code.
5. Review `/opt/tensorforge/deploy/Caddyfile` and install it as `/etc/caddy/Caddyfile`
   only after reconciling any existing sites. The installer deliberately does not
   overwrite a hosting server's existing Caddyfile.
6. Permit inbound TCP 80/443, keep 8000/8501 private, then start services:

```sh
sudo systemctl enable --now tensorforge-api tensorforge-demo
sudo systemctl restart caddy
```

Caddy reads the domain env file via the provided systemd drop-in. Its
[documented environment substitution](https://caddyserver.com/docs/caddyfile/concepts#environment-variables)
supplies the actual hostnames. Public TLS requires correct DNS and reachability;
the service configuration alone does not demonstrate that TLS works.

7. Inject BACKEND_URL and API_KEY into your local shell and run
   `python -m scripts.smoke_hosted` followed by `python -m scripts.hosted_lifecycle`.
   The lifecycle script creates/deletes its own dedicated disposable jobs only.
8. Verify the model hash/version, hosted prediction consistency, restart behavior
   on the persistent DB, TLS, and evaluation-window availability. Record the
   genuine URLs in docs/submission_manifest.json after successful checks.

One API worker/replica is mandatory. SQLite survives process/service restarts at
`/var/lib/tensorforge/jobs.sqlite3`. Both services are nonroot and keep secrets
out of browser JavaScript. No access-log configuration exposing request headers
is enabled in this Caddyfile.

Deployment status: pending server/domain access. Installer and service files
have not been executed on Linux. Docker requirement remains pending separately.
