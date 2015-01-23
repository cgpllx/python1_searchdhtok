#-*- coding:utf-8 -*-
from btdht import Parser

if __name__ == "__main__":
    parser=Parser.Parser('./torrents/5302C30A88347F10E1F0A5BF334A8AC85D545AC0.torrent')
     
    #parser=Parser.Parser('./torrents/5abfeb35aadeec51bb6bc124efe528e3a28f68c1.torrent')
    print parser.getName()
    print parser.getEncoding()
