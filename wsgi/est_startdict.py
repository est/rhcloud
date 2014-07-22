#!/usr/bin/env python

# coding: utf8

# http://code.google.com/p/babiloo/wiki/StarDict_format

import struct, gzip
import mmap
import glob, os

import dictzip

class StarDict(object):
    def __init__(self, dir_prefix=''):
        self.word_index = {}
        self.idx_filename = glob.glob(dir_prefix+'.idx')[0]
        self.parse_idx_file(self.idx_filename)

        self.dic_filename = glob.glob(dir_prefix+'.dict*')[0]
        self.dic_file = dictzip.DictzipFile(self.dic_filename)

        # f = open(self.dic_filename, 'rb')
        # mapped = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        # self.dic_file = gzip.GzipFile(mode="r", fileobj=mapped)


    def parse_idx_file(self, filename):
        l = os.stat(filename).st_size
        data = bytearray(l)
        f = open(filename, 'rb')
        f.readinto(data)
        f.close()
        i = 0
        while True:
            o = data.find('\0', i)
            k = str(data[i:o])
            v = struct.unpack_from('!II', buffer(data), o+1)
            self.word_index[ k ] = v
            i = o + 1 + 8 # 1 byte for 0x00 and 8 bytes for (offset, length)
            if i>= l:
                break

    def lookup(self, word=''):
        r = self.word_index.get(word, None)
        if r:
            self.dic_file.seek(r[0])
            return self.dic_file.read(r[1])
        return ''


if '__main__' == __name__:
    d = StarDict('def/stardict-dictd-web1913-2.4.2/dictd_www.dict.org_web1913')
    print d.lookup('Test')