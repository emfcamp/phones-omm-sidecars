"""SIP endpoint for handling calls from DECT devices."""

import logging

from pyVoIP.VoIP import InvalidStateError, VoIPCall, VoIPPhone

log = logging.getLogger(__name__)


def on_call(call: VoIPCall) -> None:
    """Handle an incoming call. Runs in a pyVoIP thread."""
    try:
        call.answer()
        from_number = call.request.headers["From"]["number"]
        to_number = call.request.headers["To"]["number"]
        log.info("call from %s to %s", from_number, to_number)
        call.hangup()
    except InvalidStateError:
        pass


def create_sip_endpoint(
    server: str,
    port: int,
    username: str,
    password: str,
    *,
    my_ip: str = "0.0.0.0",
) -> VoIPPhone:
    """Create and start a SIP endpoint."""
    phone = VoIPPhone(
        server,
        port,
        username,
        password,
        callCallback=on_call,
        myIP=my_ip,
    )
    phone.start()
    return phone
