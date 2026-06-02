#!/usr/bin/env python3

import queue
import select
import socket
import ssl
import threading

from . import messages

class Connection:
    """
        Establishes a connection to the OM Application XML Interface.
        Uses a SSL connetion per default.

        :param host: Hostname or IP address of OMM
        :param port: Port of the OM Application XML plain TCP port
        :param use_ssl: Whenever SSL should be used for the connetion
        :param timeout: The timeout used for the connection

        Usage::
            >>> c = Connection("omm.local")
            >>> c.connect()
            >>> c.send(request)
            >>> r = c.recv()
    """

    def __init__(self, host, port=12622, use_ssl=True, timeout=2):
        self._host = host
        self._port = port

        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.settimeout(timeout)

        if use_ssl:
            ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)
            ssl_context.set_ciphers('DEFAULT')

            self._socket = ssl_context.wrap_socket(tcp_socket, server_hostname=self._host)
        else:
            self._socket = tcp_socket

        self._close = False

        self._seq = 0 # state of the sequence number generator
        self._requests = {} # waiting area for pending responses


    def connect(self):
        """
            Establishes the connection
        """

        self._socket.connect((self._host, self._port))
        self._socket.setblocking(False)

        threading.Thread(target=self._receive_loop, daemon=True).start()

    def _receive_loop(self):
        """
            Receives messages from socket and associates them to the responding request

            This function is intended to be executed in thread.
        """

        recv_buffer = b""

        while not self._close:
            if select.select([self._socket], [], []) != ([], [], []):
                # wait for data availiable
                while True:
                    try:
                        # fill buffer with one message
                        data = self._socket.recv(1024)
                    except (BlockingIOError, ssl.SSLWantReadError):
                        continue

                    if not data:
                        # buffer is empty
                        break

                    recv_buffer += data

                    if b"\0" in recv_buffer:
                        # there is a full message in buffer, handle that first
                        break


                if b"\0" not in recv_buffer:
                    # no new messages
                    break

                # get one message from recv_buffer
                message, buffer = recv_buffer.split(b"\0", 1)
                recv_buffer = buffer

                # parse the message
                message = message.decode("utf-8")
                response = messages.parse(message)

                if response.seq in self._requests:
                    # if this response belongs to a request, we return it and resolve the lock
                    self._requests[response.seq]["response"] = response
                    self._requests[response.seq]["event"].set()

                # else the message will be ignored

    def _generate_seq(self):
        """
            Returns new sequence number

            This generates a number that tries to be unique during a session
        """

        seq = self._seq
        self._seq += 1
        return seq

    def request(self, request):
        """
            Sends a request, waits for response and return response

            :param request: Request object

            Usage::
                >>> r = c.request(mitel_ommclient2.messages.Ping())
                >>> r.name
                'PingResp'
        """

        # generate new sequence number and attach to request
        seq = self._generate_seq()
        request.seq = seq

        # add request to waiting area
        self._requests[seq] = {
            "event": threading.Event(),
        }

        # send request
        message = messages.construct(request)
        self._socket.send(message.encode("utf-8") + b"\0")

        # wait for response
        self._requests[seq]["event"].wait()

        # return reponse and remove from waiting area
        return self._requests.pop(seq, {"response": None})["response"]

    def close(self):
        """
            Shut down connection
        """

        self._close = True
        return self._socket.close()

    def __del__(self):
        self.close()


class SSLConnection(Connection):
    """
        Establishes a secure connection to the OM Application XML Interface

        Please not that this class might be useless on your system since new
        versions of OpenSSL don't ship with TLVv1.2 or lower anymore which are
        the protocols supported by OMM.

        :param host: Hostname or IP address of OMM
        :param port: Port of the OM Application XML ssl TCP port

        Usage:

        See :class:`Connection`
    """

    def __init__(self, host, port=12622):
        super().__init__(host, port)

        self._socket = ssl.wrap_socket(self._socket)
