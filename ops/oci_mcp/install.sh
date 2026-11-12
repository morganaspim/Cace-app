#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_sha="$(git -C "$repo_root" rev-parse HEAD 2>/dev/null || printf 'working-tree')"
root="/opt/cace-oci-mcp"
release="$root/releases/$source_sha"
venv="$root/venv"

sudo -n true

if ! id cace-mcp >/dev/null 2>&1; then
  sudo useradd --system --create-home --home-dir /var/lib/cace-oci-mcp --shell /sbin/nologin cace-mcp
fi
if getent group systemd-journal >/dev/null 2>&1; then
  sudo usermod -a -G systemd-journal cace-mcp
fi

sudo mkdir -p "$root/releases" /var/lib/cace-oci-mcp/cache
sudo rm -rf "$release"
sudo mkdir -p "$release/ops"
sudo cp -a "$repo_root/ops/oci_mcp" "$release/ops/"
sudo touch "$release/ops/__init__.py"
sudo chown -R root:root "$release"
sudo chmod -R go-w "$release"

if [[ ! -x "$venv/bin/python" ]]; then
  sudo python3 -m venv "$venv"
fi
sudo "$venv/bin/python" -m pip install --upgrade pip
sudo "$venv/bin/python" -m pip install -r "$release/ops/oci_mcp/requirements.txt"

sudo ln -sfn "$release" "$root/current"
sudo install -o root -g root -m 0644   "$release/ops/oci_mcp/cace-oci-mcp.service"   /etc/systemd/system/cace-oci-mcp.service
sudo install -o root -g root -m 0440   "$release/ops/oci_mcp/cace-oci-mcp.sudoers"   /etc/sudoers.d/cace-oci-mcp
sudo visudo -cf /etc/sudoers.d/cace-oci-mcp

sudo install -d -o cace-mcp -g cace-mcp -m 0700 /var/lib/cace-oci-mcp /var/lib/cace-oci-mcp/cache

if [[ ! -f /etc/cace-oci-mcp.env ]]; then
  sudo tee /etc/cace-oci-mcp.env >/dev/null <<'EOF'
# Fail-closed defaults. Enable capabilities only after OCI IAM is configured.
CACE_OCI_MCP_ALLOW_SERVICE_RESTART=false
CACE_OCI_MCP_ALLOW_NETWORK_WRITE=false
CACE_OCI_MCP_ALLOW_MERLIN_RSI_SIGNING=false
EOF
  sudo chmod 0600 /etc/cace-oci-mcp.env
fi

sudo systemctl daemon-reload
sudo systemctl enable --now cace-oci-mcp
sudo systemctl restart cace-oci-mcp
sudo systemctl is-active --quiet cace-oci-mcp

echo "CACE_OCI_MCP_INSTALLED source_sha=$source_sha endpoint=http://127.0.0.1:8765/mcp"
