# encoding: utf-8
# ！/usr/bin
#!/usr/bin/env python
import socket
import logging
from hashlib import sha1
from random import randint
from struct import unpack, pack
from socket import inet_aton, inet_ntoa
from threading import Timer, Thread
from time import sleep
from bencode import bencode, bdecode

stdger = logging.getLogger("std_log")
fileger = logging.getLogger("file_log")

BOOTSTRAP_NODES = [
    ("router.bittorrent.com", 6881),
    ("dht.transmissionbt.com", 6881),
    ("router.utorrent.com", 6881)
] 

TID_LENGTH = 4
RE_JOIN_DHT_INTERVAL = 10
THREAD_NUMBER = 3

def initialLog():

    stdLogLevel = logging.DEBUG
    fileLogLevel = logging.DEBUG
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stdout_handler = logging.StreamHandler()
    stdout_handler.setFormatter(formatter)
    file_handler = logging.FileHandler("HASH.log")
    file_handler.setFormatter(formatter)
    logging.getLogger("file_log").setLevel(fileLogLevel)
    logging.getLogger("file_log").addHandler(file_handler)
    logging.getLogger("std_log").setLevel(stdLogLevel)
    logging.getLogger("std_log").addHandler(stdout_handler)

def entropy(length):
    chars = []
    for i in range(length):
        chars.append(chr(randint(0, 255)))
    return "".join(chars)
    # """把爬虫"伪装"成正常node, 一个正常的node有ip, port, node ID三个属性, 因为是基于UDP协议,   
    # 所以向对方发送信息时, 即使没"明确"说明自己的ip和port时, 对方自然会知道你的ip和port,   
    # 反之亦然. 那么我们自身node就只需要生成一个node ID就行, 协议里说到node ID用sha1算法生成,   
    # sha1算法生成的值是长度是20 byte, 也就是20 * 8 = 160 bit, 正好如DHT协议里说的那范围: 0 至 2的160次方,   
    # 也就是总共能生成1461501637330902918203684832716283019655932542976个独一无二的node.   
    # ok, 由于sha1总是生成20 byte的值, 所以哪怕你写SHA1(20)或SHA1(19)或SHA1("I am a 2B")都可以,   
    # 只要保证大大降低与别人重复几率就行. 注意, node ID非十六进制,   
    # 也就是说非FF5C85FE1FDB933503999F9EB2EF59E4B0F51ECA这个样子, 即非hash.hexdigest().
def random_id():  # 创建自己的nodeId,
    hash = sha1()
    hash.update(entropy(20))
    return hash.digest()

def decode_nodes(nodes):
    n = []
    length = len(nodes)
    if (length % 26) != 0: 
        return n

    for i in range(0, length, 26):
        nid = nodes[i:i + 20]
        ip = inet_ntoa(nodes[i + 20:i + 24])
        port = unpack("!H", nodes[i + 24:i + 26])[0]
        n.append((nid, ip, port))

    return n

def timer(t, f):
    Timer(t, f).start()

def get_neighbor(target, end=10):
    return target[:end] + random_id()[end:]


class DHT(Thread):
    def __init__(self, master, bind_ip, bind_port, max_node_qsize):
        Thread.__init__(self)

        self.setDaemon(True)
        self.isServerWorking = True
        self.isClientWorking = True
        self.master = master
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.max_node_qsize = max_node_qsize
        self.table = KTable()
        self.ufd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.ufd.bind((self.bind_ip, self.bind_port))
        self.server_thread = Thread(target=self.server)
        self.client_thread = Thread(target=self.client)
        self.server_thread.daemon = True
        self.client_thread.daemon = True

        timer(RE_JOIN_DHT_INTERVAL, self.join_DHT)

    def start(self):
        self.server_thread.start()
        self.client_thread.start()
        Thread.start(self)
        return self

    def server(self):
        self.join_DHT()
        while self.isServerWorking:

            try:
                (data, address) = self.ufd.recvfrom(65536)
                msg = bdecode(data)
                stdger.debug("receive udp packet")
                self.on_message(msg, address)
            except Exception:
                pass

    def client(self):
        while self.isClientWorking:

            for node in list(set(self.table.nodes))[:self.max_node_qsize]:
                stdger.debug("send packet")
                self.send_find_node((node.ip, node.port), node.nid)

            # is the list in python thread-safe
            size = len(self.table.nodes)
            head = size - self.max_node_qsize

            if head < 0:
                head = 0
            self.table.nodes = self.table.nodes[head : size]
            sleep(1)

    def on_message(self, msg, address):
        try:
            print msg
            if msg["y"] == "r":
                if msg["r"].has_key("nodes"):
                    self.process_find_node_response(msg, address)

            elif msg["y"] == "q":
                if msg["q"] == "find_node":
                    self.process_find_node_request(msg, address)

                elif msg["q"] == "get_peers":
                    self.process_get_peers_request(msg, address)
        except KeyError, e:
            pass

    # send msg to a specified address
    def send_krpc(self, msg, address):
        try:
            # print bencode(msg)
            print msg
            self.ufd.sendto(bencode(msg), address)
            
        except:
            pass

    # send udp message
    def send_find_node(self, address, nid=None):
        nid = get_neighbor(nid) if nid else self.table.nid
        # token id
        tid = entropy(TID_LENGTH)
        # random_id() quite good idea
        msg = dict(
            t=tid,
            y="q",
            q="find_node",
            a=dict(id=nid, target=random_id())
        )
