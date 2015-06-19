from __future__ import division

import unittest
import logging

import time
import itertools

import numpy as np

from katcp.testutils import start_thread_with_cleanup
from corr2.dsimhost_fpga import FpgaDsimHost
from corr2.corr_rx import CorrRx

from mkat_fpga_tests import correlator_fixture

LOGGER = logging.getLogger(__name__)

def get_vacc_offset(xeng_raw):
    """Assuming a tone was only put into input 0, figure out if VACC is roated by 1"""
    b0 = np.abs(complexize(xeng_raw[:,0]))
    b1 = np.abs(complexize(xeng_raw[:,1]))
    if np.max(b0) > 0 and np.max(b1) == 0:
        # We expect autocorr in baseline 0 to be nonzero if the vacc is properly aligned,
        # hence no offset
        return 0
    elif np.max(b1) > 0 and np.max(b0) == 0:
        return 1
    else:
        raise ValueError('Could not determine VACC offset')

def complexize(input_data):
    """Convert input data shape (X,2) to complex shape (X)"""
    return input_data[:,0] + input_data[:,1]*1j

class test_CBF(unittest.TestCase):
    def setUp(self):
        self.receiver = CorrRx(port=8888)
        start_thread_with_cleanup(self, self.receiver, start_timeout=1)
        self.correlator = correlator_fixture.correlator
        self.corr_fix = correlator_fixture
        # Make sure the x-engines are not yet dumping
        self.corr_fix.stop_x_data()
        dsim_conf = self.correlator.configd['dsimengine']
        dig_host = dsim_conf['host']
        self.dhost = FpgaDsimHost(dig_host, config=dsim_conf)
        self.dhost.get_system_information()
        # Increase the dump rate so tests can run faster
        self.correlator.xeng_set_acc_time(0.2)

    # TODO 2015-05-27 (NM) Do test using get_vacc_offset(test_dump['xeng_raw']) to see if
    # the VACC is rotated. Run this test first so that we know immediately that other
    # tests will be b0rked.

    def test_channelisation(self):
        cconfig = self.correlator.configd
        n_chans = int(cconfig['fengine']['n_chans'])
        BW = float(cconfig['fengine']['bandwidth'])
        delta_f = BW / n_chans
        f_start = 0. # Center freq of the first bin
        chan_freqs = f_start + np.arange(n_chans)*delta_f

        test_chan = 1500
        expected_fc = f_start + delta_f*test_chan

        self.dhost.sine_sources.sin_0.set(frequency=expected_fc, scale=0.25)
        # The signal source is going to quantise the requested freqency, so see what we
        # actually got
        source_fc = self.dhost.sine_sources.sin_0.frequency
        self.dhost.sine_sources.sin_1.set(frequency=expected_fc, scale=0)
        self.dhost.sine_sources.sin_corr.set(frequency=expected_fc, scale=0)
        self.dhost.noise_sources.noise_0.set(scale=0.0)
        self.dhost.noise_sources.noise_1.set(scale=0)
        self.dhost.noise_sources.noise_corr.register.write(scale=0)
        self.dhost.outputs.out_0.select_output('signal')
        self.dhost.outputs.out_1.select_output('signal')
        self.dhost.outputs.out_0.scale_output(0.5)
        self.dhost.outputs.out_1.scale_output(0.5)

        self.corr_fix.issue_metadata()
        self.addCleanup(self.corr_fix.stop_x_data)
        self.corr_fix.start_x_data()

        full_range = 2**31      # Max range of the integers coming out of VACC
        def get_mag(dump, baseline):
            xrd = dump['xeng_raw']
            b = complexize(xrd[:,baseline,:])
            b_mag = np.abs(b)/full_range
            return b_mag

        def loggerize(data, dynamic_range=70):
            log_data = 10*np.log10(data)
            max_log = np.max(log_data)
            min_log_clip = max_log - dynamic_range
            log_data[log_data < min_log_clip] = min_log_clip
            return log_data

        # Get baseline 0 data, i.e. auto-corr of m000h
        test_baseline = 0
        dump_timeout = 10
        test_dump = self.receiver.get_clean_dump(dump_timeout)
        b_mag = get_mag(test_dump, baseline=test_baseline)
        # find channel with max power
        max_chan = np.argmax(b_mag)
        self.assertEqual(max_chan, test_chan,
                         'Channel with max power is not the test channel')

        # Place frequency samples spaced 0.1 of a channel-width over the central 80% of
        # the channel (assuming nr_freq_samples == 9)
        nr_freq_samples = 9
        # TODO 2015-05-27 (NM) This should be from -0.4 to 0.4, but the current dsim
        # doesn't have enough resolution to place a sample sufficiently close to -0.4
        # without going outside the range
        desired_chan_test_freqs = expected_fc + delta_f*np.linspace(
            -0.35, 0.35, nr_freq_samples)
        # Placeholder of actual frequencies that the signal generator produces
        signal_chan_test_freqs = np.zeros_like(desired_chan_test_freqs)
        # Channel magnitude responses for each frequency
        chan_responses = np.zeros((nr_freq_samples, n_chans))
        for i, freq in enumerate(desired_chan_test_freqs):
            LOGGER.info('Getting channel response for freq {}/{}: {} MHz.'.format(
                i+1, len(desired_chan_test_freqs), freq/1e6))
            if freq == expected_fc:
                # We've already done this one!
                this_source_freq = source_fc
                this_freq_result = b_mag
            else:
                self.dhost.sine_sources.sin_0.set(frequency=freq, scale=0.125)
                this_source_freq = self.dhost.sine_sources.sin_0.frequency
                this_freq_dump = self.receiver.get_clean_dump(dump_timeout)
                this_freq_response = get_mag(this_freq_dump, baseline=test_baseline)
            signal_chan_test_freqs[i] = this_source_freq
            chan_responses[i] = this_freq_response
        self.corr_fix.stop_x_data()
        for i, freq in enumerate(desired_chan_test_freqs):
            max_chan = np.argmax(chan_responses[i])
            self.assertEqual(max_chan, test_chan, 'Source freq {} peak not in channel '
                             '{} as expected but in {}.'
                             .format(signal_chan_test_freqs[i], test_chan, max_chan))
        self.assertLess(np.max(chan_responses[:, test_chan]), 0.99,
                        'VACC output at > 99% of maximum value, indicates that '
                        'something, somewhere, is probably overranging.')
        max_chan_response = np.max(10*np.log10(chan_responses[:, test_chan]))
        min_chan_response = np.min(10*np.log10(chan_responses[:, test_chan]))
        chan_ripple = max_chan_response - min_chan_response
        acceptable_ripple_lt = 0.3
        self.assertLess(chan_ripple, acceptable_ripple_lt,
                        'ripple {} dB within 80% of channel fc >= {} dB'
                        .format(chan_ripple, acceptable_ripple_lt))

        # from matplotlib import pyplot
        # colour_cycle = 'rgbyk'
        # style_cycle = ['-', '--']
        # linestyles = itertools.cycle(itertools.product(style_cycle, colour_cycle))
        # for i, freq in enumerate(desired_chan_test_freqs):
        #     style, colour = linestyles.next()
        #     pyplot.plot(loggerize(chan_responses[i], dynamic_range=60), color=colour, ls=style)
        # pyplot.ion()
        # pyplot.show()
        # import IPython ; IPython.embed()
