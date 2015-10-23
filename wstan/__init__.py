import asyncio
import logging
import socket
import struct
import argparse
from autobahn.websocket.protocol import parseWsUrl

__author__ = 'krrr'
__version__ = '0.1'

# global variables shared between modules
config = loop = None


def parse_relay_request(dat, allow_remain=True):
    """Extract address and port from SOCKS relay request header (only 3 parts:
    ATYP | DST.ADDR | DST.PORT). These data will also be reused in tunnel server."""
    atyp = dat[0]
    if atyp == 0x01:  # IPv4
        port_idx = 5
        target_addr = socket.inet_ntoa(dat[1:port_idx])
    elif atyp == 0x03:  # domain name
        port_idx = 2 + dat[1]
        target_addr = dat[2:port_idx].decode('ascii')
    elif atyp == 0x04:  # IPv6
        port_idx = 17
        target_addr = socket.inet_ntop(socket.AF_INET6, dat[1:port_idx])
    else:
        raise ValueError
    target_port = struct.unpack('>H', dat[port_idx:port_idx+2])[0]
    dat_remain = dat[port_idx+2:]
    if allow_remain:
        return target_addr, target_port, dat_remain
    else:
        if dat_remain:
            raise ValueError
        return target_addr, target_port


def load_config():
    parser = argparse.ArgumentParser(description='wstan')
    # common config
    parser.add_argument('uri', help='URI of server')
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-c', '--client', help='run as client (default, also act as SOCKS v5 server)',
                   action='store_true')
    g.add_argument('-s', '--server', help='run as server', action='store_true')
    parser.add_argument('-d', '--debug', action='store_true')
    # local side config
    parser.add_argument('-a', '--addr', help='listen address of local SOCKS server (defaults localhost)',
                        default='localhost')
    parser.add_argument('-p', '--port', help='listen port of local SOCKS server (defaults 1080)',
                        type=int, default=1080)
    # remote side config
    parser.add_argument('-t', '--tun-addr', help='listen address of server, override URI')
    parser.add_argument('-r', '--tun-port', help='listen port of server, override URI', type=int)
    args = parser.parse_args()

    args.tun_ssl, args.uri_addr, args.uri_port = parseWsUrl(args.uri)[:3]
    return args


def main_entry():
    global config, loop
    config = load_config()
    loop = asyncio.get_event_loop()
    logging.basicConfig(level=logging.DEBUG if config.debug else logging.INFO,
                        format='{levelname}: {message}', style='{')

    if config.server:
        from wstan.server import main
    else:
        from wstan.client import main
    return main()