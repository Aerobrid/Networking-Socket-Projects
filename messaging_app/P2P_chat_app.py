#!/usr/bin/env python3
"""
p2p_chat.py - peer-to-peer chat using TCP sockets and threading

Usage:
  To listen/wait for a connection:
    python p2p_chat.py --listen --port 5000 --name User1Name

  To connect to a peer:
    python P2P_chat_app.py --host 1.2.3.4 --port 5000 --name User2Name
"""

import socket
import threading
# for required arguments when calling program
import argparse
# reading stdin
import sys
import time

# message delimiter
DELIM = b'\n' 
# how many bytes to read from socket
BUFFER_SIZE = 4096

# for receiving peer msg
def recv_loop(conn: socket.socket, remote_name: str):
    # this loop accumulates bytes until hitting the delimiter
    # you log status and break accordingly in loop, also add to binary data "buffer" variable
    buffer = b''
    try:
        while True:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                print("\n[System] Remote peer disconnected.")
                break
            # can arrive in chunks
            buffer += data
            while True:
                # check if you delimiter is there
                idx = buffer.find(DELIM)
                if idx == -1:
                    break
                # extract
                raw = buffer[:idx]
                # move buffer
                buffer = buffer[idx + len(DELIM):]
                # try and decode output
                try:
                    text = raw.decode('utf-8', errors='replace')
                except Exception:
                    text = "<unreadable>"
                # print out the msg on new line even if user is typing
                print(f"\n{remote_name}: {text}")
                print("> ", end='', flush=True)
    # bind whatever error thrown to e (common practice)
    except Exception as e:
        print(f"\n[System] Receive error: {e}")
    # we use .shutdown() instead of .close() here to close one end (we don't read anymore data with recv())
    finally:
        try:
            conn.shutdown(socket.SHUT_RD)
        # suppress/ignore nonfatal errors
        except Exception:
            pass

# 
def send_loop(conn: socket.socket, my_name: str):
    # read from stdin (standard input) and send messages; use newline delimiting
    try:
        while True:
            # format (flush=True means write text to terminal immediately)
            print("> ", end='', flush=True)
            # read the text you want to send in local terminal
            line = sys.stdin.readline()
            if not line:
                # EOF 
                break
            # remove newlines
            text = line.rstrip("\n")
            # user can terminate session with "/quit"
            if text.lower() == "/quit":
                print("[System] Quitting and closing connection...")
                break
            # msg formatting
            payload = f"{my_name}: {text}".encode('utf-8') + DELIM
            # send your msg
            conn.sendall(payload)
    # catch any errors
    except Exception as e:
        print(f"\n[System] Send error: {e}")
    # same process as function above
    finally:
        try:
            conn.shutdown(socket.SHUT_WR)
        except Exception:
            pass

# create tcp listening socket helper function
def run_listener(port: int, my_name: str):
    # steps similar to previous projects
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', port))
    s.listen(1)
    print(f"[System] Listening on port {port} — waiting for one peer...")
    conn, addr = s.accept()
    print(f"[System] Connected by {addr[0]}:{addr[1]}")
    s.close()
    return conn, f"{addr[0]}"

# initialize tcp sender socket helper function
def run_connector(host: str, port: int):
    # similar setup but we are connecting to listener (host) now
    # code here is basically like the client_socket you get from .accept() socket method except on client-side now
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"[System] Connecting to {host}:{port} ...")
    conn.connect((host, port))
    print(f"[System] Connected to {host}:{port}")
    return conn, host

# driver code
def main():
    # set up CLI arguments for the program
    # argparse documentation was pretty hard to read and implement here
    # initial setup
    parser = argparse.ArgumentParser(description="P2P Chat App")
    # we want these arguments to be required when running program
    group = parser.add_mutually_exclusive_group(required=True)
    # add in custom arguments
    group.add_argument("--listen", action="store_true", help="Listen mode (accept a peer)")
    group.add_argument("--host", type=str, help="Host to connect to (client mode)")
    parser.add_argument("--port", type=int, default=5000, help="Port (default 5000)")
    parser.add_argument("--name", type=str, default="You", help="Your display name")
    args = parser.parse_args()
    # initialize connection here to avoid "possibly unbound" warning
    conn = None  

    # based on what user specified in --listen argument we either start listening or connect to a listening socket
    try:
        if args.listen:
            conn, remote = run_listener(args.port, args.name)
        else:
            conn, remote = run_connector(args.host, args.port)

        # start receiving thread (to receive messages while dishing them out)
        recv_t = threading.Thread(target=recv_loop, args=(conn, remote), daemon=True)
        recv_t.start()

        # start sender loop (runs in main/initial thread so stdin works)
        send_loop(conn, args.name)
    # error or exit detected
    except KeyboardInterrupt:
        print("\n[System] KeyboardInterrupt — exiting.")
    except Exception as e:
        print(f"[System] Error: {e}")
    finally:
        # close socket at end
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        time.sleep(0.1)
        print("[System] Connection closed. Bye!")

# calling main
if __name__ == "__main__":
    main()
