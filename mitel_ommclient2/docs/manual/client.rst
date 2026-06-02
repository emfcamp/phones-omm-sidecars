Client Usage Manual
===================

This should give you an introduction on how to use :class:`mitel_ommclient2.client.OMMClient2`.

If you are not interested in using the abstraction layer, even though it is recommended,
have a look at :doc:`/manual/connection` .

Creating a client
-----------------

To start with this client, you need login credentials for your OMM. The permissions
you have using this client are the ones assinged to the user you login with.

You are required to specify at least the host to connect to, a username and a corresponding
password. For further options see :class:`mitel_ommclient2.client.OMMClient2`.

.. code-block:: python

    import mitel_ommclient2

    c = mitel_ommclient2.OMMClient2("omm.local", "admin", "password")

Creating this object will directly connect to the API of the corresponding host.
Failure in connection or authenticating will raise an excaption.

Using the API
-------------

:class:`mitel_ommclient2.client.OMMClient2` ships with several mathods that wraps and
validate common API requests. See class documentation to get and overview and options.

.. code-block:: python

    c.ping()

Making custom requests
----------------------

:class:`mitel_ommclient2.client.OMMClient2` holds its :class:`mitel_ommclient2.connection.Connection`
in the connection attribute.
Use :func:`mitel_ommclient2.connection.Connection.request` directly for making some custom requests.
See :doc:`/manual/connection` about using this.
