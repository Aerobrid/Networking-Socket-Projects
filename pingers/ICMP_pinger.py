#!/usr/bin/env python3
"""
ICMP Ping client (Python 3)

Usage:
    python pinger.py google.com              # Windows
    (Run with Administrator/root privileges for the socket import) 
"""

import os
import sys
# for packing/unpacking binary data 
import struct
# we want to calculate the amount of time it takes to ping (RTT)
import time
import select
import socket

# ICMP type code for echo request = 8
# ICMP type code for echo reply = 0
ICMP_ECHO_REQUEST = 8  


# Compute the Internet checksum (required in ICMP headers)
# we use a lot of bitmasking
def checksum(data: bytes) -> int:
    # data needs to be even (16-bit)
    # if odd you are basically adding a byte to data in binary (padding it) using hexadecimal representation
    if len(data) % 2:
        data += b'\x00'
    s = 0
    for i in range(0, len(data), 2):
        w = (data[i] << 8) + data[i + 1]
        s += w
        # folding to keep in 32-bit range (since it can be unbounded)
        s &= 0xFFFFFFFF
    # fold high 16-bits if any
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    # return ones complement by doing NOT (~) and only returning lower/least 16-bits through bitmasking
    return ~s & 0xFFFF


def receive_one_ping(my_socket, ID, timeout, dest_addr):
    # receive the ping reply and return RTT info or timeout string
    time_left = timeout
    while True:
        start_select = time.time()
        ready = select.select([my_socket], [], [], time_left)
        how_long_in_select = time.time() - start_select
        if not ready[0]:
            return "Request timed out."

        time_received = time.time()
        rec_packet, addr = my_socket.recvfrom(1024)

        # firs 20 bytes is ip header
        ip_header = rec_packet[:20]
        # '!' -> enforce network byte order -> big-endian (always want to use since it follows normal standard and not local computer standard)
        # we unpack back into python whatever bytes came through in recv_packet ip header
        # B -> unsigned char (1 byte), H -> Unsigned short (2-byte), d -> double-precision float (8-byte)
        iph = struct.unpack('!BBHHHBBH4s4s', ip_header)
        version_ihl = iph[0]
        ihl = version_ihl & 0x0F
        ip_header_len = ihl * 4
        ttl = iph[5]

        # the ICMP header
        icmp_header_offset = ip_header_len
        icmp_header = rec_packet[icmp_header_offset:icmp_header_offset + 8]
        icmp_type, code, recv_checksum, packet_id, sequence = struct.unpack(
            '!BBHHH', icmp_header
        )

        # accept only replies matching the ID
        if packet_id == ID and icmp_type == 0:
            data_offset = icmp_header_offset + 8
            time_sent = struct.unpack('!d', rec_packet[data_offset:data_offset + 8])[0]
            rtt = time_received - time_sent
            bytes_returned = len(rec_packet) - ip_header_len
            return (
                f"{bytes_returned} bytes from {addr[0]}: "
                f"icmp_seq={sequence} ttl={ttl} time={round(rtt * 1000, 3)} ms"
            )

        time_left -= how_long_in_select
        if time_left <= 0:
            return "Request timed out."


def send_one_ping(my_socket, dest_addr, ID, sequence):
    # send one ICMP ECHO REQUEST packet
    my_checksum = 0
    header = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, 0, my_checksum, ID, sequence)
    data = struct.pack('!d', time.time())
    my_checksum = checksum(header + data)
    header = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, 0, my_checksum, ID, sequence)
    packet = header + data
    my_socket.sendto(packet, (dest_addr, 1))


def do_one_ping(dest_addr, timeout, ID, sequence):
    # send one ping and wait for the reply
    icmp_proto = socket.getprotobyname("icmp")
    with socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp_proto) as my_socket:
        send_one_ping(my_socket, dest_addr, ID, sequence)
        return receive_one_ping(my_socket, ID, timeout, dest_addr)


def ping(host, timeout=1):
    # we need the IP of website so we can ping it
    try:
        dest = socket.gethostbyname(host)
    except Exception as e:
        print(f"Cannot resolve {host}: {e}")
        return

    print(f"Pinging {host} [{dest}] using Python:\n")
    # lower 16-bits of current process ID (pid)
    ID = os.getpid() & 0xFFFF
    seq = 1
    # start up the pinging process and do it indefinitely,
    #  while keeping up with seq # (bitmasked) and time delay
    try:
        while True:
            result = do_one_ping(dest, timeout, ID, seq)
            print(result)
            seq = (seq + 1) & 0xFFFF
            time.sleep(1)
    # (ctrl + C) for me on windows terminal
    except KeyboardInterrupt:
        print("\nPing interrupted by user.")


# main driver code
if __name__ == "__main__":
    target = sys.argv[1] 
    if len(sys.argv) > 1:
            target = sys.argv[1]
            ping(target)
    else:
        print("Please give a website to ping.\nTemplate Usage: python ICMP_pinger.py <hostname>")

