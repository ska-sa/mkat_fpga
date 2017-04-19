#!/usr/bin/env python

import struct
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', 7779))

pkts = []
for ctr in range(100):
    pkts.append(sock.recvfrom(10000))

sock.close()

# analyse the data we have received
for pkt in pkts:
    d = struct.unpack('>%iH' % (len(pkt[0]) / 2), pkt[0])
    for ctr in range(0, len(d), 16):
        try:

            marker = d[ctr + 12]
            walking_m = (d[ctr + 13] << 32) | (d[ctr + 14] << 16) | \
                        (d[ctr + 15] << 0)
            pkt_count_m = (d[ctr + 8] << 16) | (d[ctr + 9] << 0)
            ramp_m = (d[ctr + 10] << 16) | (d[ctr + 11] << 0)
            walking_l = (d[ctr + 4] << 48) | (d[ctr + 5] << 32) | \
                        (d[ctr + 6] << 16) | (d[ctr + 7] << 0)
            pkt_count_l = (d[ctr + 0] << 16) | (d[ctr + 1] << 0)
            ramp_l = (d[ctr + 2] << 16) | (d[ctr + 3] << 0)
            # for ctr2 in range(16):
            #     print '%5i' % d[ctr + ctr2],

            print '%4i' % marker,
            print '%25i' % walking_m,
            print '%25i' % walking_l,
            print '%10i' % pkt_count_m,
            print '%10i' % pkt_count_l,
            print '%10i' % ramp_m,
            print '%10i' % ramp_l,

        except IndexError:
            pass
        print ''
    print '------------------------'

# end
