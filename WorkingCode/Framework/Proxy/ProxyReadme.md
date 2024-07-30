# Proxy

### ProxyController
Wraps all the helper classes together. 

> ProxyHeader, ProxySerializer, Connector, TCPconnector, LoRaConnector, EnumsManager

The ProxyController can register local sources (Labjacks, archivers, GUIs, etc.)
to itself and the network. When sources are registered to the network, 
all proxies within the network are given the unique name of each source. This unique name 
can be used as a source or destination when sending packages through the proxy. 
Any package paired with both a source name and destination name, both registered to the network,
will arrive at the desired proxy and be passed to their relevant manager
(data/command/event)

*Remove sources* feature is not complete yet.

Has functionality for...
* Sending Packages to correct framework instance based on source names. 
    These packages are then handled by managers (data/command/event).
* Receiving Packages with destination names
* knows all connections it has
* knows all sources on the network
* network management
    * Joining/Listening
    * Source registration
    * network packet forwarding.
    * TODO: connection status packets, finish implementing *remove sources* feature
    
### ProxySerializer
Handles turning package payloads into bytes.

##### Important Methods
* *getPacketFromPackage(sourceID, destinationID, pktID, package:Package, packetType, fmt=None)*
    - forms a single packet (bytes) including a header.
* *getMetadataPacketFromPackage(sourceID, destinationID, pktID, package:Package, metadata=None, fmt=None)*
    - Forms a metadata packet (header and pickled ordered dictionary)
* *getPayloadFromPacket(packet, sources)*
    - returns a payload (dict) when given a packet and self.sources dictionary from ProxyController

### EnumsManager
Keeps track of Enums that maybe sent in payloads. Replaces them with 
short string with format **_E##** where **##** is replaced with a unique key.

### Connector
Base class for TCP or LoRa connector classes.

Forces all connectors to have a few things including send and recv methods.

Forces all send calls to receive bytes or bytearrays, either solo or in lists/sets/tuples

## TODO: High priority
* Create LoRaConnector
* add connection status checks. (acknowledgements for some packets) so
  any proxies that are primarily senders can know when to rejoin network if connection lost
* add network rejoining after temporary lost connection
* network health checks to ensure all nodes have the same sources
* once successfully joined network or received new sources,
    send lists of sources to all managers (need manager implementation now)
## TODO: low priority
* Network needs to be able to map its paths
* Allow payloads to be non-dictionary objects
* Finish *remove sources* feature