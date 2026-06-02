# Mitel OMMClient2

Another attempt for a modern client library to the Mitel OM Application XML Interface.

## Install

Without any additional dependencies:

```
pip install "mitel_ommclient2 @ git+https://git.clerie.de/clerie/mitel_ommclient2.git@main"
```

Add dependencies to enable secret handling, if you need it.

```
pip install "mitel_ommclient2[crypt] @ git+https://git.clerie.de/clerie/mitel_ommclient2.git@main"
```

## Quicksart

Just some examples to give you an idea what this does.

```
import mitel_ommclient2

# Connect to your OMM
c = mitel_ommclient2.OMMClient2("omm.local", "admin", "admin")

# Use built in methods for common actions
c.ping()

# Create custom messages
m = mitel_ommclient2.messages.Ping()
m.timeStamp = 2342
r = c.connection.request(m)
```

Consult class documentation for more in depth examples and options.

## Interactive CLI

The package installs a script called `ommclient2`.
This allowes basic interactive testing of the library.

```
ommclient2 --help
```

## Attribution

This software is inspired by `python-mitel` by Thomas and n-st.
