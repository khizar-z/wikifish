# Deploying WikiFish On Arch Linux

This guide assumes:

- the app code will live in `/srv/wikifish/app`
- compiled snapshot artifacts will live in `/srv/wikifish/data/current`
- Caddy is already installed and already serving other sites on ports `80` and `443`
- WikiFish will listen only on `127.0.0.1:8050`

## 1. Prepare the server

Install the runtime packages:

```bash
sudo pacman -Syu
sudo pacman -S --needed python python-virtualenv git caddy
```

Create a dedicated service user and directories:

```bash
sudo useradd --system --create-home --home-dir /srv/wikifish --shell /usr/bin/nologin wikifish
sudo mkdir -p /srv/wikifish/data
sudo chown -R wikifish:wikifish /srv/wikifish
```

## 2. Install the application

```bash
sudo -u wikifish git clone https://github.com/khizar-z/wikifish.git /srv/wikifish/app
sudo -u wikifish python -m venv /srv/wikifish/app/.venv
sudo -u wikifish /srv/wikifish/app/.venv/bin/pip install --upgrade pip
sudo -u wikifish /srv/wikifish/app/.venv/bin/pip install -r /srv/wikifish/app/requirements.txt
```

## 3. Upload a compiled snapshot

Compile the snapshot on your build machine first, then copy it to the server:

```bash
rsync -avz /path/to/enwiki_snapshot/ your-user@your-server:/srv/wikifish/data/enwiki-YYYY-MM-DD/
```

On the server, point `current` at the active snapshot:

```bash
sudo -u wikifish ln -sfn /srv/wikifish/data/enwiki-YYYY-MM-DD /srv/wikifish/data/current
```

## 4. Configure systemd

Copy the example files from this repo:

```bash
sudo cp /srv/wikifish/app/deploy/systemd/wikifish.service /etc/systemd/system/wikifish.service
sudo cp /srv/wikifish/app/deploy/systemd/wikifish.env.example /etc/conf.d/wikifish
```

If needed, edit `/etc/conf.d/wikifish` and change `WIKIFISH_DATA_DIR` or `WIKIFISH_BIND`.

Start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now wikifish
sudo systemctl status wikifish
sudo journalctl -u wikifish -f
```

## 5. Add the site to Caddy

Merge this site block into your existing Caddyfile:

```caddy
wikifish.khizar.ca {
    reverse_proxy 127.0.0.1:8050
}
```

Because Caddy is already your public-facing web server, WikiFish does not need direct access to ports `80` or `443`. It only needs the internal loopback port `8050`.

Reload Caddy:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

## 6. Point DNS at the machine

Create an `A` record for `wikifish.khizar.ca` pointing at your server's public IPv4 address. If you also serve IPv6, add an `AAAA` record as well.

## 7. Updating the snapshot

When you build a new monthly snapshot:

1. copy it to a new versioned directory under `/srv/wikifish/data`
2. repoint `/srv/wikifish/data/current`
3. restart the service

Example:

```bash
sudo -u wikifish ln -sfn /srv/wikifish/data/enwiki-2026-06-01 /srv/wikifish/data/current
sudo systemctl restart wikifish
```

## 8. Smoke tests

On the server:

```bash
curl -I http://127.0.0.1:8050
curl -I https://wikifish.khizar.ca
```

You should also open the app in a browser and confirm:

- the startup banner shows the expected snapshot date
- a redirect title resolves correctly
- `Bidirectional BFS` returns results for a known short path
