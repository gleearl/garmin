# Deploying the backend to Oracle Cloud Always Free

This hosts the Garmin Dashboard backend on a free, always-on Oracle Cloud VM, with
automatic HTTPS via Caddy. The [GitHub Pages frontend](https://gleearl.github.io/garmin/)
then points at it using the ⚙️ Settings panel — no frontend redeploy needed.

> **Heads-up on credentials.** Your Garmin OAuth tokens will live on this VM. Lock the
> instance down (SSH keys only; open just ports 22/80/443). Garmin sometimes challenges
> logins from datacenter IPs — if the on-VM login fails, see "If login is blocked" below.

---

## 1. Create the Oracle Always Free VM

1. Sign up at <https://www.oracle.com/cloud/free/> (a payment card is required for identity
   verification; Always Free resources are not charged).
2. **Create instance** → Image: **Ubuntu 22.04**. Shape: **VM.Standard.A1.Flex** (ARM,
   1 OCPU / 6 GB is plenty). If you hit **"Out of capacity"**, retry, switch availability
   domain, or use the AMD **VM.Standard.E2.1.Micro** Always Free shape instead.
3. Add your SSH public key. Create.
4. **Open the firewall (two layers):**
   - **OCI security list:** VCN → Subnet → Security List → add Ingress rules for TCP **80**
     and **443** from `0.0.0.0/0`.
   - **On the VM** (Ubuntu's iptables blocks by default):
     ```bash
     sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
     sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
     sudo netfilter-persistent save
     ```

## 2. Free HTTPS hostname (DuckDNS)

Let's Encrypt needs a DNS name, not a raw IP.

1. Go to <https://www.duckdns.org>, sign in, create a subdomain (e.g. `mygarmin`).
2. Set its IP to your VM's **public IP** (from the OCI instance page).
   You now have `mygarmin.duckdns.org`.

> If you own a domain instead, just point an A record at the VM IP and use that as `DOMAIN`.

## 3. Install Docker + clone

```bash
ssh ubuntu@<VM_PUBLIC_IP>
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu && newgrp docker      # run docker without sudo
git clone https://github.com/gleearl/garmin.git
cd garmin/deploy
cp .env.example .env
sed -i 's/yourname.duckdns.org/mygarmin.duckdns.org/' .env   # your real hostname
```

## 4. Start the stack

```bash
docker compose up -d --build
```

Caddy fetches a Let's Encrypt cert for your hostname automatically (give it ~30s).
Check: `curl https://mygarmin.duckdns.org/api/summary` → `{"daily":null,...}` (empty until synced).

## 5. One-time Garmin login (handles MFA)

```bash
docker compose run --rm api python -m garmin_dash.login
```

Enter your Garmin email/password and the MFA code when prompted. Tokens are written to the
`data` volume and reused automatically afterwards.

### If login is blocked from the VM (datacenter IP)
Run the login on your **own machine** instead, then copy the tokens up:
```bash
# locally (from backend/):  uv run python -m garmin_dash.login
scp -r ~/.garminconnect ubuntu@<VM_PUBLIC_IP>:/tmp/tokens
# on the VM, load them into the data volume:
docker compose run --rm -v /tmp/tokens:/tmp/tokens api sh -c "cp /tmp/tokens/* /data/tokens/ 2>/dev/null; mkdir -p /data/tokens && cp -r /tmp/tokens/. /data/tokens/"
```

## 6. Initial data pull + daily schedule

```bash
docker compose exec -T api python -m garmin_dash.sync --days 90

# Install the daily timer (edit WorkingDirectory in the .service if your path differs):
sudo cp garmin-sync.service garmin-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now garmin-sync.timer
systemctl list-timers garmin-sync.timer        # confirm it's scheduled
```

## 7. Point the dashboard at it

Open <https://gleearl.github.io/garmin/>, click ⚙️, paste `https://mygarmin.duckdns.org`,
click **Test** (should show ✓ Connected), then **Save & reload**. Done.

---

## Operations

| Task | Command (in `deploy/`) |
|---|---|
| View logs | `docker compose logs -f api` / `... caddy` |
| Manual sync | `docker compose exec -T api python -m garmin_dash.sync --days 7` |
| Update code | `git pull && docker compose up -d --build` |
| Restart | `docker compose restart` |
| Reset cache | `docker compose down && docker volume rm deploy_data` (re-login needed) |

After `sudo reboot`, the stack auto-starts (`restart: unless-stopped`) and the DB + tokens
persist on the `data` volume — no re-login required.
