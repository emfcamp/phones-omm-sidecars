# phones-omm-sidecars

This is a collection of applications and a container that expose an API to manage the Mitel OMM DECT Controller.

**Inbound** requests are made from the phones-web service to the OMM sidecars that listen on `HTTP_PORT` (defaults to `8080`).

**Outbound** requests are made from the OMM sidecars to the phones-web service.

## Applications

### dect-users

* Runs a keep-alive loop that ensures DECT subscription settings are correct, and re-applies if they have changed externally (e.g. via web UI):
  * auth code is "0000"
  * auto-create is enabled
  * subscription mode is Configured.
* Listens for PPDevCnf events and assigns temporary numbers to new DECT handsets by calling the phones-web temp number API.
* Exposes a webhook endpoint for phones-web to notify when a user claims a vanity number or updates settings.

**`POST /webhook` — inbound**

Called by phones-web to notify OMM when a user claims a vanity number or updates settings.

**Request body**

```json
{
  "currentNumber": 1234,
  "sipUsername": "1234",
  "properties": {
    "ipei": "0012345678901234",
    "name": "Jane Doe", // optional
    "encryption": true // optional, default false
  },
  "event": "bind" // optional
}
```

**Response**

```json
// 200 OK — reconciled
{"ok": true}
```

Non-200 responses are `{"error": "<message>"}` with one of these statuses:

| Status | Cause |
|---|---|
| 400 | Malformed body or reconcile failure |

**`POST {CORE_API_URL}/temp-numbers/assign/dect` — outbound**

Called by the sidecar to phones-web to allocate a temporary number to a newly registered DECT handset.

**Request body**

```json
{ "ipei": "0012345678901234" }
```

**Response**

```json
// 200 OK
{
  "currentNumber": 1234,
  "sipUsername": "1234",
  "properties": {
    "ipei": "0012345678901234",
    "name": "Jane Doe",
    "encryption": true
  }
}
```

### dect-monitor

Exposes: 
* OMM system health metrics in the prometheus format
* Mitel Handset firmware version
* The last known RFP a handset was connected to

**`GET /metrics` — inbound**

Prometheus gauges/counters for OMM system health, on `OMM_PROM_PORT`
(default `8000`). No authentication.

**Response**

```
# HELP dect_firmware_overview_state Firmware download manager state (0=startup, 1=disabled, 2=running, 3=error)
# TYPE dect_firmware_overview_state gauge
dect_firmware_overview_state 2.0
dect_pp_active_1h 14.0
dect_rfp_active_call_legs{rfp_id="3"} 1.0
```

**`GET /firmware?num=<number>` — inbound**

Gets the firmware status of a Mitel DECT handset

**Response**

```json
// 200 OK
{
  "ppn": 12,
  "num": "1234",
  "state": "ready",
  "cause": null,
  "bytes_remaining": 0,
  "current_version": "5.1.0"
}
```

Non-200 responses are `{"error": "<message>"}` with one of these statuses:

| Status | Cause |
|---|---|
| 400 | Invalid request |
| 404 | No such user, or user has no bound device |
| 502 | Firmware status lookup failed |

**`GET /location?num=<number>` — inbound**

Gets the last known RFP a DECT Handset was connected to

**Response**

```json
// 200 OK
{
  "ppn": 12,
  "num": "1234",
  "rfp_id": 3,
  "rfp_name": "Warehouse-3",
  "last_event": "LocReg",
  "timestamp": 1755000000.0
}
```

Non-200 responses are `{"error": "<message>"}` with one of these statuses:

| Status | Cause |
|---|---|
| 400 | Invalid request |
| 404 | No such user, unbound device, or no location |

### dect-fun

Messaging bridge between DECT phones and the phones-web

**`POST /message` — inbound**

Called by phones-web to send an SMS message to a Mitel DECT handset.

**Request body**

```json
{
  "to": "1234",
  "fromNumber": "5678",
  "content": "hello",
  "fromName": "Jane Doe" // optional
}
```

**Response**

```json
// 200 OK
{"status": "ok"}
```

Non-200 responses are `{"error": "<message>"}` with one of these statuses:

| Status | Cause |
|---|---|
| 400 | Invalid request |
| 403 | Message receive license is not set.|
| 404 | No DECT handset found for given destination. |
| 503 | The queue for this DECT handset is full. |
| 500 | Unexpected failure |

**`POST {MESSAGE_TARGET_URL}` — outbound**

Called by the sidecar to relay an SMS sent by a DECT handset to phones-web

**Request body**

```json
{
  "to": "5678",
  "fromNumber": "1234",
  "fromName": "Jane Doe", // optional
  "content": "hello"
}
```

**Response**

| Status | Cause |
|---|---|
| `<400` | Success |
| `>=400` | Sends a "Delivery Failed" message back to the DECT handset|


## Attribution

This software utilises [mitel_ommclient2](https://git.clerie.de/clerie/mitel_ommclient2) which was inspired by [python-mitel](https://github.com/eventphone/python-mitel)

## License

* This project is licensed under the AGPL3 license
* mitel_ommclient2 is licensed under the MIT license