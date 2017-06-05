#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Used in conjunction with the spead_test.slx model to test incoming data on 
the frontend of a SKARAB-based f-engine.

The data is expected to be coming from a DSIM sending normal-sized packets, 
but containing a ramp from 0:639, not actual noise data.

@author: paulp
"""
import sys
import IPython
import os
import logging
import time

from casperfpga import skarab_fpga

# FPG = '/home/paulp/bofs/ct_2017-5-26_1027.fpg'  # new ELF from the repo - 1.2s slow
# FPG = '/home/paulp/bofs/ct_2017-5-26_1202.fpg'  # old ELF from tyrone - 0.3s fast
# FPG = '/home/paulp/bofs/ct_2017-5-26_1612.fpg'  # latest ELF in the repo, on Wes's suggestion
# FPG = '/home/paulp/bofs/ct_2017-6-1_0910.fpg'  # this one exhibits BROKEN data from the HMC!!!
FPG = '/home/paulp/bofs/ct_2017-6-5_0742.fpg'
# FPG = '/home/paulp/bofs/ct_rom_2017-5-25_1111.fpg'

logging.basicConfig(level=logging.INFO)

if os.environ['CORR2UUT'].strip() == '':
    print 'CORR2UUT environment variables not found.'
    sys.exit(0)

f = skarab_fpga.SkarabFpga(os.environ['CORR2UUT'])
f.get_system_information(FPG)

INPUT_BITS = int(f.system_info['input_bits'])
OUTPUT_BITS = int(f.system_info['output_bits'])

print '.fpg built with INPUT_BITS(%i) OUTPUT_BITS(%i)' % (
    INPUT_BITS, OUTPUT_BITS)

if f.gbes[0].get_port() != 30000:
    f.gbes[0].set_port(30000)


def setup_num_xengines(num_x):
    """
    
    :param num_x: 
    :return: 
    """
    f.registers.control_ct1.write(num_x=num_x, num_x_recip=1.0 / num_x,
                                  chans_per_x=(2**INPUT_BITS / 8) / num_x)


def reset_dv_system(cycle=0):
    """
    Set up the test model to run data through the HMC block.
    :param cycle: 
    :return: 
    """
    # set up the CT
    if f.registers.control_ct1.read()['data']['num_x'] == 0:
        setup_num_xengines(8)
    f.registers.control_ct0.write(trigpos=128, gapsize=45)
    # and reset the system
    f.registers.control.write(enable=False)
    f.registers.control.write(dv_cycle=cycle)
    f.registers.control.write(sync='pulse')
    f.registers.control.write(cnt_rst='pulse')
    f.registers.control.write(enable=True)


def print_status_regs():
    """
    
    :return: 
    """
    print 'status_ct:', f.registers.status_ct.read()['data']
    print 'status_ct_rdy_err:', f.registers.status_ct_rdy_err.read()['data']
    print 'status_ct_err:', f.registers.status_ct_err.read()['data']
    print 'status_ct_err_tvg_data:', f.registers.status_ct_err_tvg_data.read()['data']
    # print 'hmcerr_oobuff:', f.registers.hmcerr_oobuff.read()['data']


def read_data_in_snap(man_valid=False, printlen=-1):
    """
    
    :param man_valid: 
    :param printlen: 
    :return: 
    """
    if 'data_in_ss' not in f.snapshots.names():
        print 'data_in_ss not found, returning'
        return
    d = f.snapshots.data_in_ss.read(man_valid=man_valid, man_trig=True)['data']
    printlen = printlen if printlen > -1 else len(d['dv'])
    for ctr in range(printlen):
        print '%5i' % ctr,
        print 'dv(%i)' % d['dv'][ctr],
        print 'f0(%4i)' % ((d['dold'][ctr] >> 48) & 65535),
        print 'f1(%4i)' % ((d['dold'][ctr] >> 32) & 65535),
        print 'f2(%4i)' % ((d['dold'][ctr] >> 16) & 65535),
        print 'f3(%4i)' % ((d['dold'][ctr] >> 00) & 65535),
        print 'f4(%4i)' % ((d['dnew'][ctr] >> 48) & 65535),
        print 'f5(%4i)' % ((d['dnew'][ctr] >> 32) & 65535),
        print 'f6(%4i)' % ((d['dnew'][ctr] >> 16) & 65535),
        print 'f7(%4i)' % ((d['dnew'][ctr] >> 00) & 65535),
        print ''


def make_collection_map(input_bits=None, output_bits=None):
    """
    Make a map for the read side that stripes the frequencies 
    over the x-engines.
    :return: 
    """
    input_bits = input_bits or INPUT_BITS
    output_bits = output_bits or OUTPUT_BITS
    numbits = input_bits - 2 - 1 + output_bits
    chanbits = input_bits - 2 - 1
    maplist = []
    for fchan in range(2**chanbits):
        chanmap = range(fchan, 2**numbits, 2**chanbits)
        maplist.extend(chanmap)
    secondbank = [val + (2 ** numbits) for val in maplist]
    maplist.extend(secondbank)
    return maplist
    stripemap = make_stripe_map()
    return [stripemap[idx] for idx in maplist]


def translate_addr(addr, shift_size=9):
    low_vaults = addr & 3
    vault_to_shift = (addr >> 2) & 3
    middle = (addr >> 4) & ((2 ** shift_size) - 1)
    upper = addr >> (4 + shift_size)
    # rv = (upper << 4 + shift_size + 2) + (vault_to_shift << shift_size + 2) + (middle << 2) + low_vaults

    rv = (upper << 4 + shift_size) + (vault_to_shift << shift_size + 2) + (middle << 2) + low_vaults

    rv_dram = rv >> 8
    rv_bank = (rv >> 4) & 15
    rv_vault = rv & 15
    # print '%04i => dram(%06i) bank(%02i) vault(%1i) = %04i' % (
    #     addr, rv_dram, rv_bank, rv_vault, rv
    # )
    return rv


def map_work(input_bits, output_bits, read_map_shift=0, verbose=False):
    """

    :param input_bits: 
    :param output_bits:
     :param read_map_shift: 
    :return: 
    """
    input_vector_bits = input_bits - 2 - 1
    input_vector_len = 2 ** input_vector_bits
    total_vector_len = 2 ** (input_vector_bits + output_bits + 1)

    write_map = range(total_vector_len)
    _read_map = make_collection_map(input_bits, output_bits)
    read_map = _read_map[total_vector_len/2:]
    read_map.extend(_read_map[0:total_vector_len/2])
    data = range(input_vector_len) * (2 ** output_bits)
    data.extend(range(1024, 1024 + input_vector_len) * (2 ** output_bits))
    assert(len(data) == len(write_map))
    read_map = ([0] * read_map_shift) + read_map
    # make the translated write map
    write_map_trans = []
    for ctr in range(len(write_map)):
        write_raw = write_map[ctr]
        write_trans = translate_addr(write_raw, input_vector_bits)
        if write_trans in write_map_trans:
            raise RuntimeError('%i - %i(%i) address already used!' % (
                ctr, write_raw, write_trans))
        write_map_trans.append(write_trans)

    # write the data into 'bram' using translated map
    bram = [0] * (max(write_map_trans) + 1)
    for ctr in range(len(write_map_trans)):
        bram[write_map_trans[ctr]] = data[write_map[ctr]]
        if verbose:
            print '%4i' % ctr, \
                'bram[%04i] <= %04i' % (write_map_trans[ctr],
                                        data[write_map[ctr]]),\
                'ZERO' if data[write_map[ctr]] == 0 else ''

    # compare conventional addressing to the mapped addresses
    vault_errors = 0
    rmt = []
    for ctr in range(len(write_map)):
        read_raw = read_map[ctr]
        read_trans = translate_addr(read_raw, input_vector_bits)
        rmt.append(read_trans)
        read_vault = read_trans & 15
        write_vault = write_map_trans[ctr] & 15
        if verbose:
            print '%4i' % ctr, \
                'wr(%04i)' % write_map[ctr], \
                'rd(%04i)' % read_raw, \
                'wr_tr(%04i, %2i)' % (write_map_trans[ctr], write_vault), \
                'rd_tr(%04i, %2i)' % (read_trans, read_vault), \
                'data(%4i)' % data[read_raw], \
                'bram(%4i)' % bram[read_trans], \
                'VAULT_ERROR' if (read_vault == write_vault) else '', \
                'DATA_ERROR' if (data[read_raw] != bram[read_trans]) else ''
        if read_vault == write_vault:
            vault_errors += 1

    read_map_trans = rmt[total_vector_len / 2:]
    read_map_trans.extend(rmt[0:total_vector_len / 2])
    return vault_errors, write_map_trans, read_map_trans


def make_stripe_map(verbose=False):
    """
    This is a write-side map to stripe the incoming data over the HMC.
    :param verbose: 
    :return: 
    """
    numbits = INPUT_BITS - 2 - 1 + OUTPUT_BITS + 1
    dram = 0
    raw = 0
    loops = (2**numbits) / 16
    address_map = []
    for loop in range(loops):
        for bank in range(4):
            for vault in [8, 9, 10, 11]:
                addr = vault + (bank << 4) + (dram << 8)
                address_map.append(addr)
                if verbose:
                    print 'raw(%i) vault(%i) bank(%i) dram(%i) addr(%i)' % (
                        raw, vault, bank, dram, addr)
                raw += 1
        dram += 1
    return address_map


def write_write_map(addrmap=None):
    """
    Write the write-map to the FPGA.
    :param addrmap: 
    :return: 
    """
    if addrmap is None:
        addrmap = make_stripe_map()
    numwords = 0
    f.registers.wrmap_control.write_int(0)
    f.registers.wrmap_control.write(sel=True)
    for ctr, vword in enumerate(addrmap):
        f.registers.wrmap_data.write(data=vword)
        f.registers.wrmap_control.write(addr=ctr, en='pulse')
        numwords += 1
    f.registers.wrmap_control.write_int(0)
    return numwords


def write_read_map(addrmap=None):
    """
    Write the read-map to the FPGA.
    :param addrmap: 
    :return: 
    """
    if addrmap is None:
        addrmap = make_stripe_map()
    numwords = 0
    f.registers.rdmap_control.write_int(0)
    f.registers.rdmap_control.write(sel=True)
    for ctr, vword in enumerate(addrmap):
        f.registers.rdmap_data.write(data=vword)
        f.registers.rdmap_control.write(addr=ctr, en='pulse')
        numwords += 1
    f.registers.rdmap_control.write_int(0)
    return numwords


def tags_to_mat(filenumber=-1):
    """

    :return: 
    """
    rawdata = f.snapshots['hmcout_ss'].read(man_trig=True,
                                            man_valid=True)['data']
    import scipy.io as sio
    import numpy as np
    rawdata['tag'] = ([0] * 100) + rawdata['tag']
    rawdata['dv'] = ([0] * 100) + rawdata['we']
    del rawdata['we']
    datadict = {}
    for key in ['tag', 'dv']:
        matvar = 'simin_%s' % key
        datadict[matvar] = {
            'time': [], 'signals': {
                'dimensions': 1,
                'values': np.array(rawdata[key], dtype=np.uint32)
            }
        }
        datadict[matvar]['signals']['values'].shape = (len(rawdata[key]), 1)
    if filenumber == -1:
        filename = '/tmp/hmc_tags.mat'
    else:
        filename = '/tmp/hmc_tags_%03i.mat' % filenumber
    sio.savemat(filename, datadict)


def get_tags():
    """
    Get the tags from the output data snapshot.
    :return: 
    """
    if 'hmcout_ss' not in f.snapshots.names():
        print 'hmcout_ss not found, returning'
        return
    return f.snapshots['hmcout_ss'].read(man_trig=True)['data']['tag']


def check_output_tags():
    """
    The tag is put in the data and run through the output reorder. Are they
    correctly reordered?
    :return: 
    """
    if 'output_ss' not in f.snapshots.names():
        print 'output_ss not found, returning'
        return
    d = f.snapshots['output_ss'].read(man_trig=True, man_valid=False)['data']
    prevtag = d['tag'][0] - 1
    if prevtag == -1:
        prevtag = (2 ** OUTPUT_BITS) - 1
    tag_errors = 0
    error_indices = []
    tagdiffs = []
    for ctr in range(len(d['tag'])):
        newtag = d['tag'][ctr]
        if newtag == 0:
            if (prevtag != 511) and (ctr != 0):
                print 'TAG_ERROR1(%i, %i)' % (prevtag, newtag)
                tag_errors += 1
                error_indices.append(ctr)
        else:
            if newtag != prevtag + 1:
                print 'TAG_ERROR2(%i, %i)' % (prevtag, newtag)
                tag_errors += 1
                error_indices.append(ctr)
        dif = newtag - prevtag
        if dif not in tagdiffs:
            tagdiffs.append(dif)
        prevtag = newtag
    print '%i tag errors in %i total' % (tag_errors, len(d['tag'])), time.time()
    if tag_errors > 0:
        for ctr in range(len(d['tag'])):
            print '%5i' % ctr,
            for k in d.keys():
                print '%s(%i)' % (k, d[k][ctr]),
            print ''
        return error_indices

    # print tagdiffs
    # if tag_errors == 0:
    #     return
    # for erridx in error_indices:
    #     print '*' * 50, 'ERR at', erridx
    #     for ctr in range(erridx-5, erridx+5):
    #         print '%5i' % ctr,
    #         for k in d.keys():
    #             print '%s(%i)' % (k, d[k][ctr]),
    #         print ''


def check_mapped_output():
    """
    Check that the data is correct after it's been mapped.
    :return: 
    """
    if 'output_ss' not in f.snapshots.names():
        print 'output_ss not found, returning'
        return
    d = f.snapshots['output_ss'].read(man_trig=True,
                                      man_valid=False)['data']
    prev_f0 = d['d0_1'][0]
    prev_ctr = 0
    step_errors = 0
    ct_len_errors = 0
    tag_errors = 0
    last_tag = -8
    for ctr in range(len(d['d0_1'])):
        new_f0 = d['d0_1'][ctr]
        if prev_f0 != new_f0:
            if new_f0 % 8 == 6:
                last_tag = d['d0_0'][ctr] - 8
            ct_len = ctr - prev_ctr
            print '%5i' % ctr, '%5i' % prev_f0, '%5i' % new_f0, '%5i' % ct_len, int(new_f0 / 64),
            if (new_f0 != prev_f0 + 1) and (new_f0 != 0 and prev_f0 != 1023):
                step_errors += 1
                print 'STEP_ERROR',
            if ct_len != 32:
                ct_len_errors += 1
                print 'LEN_ERROR',
            prev_ctr = ctr
            print ''
        if new_f0 % 8 == 6:
            this_tag = d['d0_0'][ctr]
            if (this_tag != last_tag + 8) and (ctr > 0):
                print '%5i' % ctr, '%5i' % last_tag, '%5i' % this_tag, 'TAG_ERROR'
                tag_errors += 1
            last_tag = this_tag
        prev_f0 = d['d0_1'][ctr]
    print step_errors, ct_len_errors, tag_errors
    return step_errors + (ct_len_errors>1) + tag_errors


def check_output_data():
    """
    Check that the data in the output buffer makes sense.
    :return: 
    """
    if 'output_ss' not in f.snapshots.names():
        print 'output_ss not found, returning'
        return
    d = f.snapshots['output_ss'].read(man_trig=True,
                                      man_valid=False)['data']
    prevf0 = d['f0'][0] - 8
    if prevf0 == -8:
        prevf0 = 1016
    errors = 0
    error_indices = []
    diffs = []
    for ctr in range(len(d['f0'])):
        newf0 = d['f0'][ctr]
        f0diff = newf0 - prevf0
        if newf0 == 0:
            if prevf0 != 1016:
                print 'F0_ERROR(%i, %i, %i)' % (prevf0, newf0, f0diff)
                errors += 1
                error_indices.append(ctr)
        else:
            if newf0 != prevf0 + 8:
                print 'F0_ERROR(%i, %i, %i)' % (prevf0, newf0, f0diff)
                errors += 1
                error_indices.append(ctr)
        dif = newf0 - prevf0
        if dif not in diffs:
            diffs.append(dif)
        prevf0 = newf0
    print '%i errors in %i total' % (errors, len(d['f0'])), time.time()
    return errors


def check_output_data_mapped():
    """
    Check that the data in the output buffer makes sense.
    :return: 
    """
    if 'output_ss' not in f.snapshots.names():
        print 'output_ss not found, returning'
        return
    d = f.snapshots['output_ss'].read(man_trig=True,
                                      man_valid=False)['data']
    last_f0 = d['f0'][0]
    start_idx = -1
    errors = 0
    error_indices = []
    for ctr in range(len(d['f0'])):
        current_f0 = d['f0'][ctr]
        if current_f0 != last_f0:
            pkt_len = ctr - start_idx
            if (pkt_len != 256) and (start_idx != -1):
                print '%i - F0_ERROR_1(%i, %i, %i)' % (
                    ctr, last_f0, d['f0'][ctr], pkt_len)
                errors += 1
                error_indices.append(ctr)
            if (current_f0 != last_f0 + 8) and \
                    ((current_f0 != 0) and (last_f0 != 1016)):
                print '%i - F0_ERROR_2(%i, %i, %i)' % (
                    ctr, last_f0, d['f0'][ctr], pkt_len)
                errors += 1
                error_indices.append(ctr)
            start_idx = ctr
            last_f0 = current_f0
    print '%i errors in %i total' % (errors, len(d['f0'])), time.time()
    return errors


def read_hmc_readwrite_snap(printlen=-1, only_rd_en=False, only_wr_en=False):
    snapname = 'hmc_readwrite_ss'
    if snapname not in f.snapshots.names():
        print '%s not found, returning' % snapname
        return
    d = f.snapshots[snapname].read(man_trig=True, man_valid=True)['data']
    printlen = printlen if printlen > -1 else len(d[d.keys()[0]])
    for ctr in range(printlen):
        if only_rd_en and (not d['rd_en'][ctr]):
            continue
        if only_wr_en and (not d['wr_en'][ctr]):
            continue
        print '%5i' % ctr,
        # misc
        wr_rdy = d['wr_rdy'][ctr]
        rd_rdy = d['rd_rdy'][ctr]
        print 'wr_rdy(%i)' % wr_rdy,
        print 'rd_rdy(%i)' % rd_rdy,
        # write
        print '   ||||   ',
        print 'wr_en(%i)' % d['wr_en'][ctr],
        print 'wr_addr(%6i)' % d['wr_addr'][ctr],
        for ctr2 in range(6):
            print 'd%i(%4i)' % (ctr2, d['d%i' % ctr2][ctr]),
        # read
        print '   ||||   ',
        print 'rd_en(%i)' % d['rd_en'][ctr],
        print 'rd_addr(%6i)' % d['rd_addr'][ctr],
        print 'tag(%3i)' % d['tag'][ctr],
        # errors
        print '   ||||   ',
        if (wr_rdy == 0) or (rd_rdy == 0):
            print 'RDY_ERROR(%i,%i)' % (wr_rdy, rd_rdy),
        val_error = (d['d1'][ctr] != d['d0'][ctr] + 1) or \
            (d['d2'][ctr] != d['d1'][ctr] + 1) or \
            (d['d3'][ctr] != d['d2'][ctr] + 1) or \
            (d['d4'][ctr] != d['d3'][ctr] + 1) or \
            (d['d5'][ctr] != d['d4'][ctr] + 1)
        if val_error and (d['wr_en'][ctr] == 1):
            print 'VAL_ERROR',
        print ''


def read_waddrs_snap(printlen=-1):
    if 'waddrs_ss' not in f.snapshots.names():
        print 'waddrs_ss not found, returning'
        return
    d = f.snapshots.waddrs_ss.read(man_trig=True, man_valid=True)['data']
    printlen = printlen if printlen > -1 else len(d['waddr_raw'])
    for ctr in range(printlen):
        print ctr, d['dv'][ctr], d['waddr_raw'][ctr], d['waddr_map'][ctr]


def read_output_snap(printlen=-1, man_valid=False, man_trig=True):
    snapname = 'output_ss'
    if snapname not in f.snapshots.names():
        print '%s not found, returning' % snapname
        return
    d = f.snapshots[snapname].read(man_trig=man_trig,
                                   man_valid=man_valid)['data']
    printlen = printlen if printlen > -1 else len(d[d.keys()[0]])
    data_errors = 0
    for ctr in range(printlen):
        print '%5i' % ctr,
        print 'trig(%i)' % d['trig'][ctr],
        print 'dv(%i)' % d['dv'][ctr],
        print 'pkt_start(%i)' % d['pkt_start'][ctr],
        print 'd0_0(%4i)' % d['d0_0'][ctr],
        print 'd0_1(%4i)' % d['d0_1'][ctr],
        print 'd1_0(%4i)' % d['d1_0'][ctr],
        print 'd1_1(%4i)' % d['d1_1'][ctr],
        print 'd7_0(%4i)' % d['d7_0'][ctr],
        print 'd7_1(%4i)' % d['d7_1'][ctr],
        if (d['d0_1'][ctr] != d['d7_1'][ctr]) or \
                (d['d0_1'][ctr] != d['d1_1'][ctr]):
            print 'DATA_ERROR',
            data_errors += 1
        print ''
    print data_errors


def read_hmcout_snap(printlen=-1, man_valid=False, man_trig=True,
                     no_trig=False):
    snapname = 'hmcout_ss'
    if snapname not in f.snapshots.names():
        print '%s not found, returning' % snapname
        return
    if no_trig:
        d = f.snapshots[snapname].read(arm=False)['data']
    else:
        d = f.snapshots[snapname].read(man_trig=man_trig,
                                       man_valid=man_valid)['data']
    printlen = printlen if printlen > -1 else len(d[d.keys()[0]])
    for ctr in range(printlen):
        print '%5i' % ctr,
        print 'dv(%i)' % d['dv'][ctr],
        print 'sync(%i)' % d['sync'][ctr],
        print 'rd_rdy(%i)' % d['rd_rdy'][ctr],
        print 'wr_rdy(%i)' % d['wr_rdy'][ctr],
        print 'tag(%3i)' % d['tag'][ctr],
        for ctr2 in range(8):
            print 'f%i(%4i)' % (ctr2, d['f%i' % ctr2][ctr]),
        for ctr2 in range(3):
            print 'p1_f%i(%4i)' % (ctr2, d['p1_f%i' % ctr2][ctr]),
        val_error = (d['f1'][ctr] != d['f0'][ctr] + 1) or \
            (d['f2'][ctr] != d['f1'][ctr] + 1) or \
            (d['f3'][ctr] != d['f2'][ctr] + 1) or \
            (d['f4'][ctr] != d['f3'][ctr] + 1) or \
            (d['f5'][ctr] != d['f4'][ctr] + 1) or \
            (d['f6'][ctr] != d['f5'][ctr] + 1) or \
            (d['f7'][ctr] != d['f6'][ctr] + 1) or \
            (d['p1_f1'][ctr] != d['p1_f0'][ctr] + 1) or \
            (d['p1_f2'][ctr] != d['p1_f1'][ctr] + 1)
        if val_error and (d['dv'][ctr] == 1):
            print 'VAL_ERROR',
        print ''


def read_wraddr_conv_snap(printlen=-1, man_valid=False):
    _gen_read_snap('wr_addr_conv_ss', printlen, man_valid)


def read_rdaddr_conv_snap(printlen=-1, man_valid=False):
    _gen_read_snap('rd_addr_conv_ss', printlen, man_valid)


def _gen_read_snap(snapname, printlen=50, man_valid=False, man_trig=False):
    if snapname not in f.snapshots.names():
        print '%s not found, returning' % snapname
        return
    d = f.snapshots[snapname].read(man_trig=man_trig,
                                   man_valid=man_valid)['data']
    printlen = printlen if printlen > -1 else len(d[d.keys()[0]])
    for ctr in range(printlen):
        print '%5i' % ctr,
        for k in d.keys():
            print '%s(%i)' % (k, d[k][ctr]),
        print ''

# reset_dv_system()
# write_write_map()
# write_read_map()
# f.registers.control.write(enable=1)

IPython.embed()

# end
