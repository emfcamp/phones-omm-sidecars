# phones-omm-sidecars

This is a collection of applications / containers that manage the Mitel OMM DECT Controller.

## dect-users

* Runs a keep-alive loop that ensures DECT subscription settings are correct, and re-applies if they have changed externally (e.g. via web UI):
  * auth code is "0000"
  * auto-create is enabled
  * subscription mode is Configured.
* Listens for PPDevCnf events and creates provisional users for unbound devices by calling the SIP core's temp number API.
* Exposes a webhook endpoint for the SIP core to notify us of bind/unbind events.

## dect-monitor

Prometheus exporter for DECT system health metrics - subscribes to OMM events and exposes gauges via HTTP.

## dect-fun

Messaging bridge between DECT phones and the SIP core.

* **Inbound**: SIP core POSTs to us, we deliver to DECT via AXI SendMessage.
* **Outbound**: DECT phones send messages (EventMessageSend), we POST to SIP core.