# python's socket module
# socket -> endpoint for network communication
# defaulting to "from socket import *" gives me a wildcard import error,
# so it is not included
import socket

# Server configuration (what port server listens on, socket creation)
# .AF_NET means we are using IPV4 addressing, and:
# .SOCK_STREAM -> TCP, .SOCK_DGRAM -> UDP
serverPort = 6789
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Prepare the server socket:
# bind the socket to all interfaces (where to listen in on)
# the empty strings mean 0.0.0.0 -> all IPV4 addresses available on my local machine 
# this include loopback addr which I am using for learning purposes (127.0.0.1 or localhost)
serverSocket.bind(('', serverPort)) 
# make the socket listen for incoming connections/requests (a passive socket)
# set max length for incoming connection queue within the method parameter
serverSocket.listen(1)
# we set a timeout, so that:
# if no TCP connection after 1 second when .accept() keeps blocking -> we bypass it
serverSocket.settimeout(1.0)

# startup server msg
print(f"Server started on port {serverPort}...")

try:
    # we need to continuously accept and handle connections
    while True:
        # (ctrl + C) could work fine without this try-except block with timeout, did not work for me however 
        # could remove this try-except and just stop the terminal, or use other threading workarounds but that is too complex for this server
        try:
            # accept any incoming connections and store: (connection socket, client IP address)
            # a new socket (connectionSocket) is used to send/recieve with that particular client
            # .accept() blocks further execution and waits until given TCP connection or socket closes
            # learned a new thing about python today, the unpacking operator (*)!
            connectionSocket, addr = serverSocket.accept()
            print(f"Connection from {addr}")


            # you initialize it here before the try to avoid "possibly unbound" warnings
            # this avoids referencing it in the except clause before it is actually assigned a value
            filename = None  
            try:
                # receive the GET HTTP request (sent through a browser from the client) through the connection socket
                # recv() also has blocking behavior like .accept() and returns bytes
                # within the parameter -> how many bytes to read from TCP stream
                # decode() converts the bytes back into string using utf-8 (decode() default) which is good enough 
                # improvements: switching decode to use a different encoding format
                # improvements: reading whole msg instead of just fixed number of bytes (keep reading until end of HTTP header is detected "\r\n\r\n")
                message = connectionSocket.recv(1024).decode()
                print(f"Request: {message}")

                # split HTTP request into tokens
                parts = message.split()
                # either request is incorrect or server read it incorrectly
                # should read something like this: [GET, path, HTTPVER, etc.]
                if len(parts) < 2:
                    raise IOError("Malformed request")
                filename = parts[1]  # ex: "/index.html"

                # I'll also say that the home page will route you to the index.html path
                if filename == '/':
                    filename = '/index.html'

                # open the file associated to page pathway within HTTP request
                # I already gave an html file to be read in curr folder
                with open(filename[1:], 'r') as f:
                    outputdata = f.read()

                # send response HTTP header into socket
                # remember to encode back into bytes for TCP stream
                # learned today: CRLF -> Carriage Return Line Feed -> '/r/n'
                # carriage returns move cursor to the start of the current line, while line feeds move the cursor down a line
                header = 'HTTP/1.1 200 OK\r\n\r\n'
                connectionSocket.send(header.encode())

                # send the content of requested file to client 
                # remember to encode since data read from file is a string
                # added 1 CRLF instead of 2 here since this is the body of HTTP response 
                connectionSocket.send(outputdata.encode())
                connectionSocket.send("\r\n".encode())

            # to catch the cases where file can't be read (not a valid path/page on server (404 response) or favicon)
            except IOError:
                # if HTTP request wants a favicon (little image on browser tab)
                if filename == '/favicon.ico':
                    # we simply ignore the request
                    pass
                else:
                    header = 'HTTP/1.1 404 Not Found\r\n\r\n'
                    body = '404 Not Found: The requested file was not found on this server.'
                    connectionSocket.send(header.encode())
                    connectionSocket.send(body.encode())
            finally:
                # for each TCP connection to a client, we need to close it's socket
                connectionSocket.close()
        # if timeout is hit/reached we skip the blocking going to next loop (interpeter can then notice a KeyBoardInterrupt) 
        except socket.timeout:
            continue
# for user termination of server (ctrl + C)
except KeyboardInterrupt:
    print("\nServer shutting down...")

# close our listening server socket (deallocates it and releases port/OS resources for other processes to use)
serverSocket.close()

