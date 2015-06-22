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
