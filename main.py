#!/usr/bin/python3

import socket
import sys
import time
import random
import os
import getopt
import posix
import asyncio
# import dns  # dnspython, pypi, 2.2.1

iplistdir = "/run/netcheck/ips/latest"
pipe_path = "/run/netcheck/pipe"
successcount = 10
healthPercentage = 100
mode = 1  # 1 = TCP on port 80; 2 = DNS check; 3 = ICMP echo
tcpweight = 33
dnsweight = 33
icmpweight = 33
totalweight = tcpweight + dnsweight + icmpweight
highestweight = max(tcpweight, dnsweight, icmpweight)
lowestweight = min(tcpweight, dnsweight, icmpweight)
debug = True
stdout = False

pipe = open(pipe_path, "w")

def out(val):
    if(type(val) == int):
        pass
    else:
        raise TypeError("out(): val must be int")
        return False
    try:
        pipe.write(str(val))
        pipe.close
    except OSError as e:
        raise Exception(f"out(): {e}")
        return False

def log(msg):
    print(f"{round(time.time(), 1)} netcheck: {msg}", file=sys.stderr)
    if stdout: print(f"{time.time()} netcheck: {msg}")

try:
    posix.mkfifo(pipe_path)
    if debug: log("FIFO created")
except FileExistsError:
    if debug: log("FIFO exists, continue...")
    pass
except OSError as e:
    if debug: log(f"FIFO creation failed: {e}")
    sys.exit(2)

try:
    opts, args = getopt.getopt(sys.argv, "hdm:", ["help", "mark="])
except getopt.GetoptError:
    print("netcheck.py [-d] [-h | -m:<SO_MARK value> | netcheck.py --mark=<SO_MARK value>]")
    sys.exit(2)
for opt, arg in opts:
    if opt in ("-h", "--help"):
        print("netcheck.py [-d] [-h | -m:<SO_MARK value> | netcheck.py --mark=<SO_MARK value>]")
        sys.exit(0)
    elif opt in ("-d", "--debug"):
        debug = True
        log(f"opts: {opts}; args: {args}")
    if opt in ("-m", "--mark"):
        mark = arg
        if debug: log(f"mark: {mark}")

while True:
    # moderandomiser = random.randint(1, 100)
    # if moderandomiser <= 33:
    #    mode = 1
    # elif 33 < moderandomiser < 66:
    #    mode = 2
    # elif moderandomiser >= 66:
    #    mode = 3
    try:
        healthPercentage = successcount / 10 * 100
    except ZeroDivisionError:
        healthPercentage = 100
    log(f"health %: {str(healthPercentage)} ; success count: {str(successcount)}")
    out(int(healthPercentage))
    if successcount >= 10:
        successcount -= 1
        if mode == 1:  # TCP on port 80
            s = socket.socket()
            s.getsockopt(socket.SOL_SOCKET, socket.SO_MARK, )
            s.settimeout(0.5)
            host = random.choice(os.listdir(iplistdir))
            with open(f"{iplistdir}/{host}") as f:
                domain = f.read()
            port = 80
            log(f"connecting to: {host} ({domain.strip()}) on port {str(port)}")
            try:
                s.connect((host, port))
            except OSError:
                pass
            try:
                if s.getpeername():
                    log("connection successful")
                    if successcount < 10:
                        successcount += 1
                        s.close()
                    else:
                        log("connection unsuccessful")
                        if successcount > 0:
                            successcount -= 1
                        s.close()
            except OSError:
                log("connection unsuccessful")
                if successcount > 0:
                    successcount -= 1
                    s.close()
        # add other modes
    time.sleep(0.5)

