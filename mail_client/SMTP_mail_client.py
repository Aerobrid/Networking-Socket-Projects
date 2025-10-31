# for attachments folder and environment variable loading
import os
# used to create a TLS wrapper around socket for encrypted communication to gmail server
# RFC 4648 supported
import ssl
# since SMTP is limited to 7-bit ASCII, 
# we need to base64 encode any binary data (attachments like videos, pdfs, etc.) that exceeds limit (8-bit, etc.)
# so that we can send it properly through protocol and MIME code
import base64
# for tcp connections and messing with sockets (low-level networking API)
import socket
# for loading in the .env file used
from dotenv import load_dotenv

# ================= CONFIGURATION =================
# Environment variables are used here for privacy (GMAIL_USER, APP_PASSWORD, and GMAIL_RECIPIENT)
# this is easily modifiable to use hardcoded credentials or a different mail server
# To switch servers:
#   1. Change 'mailserver' to the new server's host and port
#   2. Update authentication and STARTTLS logic if needed
#   3. Optionally replace environment variable loading with direct assignment if privacy is not a concern

# load the environment variables 
load_dotenv()
gmail_user = os.getenv("GMAIL_USER")
app_password = os.getenv("APP_PASSWORD")
recipient = os.getenv("GMAIL_RECIPIENT")

# Validate credentials (list comprehension used, still confusing to look at haha)
missing = [
    name for name, val in (
        ("GMAIL_USER", gmail_user),
        ("APP_PASSWORD", app_password),
        ("GMAIL_RECIPIENT", recipient),
    ) if not val
]

# to avoid None values in credentials, which would cause .encode() to fail in later parts
# error avoided (pylance may make you see it) -> AttributeError: 'NoneType' object has no attribute 'encode'
# if using this method of talking to gmail server, make sure you are using your credentials!
if missing:
    raise EnvironmentError(
        f"Missing environment variables: {', '.join(missing)}. "
        "Please set them in your .env file."
    )

# Email subject and body (message)
subject = "Custom Python SMTP Client with Optional Attachments"
body = """Hello!

This email was sent using my own Python SMTP client that:
- Connects securely via STARTTLS
- Authenticates using AUTH LOGIN
- Sends text and all files from the 'attachments' folder

Best,
Aerobrid
"""

# ================= MIME MESSAGE FORMATTING =================
boundary = "BOUNDARY123"                                     # boundary = text/attachments separator in MIME (to handle multipart messages)
msg = f"""From: {gmail_user}                                 
To: {recipient}                                             
Subject: {subject}
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary={boundary}          
--{boundary}
Content-Type: text/plain; charset="utf-8"

{body}
"""
# Content-Type needs to know what the boundary name is so it can read it after the "--"

# attach all the files from 'attachments' folder to our msg
attachments_dir = "attachments"
if os.path.exists(attachments_dir) and os.path.isdir(attachments_dir):
    # loop through files
    for filename in os.listdir(attachments_dir):
        filepath = os.path.join(attachments_dir, filename)
        # check if file valid
        if os.path.isfile(filepath):
            # read file in binary mode for: binary data -> base64encode -> ASCII bytes -> ASCII string
            # return a string with .decode() ('aG8', not b'aG8') 
            with open(filepath, "rb") as f:
                encoded_file = base64.b64encode(f.read()).decode()
            # infer content type (ctype) based on file extension (simplified)
            if filename.lower().endswith((".jpg", ".jpeg")):
                ctype = "image/jpeg"
            elif filename.lower().endswith(".png"):
                ctype = "image/png"
            elif filename.lower().endswith(".gif"):
                ctype = "image/gif"
            else:
                ctype = "application/octet-stream"

            msg += f"""
--{boundary}
Content-Type: {ctype}; name="{filename}"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="{filename}"

{encoded_file}
"""

# End MIME multipart message
msg += f"\r\n--{boundary}--\r\n"
# SMTP terminator for message content (the period ends the DATA phase)
endmsg = "\r\n.\r\n"

