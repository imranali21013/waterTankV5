# Water Tank V5 — Flask Dashboard

## Run on Windows

1. Open PowerShell in this folder.
2. Install packages: `py -m pip install -r requirements.txt`
3. Start: `py run.py`
4. Open `http://127.0.0.1:5555` on the server PC, or `http://<PC-LAN-IP>:5555` from another device on the LAN.

## Selection behavior

There is one Tank Selection panel; the separate Physical Switch Status panel is removed.

- A physical-switch change reported by the Master with `physicalSelectionChanged: true` updates the effective dashboard selection.
- A dashboard selection updates the effective selection immediately and is returned by `GET /api/commands` to the Master.
- The Master must apply the dashboard selection and report the effective selection in telemetry.
- The next detected physical-switch change takes authority again and replaces the effective selection with the physical switch positions.

Therefore, physical selection of Tanks 1 and 2 can be changed on the dashboard to Tanks 1, 2 and 4; those three are the effective selection until the next physical-switch change. Flask cannot physically move or change the hardware switches.

## Firmware API contract

- Master telemetry: `POST /api/master`
- Slave telemetry: `POST /api/slave`
- Master polls commands: `GET /api/commands`
- Dashboard controls: `POST /api/control`
- Dashboard reads telemetry: `GET /api/dashboard`

The command response includes `tankSelection` and `selectionSource` (`DASHBOARD` or `PHYSICAL`). On a physical switch transition, Master should send `physicalSelectionChanged: true` in the next `/api/master` payload and clear the flag on subsequent packets.

## Safety

This is the Flask/dashboard stage only. The ESP32 Master must validate commands and enforce sensor, timeout, interlock and stop conditions locally. Test first with pump and valve power disconnected.
