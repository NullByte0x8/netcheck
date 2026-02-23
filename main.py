#!/usr/bin/python3

import socket
import sys
import time
import random
import os
import getopt
# import dns  # dnspython, pypi, 2.2.1

iplistdir = "/var/lib/netcheck/domains"
successcount = 10
healthPercentage = 100
mode = 1  # 1 = TCP on port 80; 2 = DNS check; 3 = ICMP echo
tcpweight = 33
dnsweight = 33
icmpweight = 33
totalweight = tcpweight + dnsweight + icmpweight
highestweight = max(tcpweight, dnsweight, icmpweight)
lowestweight = min(tcpweight, dnsweight, icmpweight)

try:
    opts, args = getopt.getopt(sys.argv, "hm:", ["help", "mark="])
except getopt.GetoptError:
    print("netcheck.py -m:<SO_MARK value> | netcheck.py --mark=<SO_MARK value>")
    sys.exit(2)
for opt, arg in opts:
    if opt in ("-h", "--help"):
        print("netcheck.py -m:<SO_MARK value> | netcheck.py --mark=<SO_MARK value>")
        sys.exit()
    elif opt in ("-m", "--mark"):
        mark = arg

while True:
    # moderandomizer = random.randint(1, 100)
    # if moderandomizer <= 33:
    #    mode = 1
    # elif 33 < moderandomizer < 66:
    #    mode = 2
    # elif moderandomizer >= 66:
    #    mode = 3
    try:
        healthPercentage = successcount / 10 * 100
    except ZeroDivisionError:
        healthPercentage = 100
    print("health %: " + str(healthPercentage) + "; success count:" + str(successcount))
    if successcount >= 10:
        successcount -= 1
    try:
        if mode == 1:  # TCP on port 80
            s = socket.socket()
            s.getsockopt(socket.SOL_SOCKET, socket.SO_MARK, )
            s.settimeout(0.5)
            host = random.choice(os.listdir(iplistdir))
            port = 80
            print("connecting to: " + host + " on port " + str(port))
            try:
                s.connect((host, port))
            except OSError:
                pass
            try:
                if s.getpeername():
                    print("connection successful")
                    if successcount < 10:
                        successcount += 1
                        s.close()
                    else:
                        print("connection unsuccessful")
                        if successcount > 0:
                            successcount -= 1
                        s.close()
            except OSError:
                print("connection unsuccessful")
                if successcount > 0:
                    successcount -= 1
                    s.close()
        # add other modes
    except KeyboardInterrupt:
        print("exiting...")
        sys.exit()
    time.sleep(0.5)
