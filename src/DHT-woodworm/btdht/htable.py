# -*- coding: utf-8 -*-

import threading
import MySQLdb
import logging
import random

'''
one hash_info conrresponds  many peers
'''
fileLogger=logging.getLogger("btdht")
class HashTable(object):

    def __init__(self):#构造
        self.hashes = {}
        #the mutex to access the critical resource
        self.lock = threading.Lock()#创建一个锁
        try:                            #数据库的用户名和密码
            self.conn=MySQLdb.connect(host='127.0.0.1',user='root',passwd='',port=3306,charset="UTF8")
            self.cur=self.conn.cursor()
            self.conn.select_db('dht')#选择数据库 dht
        except MySQLdb.Error,e:
            print 'mysql error %d:%s'%(e.args[0],e.args[1])


    def add_hash(self, hash):#插入数据到数据库
        #利用with可以防止异常的问题
        with self.lock:
            if hash not in self.hashes:
                self.hashes[hash] = []#python中的和php有点像，这里下标为hash，值为空集合
                sql="insert into hash_info(hash,info) values('%s','%s')"%(hash.encode('hex'),"")#拼接sql

                try:
                    self.cur.execute(sql)#插入到数据库中
                    self.conn.commit()#提交
                    fileLogger.debug('find new hash: %s'%hash.encode('hex').upper())#插入正确有打印logo信息
                except MySQLdb.Error,e:
                    logging.debug('insert duplicate hash into mysql')#发送错误了打印logo信息


    def remove_hash(self, hash):#从self.hashes集合中删除一个 hash
        with self.lock:
            if hash in self.hashes:#hash是否在hashes中
                del self.hashes[hash]#删除

    #对某个资源添加一个peer
    def add_peer(self, hash, peer):#hash也是一个集合，里面装的是peer
        with self.lock:
            if hash in self.hashes:
                if peer not in self.hashes[hash]:
                    self.hashes[hash].append(peer)

    #never remove any peer
    def remove_peer(self):#未实现
        return

    def count_hash_peers(self, hash):#每一个节点的路由表长度
        return len(self.hashes[hash])

    #获取某个hash值对应的所有peer值
    def get_hash_peers(self, hash):
        return self.hashes[hash]#返回指定节点的全部peers,（路由表中的数据（路由表中存放的是相邻节点的信息））

    def count_hashes(self):
        return len(self.hashes)#节点数（用户数）

    def get_hashes(self):#获取所有用户
        return self.hashes

    def count_all_peers(self):#全部peer数（所有hash中的全部加起来）
        tlen = 0
        for hash in self.hashes.keys():
            tlen += len(self.hashes[hash])
        return tlen

    def closeDataBase(self):#关闭数据库
        try:
            self.cur.close()
            self.conn.close()
        except MySQLdb.Error,e:
            print 'mysql error %d:%s'%(e.args[0],e.args[1])


    def saveHashInfo(self,name):
        '''
        with open(name+"_hash_info.txt",'a') as file:
            for hash in self.hashes.keys():
                file.write(hash.encode('hex')+"\n\r")
        '''
        try:
            conn=MySQLdb.connect(host='127.0.0.1',user='root',passwd='456',port=3306,charset="UTF8")
            cur=conn.cursor()
            conn.select_db('dht')
            for hash in self.hashes.keys():
                hash_hex=(hash.encode('hex'))
                sql="insert into hash_info(hash,info) values('%s','%s')"%(hash_hex,"")
                try:
                    cur.execute(sql)
                    conn.commit()
                except MySQLdb.Error,e:
                    print 'mysql error %d:%s'%(e.args[0],e.args[1])
            cur.close()
            conn.close()
        except MySQLdb.Error,e:
            print 'mysql error %d:%s'%(e.args[0],e.args[1])
