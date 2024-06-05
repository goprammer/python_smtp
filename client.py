import socket
import sys
import datetime as dt
import json
import time

HOST, PORT = "localhost", 2525

class Response():
    def __init__(self, b):
        ws = b.find(32)
        s = b.decode("utf-8").strip()
        if ws == -1 or ws+1 >= len(s):
            self._code = "500"
            self._msg = ""
        else:  
            self._code = s[:ws]
            self._msg = s[ws+1:]

    def __str__(self):
        return f'{self._code} {self._msg}'

    def expectedCode(self, code):
        return self._code == code

# Create a socket (SOCK_STREAM means a TCP socket)
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    timestamp = dt.datetime.now(dt.UTC).astimezone().strftime("%a %B %d, %Y %H:%M:%S %z")
    with open("mail.json", "r") as f:
        mail = json.load(f)

    sock.connect((HOST, PORT))
    
    try:
        sock.sendall(bytes("HELO client\r\n", "utf-8"))
        res = Response(sock.recv(1024))
        print(res)
        if res.expectedCode("250") == False:
            raise Exception(str(res))

        sock.sendall(bytes("MAIL FROM:<{}>\r\n".format(mail["from"]), "utf-8"))
        res = Response(sock.recv(1024))
        print(res)
        if res.expectedCode("250") == False:
            raise Exception(str(res))

        sock.sendall(bytes("RCPT TO:<{}>\r\n".format(mail["to"]), "utf-8"))
        res = Response(sock.recv(1024))
        print(res)
        if res.expectedCode("250") == False:
            raise Exception(str(res))

        sock.sendall(bytes("DATA\r\n", "utf-8"))
        res = Response(sock.recv(1024))
        print(res) 
        if res.expectedCode("354") == False:
            raise Exception(str(res))

        data = "To: " + mail["to"] + "\r\n"
        data += "From: " + mail["from"]  + "\r\n"
        data += "Date: " + timestamp + "\r\n"
        data += "Subject: " + mail["subject"] + "\r\n\r\n"
        data += mail["body"] + "\r\n.\r\n"

        sock.sendall(bytes("{}".format(data), "utf-8"))
        res = Response(sock.recv(1024))
        print(res) 
        if res.expectedCode("250") == False:
            raise Exception(str(res))

        sock.sendall(bytes("QUIT\r\n", "utf-8"))
        res = Response(sock.recv(1024))
        print(res) 


    except Exception as err:
        print("Received error code from server.")
        print("Email was not sent.")
        print(err)
    else:
        print("Email was successfully send")
