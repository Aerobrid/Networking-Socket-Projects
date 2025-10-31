# Networking Projects

This repository contains multiple networking projects I built using **Python 3**, demonstrating **socket programming, TCP/IP, multithreading, HTTP requests, API's, URL + CLARG parsing, and network protocols**. These projects are cross-platform and can be run on **Windows, Linux, or macOS**. Only Windows support is provided below. Make sure you are in the program's folder to actually run it. "py" keyword can also be used instead of "python".

## SMTP + TLS Encryption Mail-Client Execution

Set up your credentials for gmail Mailserver used. You would want to provide your email address and a Gmail App Password. More on that [here.](https://support.google.com/mail/answer/185833?hl=en)
```bash
python SMTP_mail_client.py
```

## TCP/IP TMultithreaded Messaging-App Execution

**For Listener/Server:**
```bash
python P2P_chat_app.py --listen --port 5000 --name YourNameHere
```

**For Connector/Client:**
```bash
python P2P_chat_app.py --host <IP_ADDRESS> --port 5000 --name YourNameHere
```

## ICMP/TCP TraceRoute Pinger Execuion

Requires administrator/root privileges for ICMP raw socket access on most systems.
```bash
python ICMP_traceroute.py <hostname>
```

## Multithreaded HTTP Proxy Server Exection

```bash
python HTTP_ProxyServer.py localhost
```
Access via browser assuming you host it on your computer: http://localhost:8888/index.html

## HTTP WebServer Execution

```bash
python WebServer.py
```
Only works with HTTP websites for the most part.
The format via browser assuming you host it on your computer: http://localhost:8888/httpforever.com/




