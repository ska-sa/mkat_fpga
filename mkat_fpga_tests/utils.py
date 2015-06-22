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
