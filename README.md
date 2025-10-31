# Networking Projects

This repository contains multiple networking projects I built using **Python 3**, demonstrating **socket programming, TCP/IP, multithreading, HTTP requests, API's, URL + CLARG parsing, and network protocols**. These projects are cross-platform and can be run on **Windows, Linux, or macOS**. Only Windows support is provided below. Make sure you are in the program's folder to actually run it. "py" keyword can also be used instead of "python".

## SMTP + TLS Encryption Mail-Client Execution

Set up your credentials for gmail Mailserver used. You would want to provide your email address and a Gmail App Password. More on that [here.](https://support.google.com/mail/answer/185833?hl=en)
```bash
python SMTP_mail_client.py
```

## TCP/IP TMultithreaded Messaging-App Execution

Just used port 5000 as default \
**For Listener/Server:**
```bash
python P2P_chat_app.py --listen --port 5000 --name YourNameHere
```
Program allows for connection across devices (not just localhost) through IP address in --host part. \
**For Connector/Client:**
```bash
python P2P_chat_app.py --host localhost --port 5000 --name YourNameHere
```

## ICMP/TCP Pinger Execuion

Requires administrator/root privileges for ICMP raw socket access on most systems. Make sure to change hostname to whatever website you want to ping.
```bash
python ICMP_pinger.py <hostname>
```

## Multithreaded HTTP Proxy Server Exection

```bash
python HTTP_ProxyServer.py localhost
```
Only works with HTTP websites for the most part, accessible through your browser. \
You can bind it to your LAN IP or 0.0.0.0 to allow other devices to connect
**Format Example:**
http://localhost:8888/httpforever.com/

## ICMP/TCP TraceRoute Pinger Execuion

Requires administrator/root privileges for ICMP raw socket access on most systems. Make sure to change hostname to whatever website you want to ping.
```bash
python ICMP_traceroute.py <hostname>
```

## HTTP WebServer Execution

```bash
python WebServer.py
```
Access via browser assuming you host it on your computer: http://localhost:8888/index.html \
You can bind it to your LAN IP or 0.0.0.0 to allow other devices to connect.