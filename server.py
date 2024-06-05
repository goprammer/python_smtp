import socket
import asyncio
import os
import datetime as dt

HOST = "localhost"
PORT = 2525
ReadTimeout = 10.0

def parseEmailAddress(s):
    i = s.find(":")
    if i == -1 or i+1 >= len(s):
        return ()
    
    s = s[i+1:].strip("<").strip(">")
    
    i = s.find("@")
    if i == -1 or i+1 >= len(s):
       return ()

    return (s[:i], s[i+1:])

def getRFCResponse(keyword, msg):
    request_response = {
        "HELO": "250 " + msg + " Ready to serve\r\n",
        "MAIL": "250 sender " + msg + " OK\r\n",
        "RCPT": "250 recipient " + msg + " OK\r\n",
        "DATA": "354 Ready for data; end with <CRLF>.<CRLF>\r\n",
        ".": "250 message sent\r\n",
        "QUIT": "221 Good bye\r\n",
    }

    try:
        return bytes(request_response[keyword], "utf-8")
    except Exception as err:
        print("Error: Received unknown command from client -",err)
        return bytes("500 Unknown command\r\n", "utf-8")

class DiskWriter():
    def writeToDisk(self):
        if self._to[0] == "" or self._to[1] == "":
            return

        delivered_to =  "Delivered-To: <{}@{}>\n".format(self._to[0], self._to[1])
        return_path = "Return-Path: <{}@{}>\n".format(self._from[0], self._from[1])
        received = "Received: {}\n".format(dt.datetime.now(dt.UTC)
            .astimezone().strftime("%a %B %d, %Y %H:%M:%S %z"))
        
        W = len(return_path) + len(delivered_to) + len(received)
        S = W            
        W += len(list(bytes(self._data, "utf-8")))
        self._data = self._data.strip()
        self._data = self._data.replace("\r","")
        S += len(list(bytes(self._data, "utf-8")))
        filename = str((dt.datetime.now(dt.UTC) - dt.datetime(1970, 1, 1,0,0,0,0, dt.UTC))
            .total_seconds()) + ",S=" + str(S) + ",W=" + str(W)
        os.makedirs(os.path.join("mailbox", self._to[1], self._to[0]), exist_ok=True)
        with open(os.path.join("mailbox", self._to[1], self._to[0], filename), "w") as f:
            f.write(delivered_to)
            f.write(return_path)
            f.write(received)
            f.write("\n")
            f.write(self._data)

class Mail(DiskWriter):
    def __init__(self, starttime):
        self._dataready = False
        self._data = ""
        self._starttime = starttime

    def smtpAction(self, keyword, msg):
        if keyword == ".":
            self._dataready = False
            self.writeToDisk()
            return getRFCResponse(keyword, msg)
        elif self._dataready:
            self._data += keyword
            if msg != "":
                self._data += " " 
                self._data += msg 
            
            self._data += "\n"
            if len(self._data) > 3 and self._data[-3:] == "\r\n.":
                return self.smtpAction(".", "")
            else:
                return bytes()
        elif keyword == "MAIL":
            self._from = parseEmailAddress(msg)
            return getRFCResponse(keyword, msg)
        elif keyword == "RCPT":
            self._to = parseEmailAddress(msg)
            return getRFCResponse(keyword, msg)
        elif keyword == "DATA":
            self._dataready = True
            return getRFCResponse(keyword, msg)
        elif keyword == "HELO":
            return getRFCResponse(keyword, msg)
        elif keyword == "QUIT":
            return getRFCResponse(keyword, msg)

    def timed_out(self):
        if (dt.datetime.now() - self._starttime).total_seconds() > 10:
            return  True
        else: 
            return False

async def line_reader(reader, writer):
    m = Mail(dt.datetime.now())
    try:
        async with asyncio.timeout(ReadTimeout):
            async for line in reader:
                ws = line.find(32)
                keyword = line[:ws].decode("utf-8").strip()
                msg = line[ws:].decode("utf-8").strip()
                res = m.smtpAction(keyword, msg)
                writer.write(res)
                
                await writer.drain()
                
                if keyword == "QUIT":
                    break 

    except TimeoutError:
        print("Read timed out.")
        writer.write(bytes("221 Timed  out. Connection closed.\r\n", "utf-8"))
        await writer.drain()

    finally:
        writer.close()        

async def server():
    print("Simple SMTP listening on {}:{}".format(HOST,PORT))
    server = await asyncio.start_server(line_reader, HOST, PORT)
    async with server:
        await server.serve_forever()

async def main():
    task = asyncio.create_task(server()) 
    try:
        await asyncio.Future()  
    except asyncio.CancelledError as err:
        print("ctrl C received")
        task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
