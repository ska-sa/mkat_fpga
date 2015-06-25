import numpy as np

VACC_FULL_RANGE = float(2**31)      # Max range of the integers coming out of VACC

def complexise(input_data):
    """Convert input data shape (X,2) to complex shape (X)"""
    return input_data[:,0] + input_data[:,1]*1j

def magnetise(input_data):
    id_c = complexise(input_data)
    id_m = np.abs(id_c)
    return id_m

def normalise(input_data):
    return input_data / VACC_FULL_RANGE

def normalised_magnitude(input_data):
    return normalise(magnetise(input_data))

def loggerise(data, dynamic_range=70):
    log_data = 10*np.log10(data)
    max_log = np.max(log_data)
    min_log_clip = max_log - dynamic_range
    log_data[log_data < min_log_clip] = min_log_clip
    return log_data


def baseline_checker(xeng_raw, check_fn):
    """Apply a test function to correlator data one baseline at a time

    Returns a set of all the baseline indices for which the test matches
    """
    baselines = set()
    for bl in range(xeng_raw.shape[1]):
        if check_fn(xeng_raw[:, bl, :]):
            baselines.add(bl)
    return baselines

def zero_baselines(xeng_raw):
    """Return baseline indices that have all-zero data"""
    return baseline_checker(xeng_raw, lambda bldata: np.all(bldata == 0))

def nonzero_baselines(xeng_raw):
    """Return baseline indices that have some non-zero data"""
    return baseline_checker(xeng_raw, lambda bldata: np.any(bldata != 0))

def all_nonzero_baselines(xeng_raw):
    """Return baseline indices that have all non-zero data"""
    return baseline_checker(xeng_raw, lambda bldata: np.all(np.linalg.norm(
                    bldata.astype(np.float64), axis=1) != 0))

def init_dsim_sources(dhost):
    """Select dsim signal output, zero all sources, output scalings to 0.5"""
    for sin_source in dhost.sine_sources:
        sin_source.set(frequency=0, scale=0)
    for noise_source in dhost.noise_sources:
        noise_source.set(scale=0)
    for output in dhost.outputs:
        output.select_output('signal')
        output.scale_output(0.5)

class CorrelatorFrequencyInfo(object):
    """Derrive various bits of correlator frequency info using correlator config"""

    def __init__(self, corr_config):
        """Initialise the class

        Parameters
        ==========
        corr_config : dict
            Correlator config dict as in :attr:`corr2.fxcorrelator.FxCorrelator.configd`

        """
        self.corr_config = corr_config
        self.n_chans = int(corr_config['fengine']['n_chans'])
        "Number of frequency channels"
        self.bandwidth = float(corr_config['fengine']['bandwidth'])
        "Correlator bandwidth"
        self.delta_f = self.bandwidth / self.n_chans
        "Spacing between frequency channels"
        f_start = 0. # Center freq of the first bin
        self.chan_freqs = f_start + np.arange(self.n_chans)*self.delta_f
        "Channel centre frequencies"

    def calc_freq_samples(self, chan, samples_per_chan, chans_around=0):
        """Calculate frequency points to sweep over a test channel.

        Parameters
        =========
        chan : int
           Channel number around which to place frequency samples
        samples_per_chan: int
           Number of frequency points per channel
        chans_around: int
           Number of channels to include around the test channel. I.e. value 1 will
           include one extra channel above and one below the test channel.

        Will put frequency sample on channel boundary if 2 or more points per channel are
        requested, and if will place a point in the centre of the chanel if an odd number
        of points are specified.

        """
        assert samples_per_chan > 0
        assert chans_around > 0
        assert 0 <= chans < self.n_chans
        assert 0 <= chans + chans_around < self.n_chans
        assert 0 <= chans - chans_around < self.n_chans

        fc = self.chan_freqs[centre_chan]
        start_chan = chan - chans_around
        end_chan = chan + chans_around
        if samples_per_chan == 1:
            return self.chan_freqs[start_chan:end_chan+1]

        start_freq = self.chan_freqs[start_chan] - self.delta_f/2
        end_freq = self.chan_freqs[end_chan] + self.delta_f/2
        sample_spacing = self.delta_f / (samples_per_chan - 1)
        num_samples = int(np.round(
            (end_freq - start_freq) / sample_spacing)) + 1
        return np.linspace(start_freq, end_freq, num_samples)
