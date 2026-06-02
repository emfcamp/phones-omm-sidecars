Message Usage Manual
====================

The API consists of three main message types: request, response and event. They
are represented by :class:`mitel_ommclient2.messages.Request`, :class:`mitel_ommclient2.messages.Response`
and events aren't supported yet.

There are several subclasses for each messages type, which provide a conveinient
interface to message content using attributes.

For each message you can access each field directly as class attributes.
There are two special attributes:
  * name: returns the message name
  * childs: allowes you to access childs by the child name as class attributes

Using messages
--------------

Just choose one of several message classes of :module:`mitel_ommclient2.messages`
and hand it over to :func:`mitel_ommclient2.client.OMMClient2.request` or
:func:`mitel_ommclient2.connection.Connection.request`.

.. code-block:: python

    import time

    my_time = int(time.time())

    m = mitel_ommclient2.messages.Ping()
    m.timeStamp = my_time
    r = c.request(m)

    ping = r.timeStamp - my_time

A more complex example
----------------------

This demonstrates how to access message childs.

.. code-block:: python

    m = messages.GetAccount()
    m.id = id
    r = self.connection.request(m)
    return r.childs.account[0]