# find_node Query = {"t":"aa", "y":"q", "q":"find_node", "a": {"id":"abcdefghij0123456789", "target":"mnopqrstuvwxyz123456"}}
# bencoded = d1:ad2:id20:abcdefghij01234567896:target20:mnopqrstuvwxyz123456e1:q9:find_node1:t2:aa1:y1:qe
# Response = {"t":"aa", "y":"r", "r": {"id":"0123456789abcdefghij", "nodes": "def456..."}}
# bencoded = d1:rd2:id20:0123456789abcdefghij5:nodes9:def456...e1:t2:aa1:y1:re
        self.send_krpc(msg, address)

    # only need to send a random_id to the bootstrap node.
    def join_DHT(self):
        for address in BOOTSTRAP_NODES: 
            self.send_find_node(address)



    def   play_dead(self, tid, address):
        msg = dict(
            t=tid,
            y="e",
            e=[202, "Server Error"]
        )
        self.send_krpc(msg, address)

    def process_find_node_response(self, msg, address):
        nodes = decode_nodes(msg["r"]["nodes"])
        for node in nodes:
            (nid, ip, port) = node
            if len(nid) != 20: continue
            if ip == self.bind_ip: continue
            self.table.put(KNode(nid, ip, port))

    def process_get_peers_request(self, msg, address):
        try:
            tid = msg["t"]
            infohash = msg["a"]["info_hash"]
            print msg
            print tid
            self.master.log(infohash, address)
            self.play_dead(tid, address)
        except KeyError, e:
            pass

    def process_find_node_request(self, msg, address):
        try:
            tid = msg["t"]
            target = msg["a"]["target"]
            self.master.log(target, address)
            self.play_dead(tid, address)
        except KeyError, e:
            pass

    def stop(self):
        self.isClientWorking = False
        self.isServerWorking = False

class KTable():
    def __init__(self):
        self.nid = random_id()
        self.nodes = []

    def put(self, node):
        self.nodes.append(node)


class KNode(object):
    def __init__(self, nid, ip=None, port=None):
        self.nid = nid
        self.ip = ip
        self.port = port

    def __eq__(self, node):
        return node.nid == self.nid

    def __hash__(self):
        return hash(self.nid)


# using example
class Master(object):

    def log(self, infohash, address=None):  # infohash.encode("hex")这个是infohash
        stdger.debug("%s from %s:%s" % (infohash.encode("hex"), address[0], address[1]))
        fileger.debug('%s from %s:%s' % (infohash.encode('hex').upper(), address[0], address[1]))


if __name__ == "__main__":
    # max_node_qsize bigger, bandwith bigger, spped higher
    initialLog()
    threads = []
    for i in xrange(THREAD_NUMBER):
        port = i + 9500
        stdger.debug("start thread %d" % port)
        dht = DHT(Master(), "0.0.0.0", port, max_node_qsize=1000)
        dht.start()
        threads.append(dht)
        sleep(1)

    sleep(60 * 60 * 10)
    k = 0
    for i in threads:
        stdger.debug("stop thread %d" % k)
        i.stop()
        i.join()
        k = k + 1
