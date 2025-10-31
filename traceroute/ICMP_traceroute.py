#!/usr/bin/env python3
"""
Traceroute with ICMP, TCP fallback, and geolocation lookup

Usage:
    py (or python) ICMP_traceroute.py <hostname>  (Windows -> run as Administrator)
"""

import os
import sys
# using module we can: binary data <--> python data
import struct
# timestamps
import time
import select
import socket
# make HTTP requests
import requests

# ICMP
ICMP_ECHO_REQUEST = 8
ICMP_ECHO_REPLY = 0

# traceroute configuration
ICMP_TIME_EXCEEDED = 11
MAX_HOPS = 30
TRIES = 2
TIMEOUT = 2.0
TCP_PORT = 80


def checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b'\x00'
    s = 0
    for i in range(0, len(data), 2):
        w = (data[i] << 8) + (data[i + 1])
        s += w
        s &= 0xFFFFFFFF
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return ~s & 0xFFFF

def get_location(ip: str) -> str:
    # loopback recognition
    if ip in ("*", "127.0.0.1"):
        return "Localhost"
    try:
        # HTTP GET to public IP geolocation API endpoint to aquire the city, region, and country info for given IP 
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=2)
        # get json data of it from response obj so that we can index the strings from dict
        data = response.json()
        if data["status"] == "success":
            city = data.get("city", "")
            region = data.get("regionName", "")
            country = data.get("country", "")
            return f"{city}, {region}, {country}".strip(", ")
        else:
            return "Location unknown"
    except Exception:
        return "Lookup failed"

# build an ICMP Echo Request packet
def build_icmp_packet(ID: int) -> bytes:
    # initially its zero
    my_checksum = 0
    # compute without correct checksum first
    header = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, 0, my_checksum, ID, 1)
    # pack (convert to binary data) our curr timestamp (used for RTT calculation with reply back)
    data = struct.pack('!d', time.time())
    # compute the ICMP checksum based on header and payload
    my_checksum = checksum(header + data)
    # repacked ICMP Echo request is now correct
    header = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, 0, my_checksum, ID, 1)
    # return header with payload
    return header + data

def icmp_trace(hostname):
    # returns the IP address of website given
    # not to be confused with .gethostname(), which returns machine hostname
    dest_addr = socket.gethostbyname(hostname)
    print(f"Tracing route to {hostname} [{dest_addr}] via ICMP:\n")

    reached = False
    for ttl in range(1, MAX_HOPS + 1):
        for tries in range(TRIES):
            # .SOCK_RAW allows for sending raw packets (admin access required)
            # told to use ICMP protocol with .getprotobyname() (returns a constant value of 7)
            with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname("icmp")) as my_socket:
                # set TTL
                my_socket.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, struct.pack('I', ttl))
                # wait TIMEOUT seconds for a reply back
                my_socket.settimeout(TIMEOUT)
                # get process ID as unique identifier
                ID = os.getpid() & 0xFFFF
                # create the packet
                packet = build_icmp_packet(ID)
                # time before sending
                start_time = time.time()
                try:
                    # send packet and wait for socket to become readable
                    my_socket.sendto(packet, (hostname, 0))
                    ready = select.select([my_socket], [], [], TIMEOUT)
                    # no packet back -> timeout
                    if not ready[0]:
                        raise socket.timeout

                    # recieve back packet and extract info
                    recv_packet, addr = my_socket.recvfrom(1024)
                    time_received = time.time()
                    icmp_header = recv_packet[20:28] 
                    icmp_type, code, _, _, _ = struct.unpack("!BBHHH", icmp_header)
                    rtt = (time_received - start_time) * 1000

                    ip = addr[0]
                    if icmp_type == ICMP_TIME_EXCEEDED:
                        # intermediate hop —> just print IP, no geolocation
                        print(f"{ttl:<2}\t{ip:<15}\t{round(rtt):>3} ms")
                        break
                    elif icmp_type == ICMP_ECHO_REPLY:
                        # final destination —> do geo lookup
                        location = get_location(ip)
                        # output to terminal (use alignment, rounding for RTT, and tabbing)
                        print(f"{ttl:<2}\t{ip:<15}\t{round(rtt):>3} ms\t{location} (destination)")
                        reached = True
                        return reached
                    
                # timeout reached or not admin:
                except socket.timeout:
                    if tries == TRIES - 1:
                        print(f"{ttl:<2}\t*\tRequest timed out.")
                except PermissionError:
                    print("Permission denied. Run with admin/root.")
                    return False
    # for our fallback
    return reached

def tcp_trace(hostname):
    # A TCP-based traceroute 
    dest_addr = socket.gethostbyname(hostname)
    print(f"\nSwitching to TCP traceroute on port {TCP_PORT}:\n")

    for ttl in range(1, MAX_HOPS + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP) as tcp_socket:
            tcp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
            tcp_socket.settimeout(TIMEOUT)

            start_time = time.time()
            try:
                tcp_socket.connect((dest_addr, TCP_PORT))
                rtt = (time.time() - start_time) * 1000
                # only for final destination
                location = get_location(dest_addr)  
                print(f"{ttl:<2}\t{dest_addr:<15}\t{round(rtt):>3} ms\t{location} (destination)")
                return

            except socket.timeout:
                print(f"{ttl:<2}\t*\tRequest timed out.")
            except socket.error:
                print(f"{ttl:<2}\tintermediate\tRequest timed out.")

# driver code
# fallback to tcp tracing (SYN packets)
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py ICMP_traceroute.py <hostname>")
    else:
        target = sys.argv[1]
        reached = icmp_trace(target)
        if not reached:
            tcp_trace(target)