# ================= SMTP CONNECTION =================
# hostname and port to connect to
mailserver = ("smtp.gmail.com", 587)
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientSocket.connect(mailserver)
# print out mailserver greeting to terminal FROM BYTES -> STRING 
# Reminder: all client-server communication here happens over TCP sockets using bytes
# IMPROVEMENT: you can call a helper to read SMTP reply correctly instead of reading 1st 1024 bytes
print("[+] Connected to server:", clientSocket.recv(1024).decode())

# EHLO (Extended Hello) tells the mail server: “Hello, I’m an SMTP client.”
# The server responds with its capabilities (CHUNKING, PIPELINING, SIZE, STARTTLS, etc.)
clientSocket.send(b"EHLO Aerobrid\r\n")
print("[+] EHLO:", clientSocket.recv(1024).decode())

# STARTTLS (ask the mailserver for TLS encryption upgrade)
# print server response (220 OK)
clientSocket.send(b"STARTTLS\r\n")
print("[+] STARTTLS:", clientSocket.recv(1024).decode())

# Wrap socket in TLS
context = ssl.create_default_context()
clientSocket = context.wrap_socket(clientSocket, server_hostname="smtp.gmail.com")

# EHLO again after TLS to identify user as SMTP client
# this is needed again because the SMTP session is reset to initial state following the TLS handshake
# print server response
clientSocket.send(b"EHLO Aerobrid\r\n")
print("[+] EHLO (TLS):", clientSocket.recv(1024).decode())

# AUTH LOGIN
# The order this process goes in:
# 1. you send an AUTH LOGIN SMTP command to server and then in return it expects credentials in base64 format
# 2. the server asks for valid client email and password with corresponding 334 codes
# 3. provide them through proper conversion: original string -> UTF-8 encoding (ASCII backwards-compatible) -> binary data -> base64encode -> ASCII bytes 
# 4. passes if server replies with: 235 - Authentication successful
# print server response
clientSocket.send(b"AUTH LOGIN\r\n")
print("[+] AUTH:", clientSocket.recv(1024).decode())

clientSocket.send(base64.b64encode(gmail_user.encode()) + b"\r\n")
print("[+] USER:", clientSocket.recv(1024).decode())

clientSocket.send(base64.b64encode(app_password.encode()) + b"\r\n")
auth_reply = clientSocket.recv(1024).decode()
print("[+] PASS:", auth_reply)
if not auth_reply.startswith("235"):
    raise Exception("Authentication failed! Check your Gmail app password.")

# MAIL FROM SMTP command specifies the sender (client) email address
# print server response (250 OK)
clientSocket.send(f"MAIL FROM:<{gmail_user}>\r\n".encode())
print("[+] MAIL FROM:", clientSocket.recv(1024).decode())

# RCPT TO SMTP command specifies what the destination email address is
# print server response (250 OK)
clientSocket.send(f"RCPT TO:<{recipient}>\r\n".encode())
print("[+] RCPT TO:", clientSocket.recv(1024).decode())

# DATA SMTP command tells server if it is okay now to send mail data
# if its okay (reply back is a 354 Go ahead), we send out msg and the final line containing "." to end mail data transfer
# print server response (250 OK)
clientSocket.send(b"DATA\r\n")
data_reply = clientSocket.recv(1024).decode()
print("[+] DATA:", data_reply)
if not data_reply.startswith("354"):
    raise Exception("Server is not ready for DATA phase of SMTP connection")

clientSocket.sendall(msg.encode())
clientSocket.send(endmsg.encode())
print("[+] MESSAGE SENT:", clientSocket.recv(1024).decode())

# QUIT SMTP command sends a request to end the SMTP connection
# server must reply back with a "221 OK"
clientSocket.send(b"QUIT\r\n")
print("[+] QUIT:", clientSocket.recv(1024).decode())

# close the socket  
clientSocket.close()
print("[✓] Connection closed successfully.")
