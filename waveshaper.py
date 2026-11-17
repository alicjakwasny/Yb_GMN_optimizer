import requests
import numpy as np
import json
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt

def scale_0_1_to_limit(x, min_val, max_val):
    return min_val + x*(max_val-min_val)

def thz_to_nm(freq_thz):
    """
    Convert frequency [THz] to wavelength [nm].
    """
    c = 299792.458  # speed of light in nm*THz
    return c / freq_thz


def nm_to_thz(wavelength_nm):
    """
    Convert wavelength [nm] to frequency [THz].
    """
    c = 299792.458
    return c / wavelength_nm

def gdd_ps_per_nm_to_s2(gdd_ps_per_nm, lambda_center_nm):
    """
    Konwertuje 'GDD' podane jako dτ/dλ w [ps / nm] do GDD = dτ/dω w [s^2].
    Zwraca wartość w s^2 (może być ujemna zgodnie z rachunkiem).
    """
    c = 299792458.0  # m/s
    # dτ/dλ: ps/nm -> s/m
    dtdl_s_per_m = gdd_ps_per_nm * 1e-3
    # lambda_center w metrach
    lambda_m = lambda_center_nm * 1e-9
    # dλ/dω = - λ^2 / (2π c)
    dlambda_domega = - (lambda_m**2) / (2 * np.pi * c)
    # GDD = dτ/dω = (dτ/dλ) * (dλ/dω)
    return dtdl_s_per_m * dlambda_domega


def phase_filter(phase, num_points=1000):
    """
    Interpolate and resample a user-provided phase vector to a new vector of length num_points.

    Parameters:
    -----------
    phase : array-like
        Original phase vector provided by the user.
    num_points : int
        Desired length of the output phase vector.

    Returns:
    --------
    new_phase : ndarray
        Smoothed and resampled phase vector of length num_points.
    """
    phase = np.asarray(phase)
    if len(phase) == 1:
        # If only one point, just repeat it
        return np.full(num_points, phase[0])

    # Original positions (normalized 0 to 1)
    x_old = np.linspace(0, 1, len(phase))

    # Target positions (normalized 0 to 1)
    x_new = np.linspace(0, 1, num_points)

    # Cubic interpolation for smooth phase
    interpolator = interp1d(x_old, phase, kind='cubic')
    new_phase = interpolator(x_new)

    return new_phase


def attenuation_filter(shaper,
                       type="Gaussian",
                       lambda_center=1560,
                       bandwidth_nm=7,
                       phase=[0],
                       num_points=1000):
    """
    Generate Gaussian-shaped intensity and phase arrays ready for WaveShaper.

    Args:
        shaper: WaveShaper object (must have start_freq and stop_freq in THz)
        lambda_center: center wavelength (nm)
        bandwidth_nm: FWHM (nm)
        phase: list or array of phase points
        num_points: number of points for the Gaussian profile

    Returns:
        frequencies_full: frequency array including start/stop edges
        intensities_full: intensity array (0-1)
        phases_full: phase array
    """
    # Frequency grid for Gaussian
    freqs = np.linspace(shaper.start_freq, shaper.stop_freq, num_points)

    # Convert center and FWHM to frequency
    f_center = nm_to_thz(lambda_center)
    f1 = nm_to_thz(lambda_center - bandwidth_nm / 2)
    f2 = nm_to_thz(lambda_center + bandwidth_nm / 2)
    fwhm_thz = abs(f2 - f1)

    # SHAPE SELECTION
    if type.lower() == "gaussian":
        # Gaussian transmission
        intensities = np.exp(-4 * np.log(2) * ((freqs - f_center) / fwhm_thz) ** 2)

    elif type.lower() == "sech2" or type.lower() == "sech^2":
        # sech^2 with FWHM matching the desired value
        #
        # FWHM = 2 * a * arcosh(sqrt(2))
        # => a = FWHM / (2 * arcosh(sqrt(2)))
        #
        a = fwhm_thz / (2 * np.arccosh(np.sqrt(2)))

        x = (freqs - f_center) / a
        intensities = 1 / (np.cosh(x) ** 2)

    else:
        raise ValueError("type must be 'Gaussian' or 'Sech2'")

    # Interpolate phase to match Gaussian points
    phases = phase_filter(phase, num_points)

    # Append start/stop points (full transmission, zero phase)
    frequencies_full = np.concatenate(([shaper.start_freq], freqs, [shaper.stop_freq]))
    intensities_full = np.concatenate(([1], intensities, [1]))
    phases_full = np.concatenate(([0], phases, [0]))

    return frequencies_full, intensities_full, phases_full

def parabolic_phase(shaper,
                    lambda_center=1560,
                    gdd=0,  #ps/nm
                    num_points=1000):

    gdd_s2 = gdd #gdd_ps_per_nm_to_s2(gdd, lambda_center)   ###ZMIANA JEDNOSTEK

    # Frequency grid for Gaussian
    freqs = np.linspace(shaper.start_freq, shaper.stop_freq, num_points)

    # Convert center and FWHM to frequency
    f_center = nm_to_thz(lambda_center)

    phases = 0.5 * gdd_s2 * (2*np.pi*(freqs - f_center))**2

    # Append start/stop points (full transmission, zero phase)
    frequencies_full = np.concatenate(([shaper.start_freq], freqs, [shaper.stop_freq]))
    phases_full = np.concatenate(([0], phases, [0]))

    return frequencies_full, phases_full

