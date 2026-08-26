#!/bin/bash
# NUT final-shutdown handler for Syndome Claire (USB monitor-only; no killpower).
set -euo pipefail

LOG=/var/log/nut-fsd-shutdown.log
UPS_NAME="${NUT_UPS_NAME:-claire}"
RTC_WAKE_SECS=1800

if [[ -f /etc/default/nut-fsd-shutdown ]]; then
  # shellcheck disable=SC1091
  source /etc/default/nut-fsd-shutdown
fi

log() {
  echo "$(date -Is) $*" | tee -a "$LOG"
}

log "FSD triggered for ${UPS_NAME}@localhost"

for cmd in shutdown.return load.off; do
  if upscmd "${UPS_NAME}@localhost" "$cmd" >>"$LOG" 2>&1; then
    log "upscmd ${cmd} succeeded"
  else
    log "upscmd ${cmd} failed (expected on Claire monitor-only USB)"
  fi
done

if upsdrvctl shutdown >>"$LOG" 2>&1; then
  log "upsdrvctl shutdown succeeded"
else
  log "upsdrvctl shutdown failed (expected on Claire)"
fi

if rtcwake -m no -s "$RTC_WAKE_SECS" >>"$LOG" 2>&1; then
  log "RTC wake armed in ${RTC_WAKE_SECS}s"
else
  log "rtcwake failed — check BIOS Power On By RTC"
fi

log "Halting OS"
exec shutdown -h now
