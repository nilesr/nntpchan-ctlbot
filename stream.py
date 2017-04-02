#!/usr/bin/env python3
import subprocess
import random
import time
import string
import sys
import BTEdb
import base64
import json
user = "CHANGEME"
pw = "CHANGEME"
from twisted.internet import reactor, protocol, ssl
import twisted.protocols.basic

#debug = True
debug = True
messages = []

db = BTEdb.Database("db.json")
if not db.TableExists("main"):
    db.CreateTable("main")
    db.Insert("main", oldmax=0)
oldmax = db.Dump("main")[0]["oldmax"]


def handle_text(s, lines): # handle a text/plain encoded section
    messages.append(s + " /// " + " ".join(lines[lines.index(""):])) # subject // line1 line2 line3


def handle_part(s, lines): # handle one part of a multipart/mixed encoding
    types = [k.split()[1][:-1] for k in lines if "Content-Type:" in k]
    if types[0] == "text/plain":
        messages.append(
            s + " /// " + base64.b64decode(" ".join(lines[lines.index(""):])).decode("utf-8").replace("\n", " "))
    else:
        print(types[0] + " is not text/plain, skipping")


def handle(lines):
    if len(lines) == 0:
        return
    types = [k.split()[1][:-1] for k in lines if "Content-Type:" in k]
    subj = [" ".join(k.split()[1:]) for k in lines if "Subject:" in k][0] # grab subject
    if types[0] == "text/plain": # if it's plain, delegate that
        handle_text(subj, lines)
    elif types[0] == "message/rfc822": # if it's rfc822, extract the plain section and delegate that
        handle_text(subj, lines[lines.index("") + 1:])
    else: # otherwise split at the boundry and handle each part
        bound = [k.split()[2].replace("boundary=", "")
                 for k in lines if "multipart/mixed" in k][0]
        r = [[]]
        for l in lines:
            if l == "--" + bound:
                r.append([])
            else:
                r[-1].append(l)
        for s in r:
            handle_part(subj, s)


class client(twisted.protocols.basic.LineReceiver):
    def sl(self, line):
        if debug:
            print("Send: " + line)
        self.sendLine(line.encode("utf-8"))
    def __init__(self):
        self.max = 0
        self.min = 0
        self.in_message = False
        self.this_message = []
    def lineReceived(self, data):
        data = data.decode("utf-8")
        if debug:
            print("Recv: " + data)
        if len(data) == 0:
            self.this_message.append("")
            return
        elif self.in_message:
            if data == "." or data.split()[0] == "430":
                self.in_message = False
                handle(self.this_message)
                self.cur += 1
                if self.cur < self.max:
                    self.sl("ARTICLE " + str(self.cur))
                    self.in_message = True
                    self.this_message = []
                else:
                    db.Truncate("main")
                    db.Insert("main", oldmax=self.max)
                    self.sl("QUIT")
            else:
                self.this_message.append(data)
        data = data.split()
        if data[0] == "200":  # posting allowed
            # self.sl("AUTHINFO USER " + user)
        # if data[0] == "381":  # password required
            # self.sl("AUTHINFO PASS " + pw)
        # if data[0] == "281":  # authentication success
            self.sl("GROUP ctl")
        if data[0] == "211":  # group stats
            self.min = int(data[2])
            self.max = int(data[3])
            if self.max > oldmax:
                self.cur = oldmax + 1
                self.sl("ARTICLE " + str(oldmax + 1))
                self.in_message = True
            else:
                self.sl("QUIT")
        if data[0] == "205":  # bai
            reactor.stop()
            # sys.exit(0)


class fac(protocol.ClientFactory):
    protocol = client


# this connects the protocol to a server running on port 8000
reactor.connectTCP("10.8.0.1", 1199, fac())
reactor.run()

if len(messages) == 0:
    x = "no messages"
    open("/dev/shm/stream", "w").write(x) # just to make sure if we invoke stream2.py it will die before trying to connect
    sys.exit(0)

x = json.dumps(messages, indent=4)
open("/dev/shm/stream", "w").write(x)
subprocess.call(["python3", "stream2.py"])

