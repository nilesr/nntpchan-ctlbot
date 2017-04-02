from twisted.words.protocols import irc
import sys
import threading
import time
import json
from twisted.internet import reactor, protocol, ssl
import twisted.protocols.basic

messages = json.load(open("/dev/shm/stream", "r"))
#messages = ["TEST!!"]
channel = "#nntpchan"

class ircproto(irc.IRCClient):
    nickname = "ctlbot"
    password = "ctlbot/freenode:CHANGEME"

    def sleepAndDie(self): # We need the thread because for some reason calling quit right after we send the message results in the message not getting sent
        print("Sleeping thread started")
        time.sleep(4)
        # self.quit()
        # reactor.stop()
        reactor.callFromThread(reactor.stop)

    def signedOn(self):
        self.join(channel)

    def joined(self, channel_p):
        if channel == channel_p: # forgetting this check got me in a lot of trouble on freenode
            for m in messages:
                print("PRIVMSG " + m)
                self.msg(channel, "New message to ctl: " + m)
            t = threading.Thread(target=self.sleepAndDie)
            t.start()


class ircfac(protocol.ReconnectingClientFactory):
    protocol = ircproto

reactor.connectSSL("10.8.0.1", 9030, ircfac(), ssl.ClientContextFactory())
reactor.run()