def polynomial_phase(shaper,
                    lambda_center=1560,
                    gdd=0,  #ps/nm
                    tod=0,
                    fod=0,
                    num_points=1000):

    #gdd_s2 = gdd #gdd_ps_per_nm_to_s2(gdd, lambda_center)   ###ZMIANA JEDNOSTEK

    # Frequency grid for Gaussian
    freqs = np.linspace(shaper.start_freq, shaper.stop_freq, num_points)

    # Convert center and FWHM to frequency
    f_center = nm_to_thz(lambda_center)

    # Angular frequency difference Δω
    domega = 2*np.pi*(freqs-f_center)

    phases = (
            (1/2) * gdd * domega**2 +
            (1/6) * tod * domega**3 +
            (1/24) * fod * domega**4
            )

    # Append start/stop points (full transmission, zero phase)
    frequencies_full = np.concatenate(([shaper.start_freq], freqs, [shaper.stop_freq]))
    phases_full = np.concatenate(([0], phases, [0]))

    return frequencies_full, phases_full


class WaveShaper:

    def __init__(self):
        '''
        Connect to WaveShaper and initiate WaveShaper class object that you use for communication with WaveShaper.
        '''

        self.ip = '169.254.6.8'
        #self.ip = "localhost:8000"
        result = requests.get('http://' + self.ip + '/waveshaper/devinfo').json()

        self.start_freq = result['startfreq']
        self.stop_freq = result['stopfreq']

        self.centre_wl = thz_to_nm(self.start_freq / 2 + self.stop_freq / 2)
        self.span_wl = - thz_to_nm(self.stop_freq) + thz_to_nm(self.start_freq)

    def createWspString(self, wsFreq, wsAttn, wsPhase, wsPort):
        '''
        Inside function of the WaveShaper.
        '''
        wsAttn[np.isnan(wsAttn)] = 60
        wsPhase[np.isnan(wsPhase)] = 0
        wsAttn[wsAttn > 60] = 60
        wsAttn[wsAttn <= 0] = 0
        wspString = ''
        for i in range(len(wsFreq)):
            wspString = '%s%.4f\t%.4f\t%.4f\t%d\n' % (wspString, wsFreq[i], wsAttn[i], wsPhase[i], wsPort[i])
        return wspString

    def uploadProfile(self, ip, wsFreq, wsAttn, wsPhase, wsPort, timeout=10):
        '''
        Inside function of the WaveShaper.
        '''
        data = {'type': 'wsp', 'wsp': self.createWspString(wsFreq, wsAttn, wsPhase, wsPort)}
        r = requests.post('http://' + ip + '/waveshaper/loadprofile', json.dumps(data), timeout=timeout)
        return r

    def transm_to_db(self, percentage):
        '''
        Translate transmission mask from the percentage [0, 1] to decibels [-60, 0].
        '''
        return -10 * np.log10(percentage)

    def write(self, freq, intens, phase):
        '''
        Upload profile to the WaveShaper. Frequency is given in THz. "Intens" is the transmission mask: 0 means no transmission, 1 means full transmission. Phase has no bounds.
        '''
        port = np.ones(freq.shape)
        intens2 = self.transm_to_db(intens)
        r = self.uploadProfile(self.ip, freq, intens2, phase, port)
        r_json = r.json()
        #r = self.uploadProfile(self.ip, freq, intens, phase, port)
        # r -> JSON containing rc (result code), msg (result in text format) and sno(Waveshaper serial number)
        # rc: 0 -> "OK", -1 -> -> "total power >1" lub "error: invalid json format"
        return r_json

if __name__ == '__main__':
    shaper = WaveShaper()
    #phases = np.array([20, 40, 50])
    #shaper.write(freq = np.array([192, 193, 194]), intens=np.array([1, 0.5, 1]), phase = phases)

    '''
    #wavelengths = np.linspace(1545, 1565, 5)
    #frequencies = nm_to_thz(wavelengths)
    frequencies = np.linspace(shaper.start_freq, shaper.stop_freq, 1000)
    intensities = np.ones_like(frequencies)
    phases = np.zeros_like(intensities)
    #phases = np.array(vec)
    
    frequencies, intensities, phases = attenuation_filter()
    frequencies_full = np.concatenate(([shaper.start_freq], frequencies, [shaper.stop_freq]))
    intensities_full = np.concatenate(([60], intensities*10, [60]))
    phases_full = np.concatenate(([0], phases, [0]))

    shaper.write(freq = frequencies_full, intens=intensities_full, phase = phases_full)
    '''
    freqs, intens, phases = attenuation_filter(shaper,
                                               lambda_center=1560,
                                               bandwidth_nm=7,
                                               phase=[0],
                                               num_points=1000)

    shaper.write(freq=freqs, intens=intens, phase=phases)

shaper = WaveShaper()