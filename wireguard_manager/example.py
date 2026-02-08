import InterfaceManager





#example usage
mgr = InterfaceManager.InterfaceManager()

ifaces = mgr.list_interfaces()  # ['wg0', 'wg1']



for iface_nsme in ifaces:

    #mgr.up(iface)  # bring up interface
    
    iface = mgr.load(iface_nsme)
    iface_info = iface.show()  # dict with interface info like public key, listening port, etc.
    print(iface_info)
    if iface_info["state"] == "up":
        print(f"{iface_info['interface']} is up with public key {iface_info['public_key']} and listening port {iface_info['listening_port']}")

        peer_keys = iface.get_peers()  # list of peer public keys

        for peer_key in peer_keys:
            peer = iface.get_peer(peer_key)
            stats = peer.stats()  # dict with peer stats like endpoint, latest handshake, rx/tx bytes, etc.
            print(stats)

    mgr.down(iface_nsme)  # bring down interface

