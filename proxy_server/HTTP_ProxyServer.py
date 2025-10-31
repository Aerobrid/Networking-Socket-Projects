import socket
import sys
# to handle each client connection in a separate thread
import threading
import os
# for URL breakdown into parts
from urllib.parse import urlparse

"""
Multithreaded HTTP Proxy Server
---------------------------------------
- Accepts client HTTP requests and forwards them to the destination web server
- Caches GET responses locally for faster subsequent access 
- Handles concurrent client connections via python threading mpdule
- Supports basic HTTP error handling and graceful shutdown
"""


# convert URL to safe filename for caching purposes
def sanitize_filename(url):
    return url.replace("/", "_").replace("?", "_").replace(":", "_")

# handle each client connection (via multithreading in main loop)
# proxy server acts as the middleman with behavior shown below in function
def handle_client(client_sock, addr):
    print(f"[System] Connection from {addr}")
    try:
        # read bytes into string (through UTF-8 decoding) sent in by the client (the user) 
        # if nothing sent just close/quit
        request = client_sock.recv(8192).decode()
        if not request:
            client_sock.close()
            return

        # split request to lines based on CRLF's
        # if no lines just close/quit
        lines = request.split("\r\n")
        if len(lines) == 0:
            client_sock.close()
            return

        # something like: GET http://host/path HTTP/1.1"
        first_line = lines[0]
        try:
            method, url, protocol = first_line.split()
        except ValueError:
            # if parsing that first http request line fails then we send back a 400 Bad Request and close/quit
            # .sendall() used in program to ensure that all bytes are sent; .send() sends up to specified bytes
            # .sendall() is better for large amounts of data 
            client_sock.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            client_sock.close()
            return

        # rest of lines within request are req headers
        # I want to see it (debug reasons), so logged into terminal (just like proxyServer and client connection logs)
        headers = lines[1:]
        print(f"[Request] {method} {url}")

        # remove leading slash if it exists (some browsers prepend a slash with the URL given)
        if url.startswith("/"):
            url = url[1:]

        # PARSE URL
        # if url given does not have a scheme then we just default to using http
        parsed = urlparse(url if "://" in url else "http://" + url)
        # where we want to direct our proxy (domain)
        host = parsed.netloc
        # what path in website?
        path = parsed.path
        # if not provided, the main server's home/default path is fine
        if not path:
            path = "/"

        # set up cache path and create cache directory (folder) if it doesn't already exist
        CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
        os.makedirs(CACHE_DIR, exist_ok=True)

        # set up file inside the cache folder with proper "sanitized" filename
        cache_file = os.path.join(CACHE_DIR, sanitize_filename(url))
        print(f"[Cache] {cache_file}")

        # if GET HTTP method was read and cache file exists, we read its contents
        if method.upper() == "GET" and os.path.exists(cache_file):
            # called a "cache hit"
            print("[Cache] Hit")
            # rb -> read binary 
            with open(cache_file, "rb") as f:
                response = f.read()
            
            # if body is missing minimal HTTP headers, add them in 
            if not response.startswith(b"HTTP/"):
                response = b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n" + response

            # send all bytes -> close socket
            client_sock.sendall(response)
            client_sock.close()
            return

        # Connect to remote server client specifies
        try:
            # need the IP address for socket and TCP connection
            server_ip = socket.gethostbyname(host)
        # dns lookup case
        except socket.gaierror:
            client_sock.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            client_sock.close()
            return

        # socket creation and tcp connection to remote server on port 80
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.connect((server_ip, 80))

        # build HTTP request and ignore proxy-specific headers
        request_line = f"{method} {path} HTTP/1.1\r\n"
        forward_headers = ""
        for header in headers:
            if header.lower().startswith("proxy-connection") or header.lower().startswith("connection"):
                continue
            # make sure to always separate lines with CRLF 
            forward_headers += header + "\r\n"

        # the mandatory headers to add in
        forward_headers += f"Host: {host}\r\n"
        forward_headers += "Connection: close\r\n"
        forward_headers += "User-Agent: PythonProxy/1.0\r\n"

        full_request = request_line + forward_headers + "\r\n"

        # handle POST body (optional) 
        if method.upper() == "POST":
            body_index = request.find("\r\n\r\n")
            if body_index != -1:
                body = request[body_index + 4:]
                full_request += body

        # remember to send in bytes (binary data) through socket to remote server here
        server_sock.sendall(full_request.encode())

        # receive the response from remote server in chunks (loop it)
        response = b""
        while True:
            data = server_sock.recv(8192)
            if not data:
                break
            response += data

        # if its a GET method that client sent in, write remote server response to our cache_file
        if method.upper() == "GET":
            with open(cache_file, "wb") as f:
                f.write(response)
            print("[Cache] Saved")

        # send back response to client socket and close socket we have with remote server
        client_sock.sendall(response)
        server_sock.close()
    # catch any errors -> send error if possible
    except Exception as e:
        print(f"[Error] {e}")
        try:
            client_sock.sendall(b"HTTP/1.1 500 Internal Server Error\r\n\r\n")
        except:
            pass
    # we need to close our client socket (TCP connection)
    finally:
        client_sock.close()
        print(f"[System] Closed connection {addr}")


# main function
def main():
    # Each client connects to the proxy server; handled in a separate thread and socket
    # The proxy then opens its own socket to the target (remote) server on behalf of that client

    # argument run case
    # proxy server listens in on IP address given to it
    if len(sys.argv) <= 1:
        print('Usage: python ProxyServer.py server_ip')
        sys.exit(2)

    SERVER_IP = sys.argv[1]
    # Change if needed
    SERVER_PORT = 8888  

    # create a TCP socket for listening to client connections when they come in
    tcpSerSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcpSerSock.bind((SERVER_IP, SERVER_PORT))
    # set max number of queued TCP connections here
    tcpSerSock.listen(5)
    # allows for a graceful ctrl + C with timeout exception (since accept() has blocking behavior)
    tcpSerSock.settimeout(1.0)  
    print(f"[System] Proxy Server running on {SERVER_IP}:{SERVER_PORT}")

    # Main loop
    try:
        while True:
            try:
                # accept a TCP connection from client 
                # a new socket (client_socket) is used to send/recieve with that particular client
                client_sock, addr = tcpSerSock.accept()
            except socket.timeout:
                # timeout every second so Ctrl+C works (learned from WebServer.py)
                continue  

            print('[System] Ready to serve...')
            # create a thread for each client and run handle_client()
            threading.Thread(target=handle_client, args=(client_sock, addr), daemon=True).start()
    # close server socket and exit program
    except KeyboardInterrupt:
        print("\n[System] Shutting down proxy server...")
        tcpSerSock.close()
        sys.exit(0)

# main guard
if __name__ == "__main__":
    main()