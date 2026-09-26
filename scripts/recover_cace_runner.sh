#!/usr/bin/env bash
set -euo pipefail

mode=status
if [[ "${1:-}" == "--repair" ]]; then
  mode=repair
elif [[ "${1:-}" == "--status" || -z "${1:-}" ]]; then
  mode=status
else
  echo "usage: $0 [--status|--repair]" >&2
  exit 2
fi

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

find_runner_root() {
  local candidate
  for candidate in     /opt/actions-runner     /home/morganaspi/actions-runner     /home/github-runner/actions-runner; do
    if [[ -x "$candidate/run.sh" && -x "$candidate/config.sh" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

runner_root="$(find_runner_root || true)"
if [[ -z "$runner_root" ]]; then
  printf '%s\n' '{"schema_version":1,"ok":false,"reason":"runner_root_not_found","repair_attempted":false}'
  exit 10
fi

configured=false
[[ -f "$runner_root/.runner" ]] && configured=true

service_name=""
if [[ -s "$runner_root/.service" ]]; then
  service_name="$(tr -d '\r\n' < "$runner_root/.service")"
fi

listener_present=false
if pgrep -f 'Runner\.Listener run' >/dev/null 2>&1; then
  listener_present=true
fi

service_active=false
service_enabled=false
if [[ -n "$service_name" ]] && command -v systemctl >/dev/null 2>&1; then
  systemctl is-active --quiet "$service_name" && service_active=true || true
  systemctl is-enabled --quiet "$service_name" && service_enabled=true || true
fi

watchdog_active=false
if command -v systemctl >/dev/null 2>&1; then
  systemctl is-active --quiet cace-runner-watchdog.service && watchdog_active=true || true
fi

repair_attempted=false
repair_error=""
if [[ "$mode" == repair ]]; then
  repair_attempted=true
  if [[ "$configured" != true ]]; then
    repair_error="runner_not_configured_registration_required"
  elif ! command -v systemctl >/dev/null 2>&1; then
    repair_error="systemd_unavailable"
  elif ! sudo -n true >/dev/null 2>&1 && [[ "$(id -u)" -ne 0 ]]; then
    repair_error="passwordless_sudo_unavailable"
  else
    root_prefix=()
    if [[ "$(id -u)" -ne 0 ]]; then
      root_prefix=(sudo -n)
    fi

    if [[ -z "$service_name" ]]; then
      if [[ ! -x "$runner_root/svc.sh" ]]; then
        repair_error="runner_service_installer_missing"
      else
        owner="$(stat -c '%U' "$runner_root/.runner" 2>/dev/null || echo github-runner)"
        if [[ "$owner" == root || -z "$owner" ]]; then
          owner=github-runner
        fi
        (
          cd "$runner_root"
          "${root_prefix[@]}" ./svc.sh install "$owner"
        )
        if [[ -s "$runner_root/.service" ]]; then
          service_name="$(tr -d '\r\n' < "$runner_root/.service")"
        else
          repair_error="runner_service_marker_missing_after_install"
        fi
      fi
    fi

    if [[ -z "$repair_error" && -n "$service_name" ]]; then
      "${root_prefix[@]}" systemctl daemon-reload
      "${root_prefix[@]}" systemctl enable "$service_name" >/dev/null
      "${root_prefix[@]}" systemctl restart "$service_name"
    fi

    if [[ -z "$repair_error" ]]; then
      watchdog_bin=/usr/local/sbin/cace-runner-watchdog
      watchdog_unit=/etc/systemd/system/cace-runner-watchdog.service

      tmp_watchdog="$(mktemp)"
      cat > "$tmp_watchdog" <<'EOF'
#!/usr/bin/env bash
set -uo pipefail
telemetry=/var/lib/cace-cache/telemetry
runner_root=""
for candidate in /opt/actions-runner /home/morganaspi/actions-runner /home/github-runner/actions-runner; do
  if [[ -s "$candidate/.service" ]]; then
    runner_root="$candidate"
    break
  fi
done
mkdir -p "$telemetry"
while true; do
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '%s\n' "$ts" > "$telemetry/heartbeat.tmp" &&
    mv "$telemetry/heartbeat.tmp" "$telemetry/heartbeat"
  service=""
  if [[ -n "$runner_root" ]]; then
    service="$(cat "$runner_root/.service" 2>/dev/null || true)"
  fi
  if [[ -n "$service" ]] &&
      systemctl list-unit-files "$service" --no-legend 2>/dev/null | grep -q "$service"; then
    if ! systemctl is-active --quiet "$service"; then
      printf '%s runner-inactive restart-requested service=%s\n' "$ts" "$service" >> "$telemetry/watchdog.log"
      systemctl restart "$service" || true
    fi
  fi
  {
    echo "timestamp=$ts"
    echo "runner_service=$service"
    [[ -n "$service" ]] && systemctl status "$service" --no-pager 2>&1 || true
    free -h || true
    df -h / /var/lib/cace-cache 2>/dev/null || true
  } > "$telemetry/latest.tmp"
  mv "$telemetry/latest.tmp" "$telemetry/latest.txt"
  sleep 30
done
EOF
      "${root_prefix[@]}" install -m 0755 "$tmp_watchdog" "$watchdog_bin"
      rm -f "$tmp_watchdog"

      tmp_unit="$(mktemp)"
      cat > "$tmp_unit" <<'EOF'
[Unit]
Description=CACE GitHub runner watchdog
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/sbin/cace-runner-watchdog
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
      "${root_prefix[@]}" install -m 0644 "$tmp_unit" "$watchdog_unit"
      rm -f "$tmp_unit"
      "${root_prefix[@]}" systemctl daemon-reload
      "${root_prefix[@]}" systemctl enable --now cace-runner-watchdog.service >/dev/null

      sleep 2
      systemctl is-active --quiet "$service_name" && service_active=true || service_active=false
      systemctl is-enabled --quiet "$service_name" && service_enabled=true || service_enabled=false
      systemctl is-active --quiet cace-runner-watchdog.service && watchdog_active=true || watchdog_active=false
      pgrep -f 'Runner\.Listener run' >/dev/null 2>&1 && listener_present=true || listener_present=false
    fi
  fi
fi

python3 - "$runner_root" "$configured" "$service_name" "$service_active" "$service_enabled" "$watchdog_active" "$listener_present" "$repair_attempted" "$repair_error" <<'PY'
import json
import sys

(
    runner_root,
    configured,
    service_name,
    service_active,
    service_enabled,
    watchdog_active,
    listener_present,
    repair_attempted,
    repair_error,
) = sys.argv[1:]

payload = {
    "schema_version": 1,
    "ok": not repair_error and configured == "true",
    "runner_root": runner_root,
    "configured": configured == "true",
    "registration_required": configured != "true",
    "service_name": service_name or None,
    "service_active": service_active == "true",
    "service_enabled": service_enabled == "true",
    "watchdog_active": watchdog_active == "true",
    "listener_present": listener_present == "true",
    "repair_attempted": repair_attempted == "true",
    "repair_error": repair_error or None,
    "authority": "local-runner-recovery-only",
    "repository_mutation": False,
    "instance_lifecycle_mutation": False,
}
print(json.dumps(payload, sort_keys=True))
PY

[[ -z "$repair_error" ]] || exit 20
