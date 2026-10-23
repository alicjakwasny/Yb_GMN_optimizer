import numpy as np
from scipy.integrate import trapezoid
import datetime
import os
import matplotlib.pyplot as plt

def vec_to_mask(vec, stripe_width):
    new_vec = []

    for element in vec:
        temp = np.full(stripe_width, element)
        new_vec = np.concatenate((new_vec, temp))
        mask = [new_vec for i in range(1200)]
        mask = np.array(mask, dtype=np.int16)

    return mask

def vec_to_half_mask(vec, stripe_width):
    new_vec = []
    black_vec = np.full(int(1920 / 4), 0)

    for element in vec:
        temp = np.full(stripe_width, element)
        new_vec = np.concatenate((new_vec, temp))

    new_vec = np.concatenate((black_vec, new_vec, black_vec))
    mask = [new_vec for i in range(1200)]
    mask = np.array(mask, dtype=np.int16)

    return mask


'''
def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx

def find_nearest_new(array, value):
    array = np.asarray(array)
    for i in range(len(array)):
        difference = array[i] - value
        try:
            next_difference = array[i+1] - value
        except ValueError or IndexError:
            next_difference = array[0] - value

        if (difference*next_difference < 0):    #checking if they have opposite signs
            if np.abs(difference) < np.abs(next_difference):
                return i
            else:
                return i+1
'''

def find_nearest(array, value):
    array = np.asarray(array)
    if array.size == 0:
        raise ValueError("find_nearest: próba znalezienia najbliższej wartości w pustej tablicy.")
    idx = (np.abs(array - value)).argmin()
    return idx

def find_crossing(array, value):
    array = np.asarray(array)

    if array.size == 0:
        raise ValueError("find_nearest: próba znalezienia najbliższej wartości w pustej tablicy.")

    diff = array - value
    sign_change = np.where(diff[:-1] * diff[1:] < 0)[0]

    if len(sign_change) == 0:
        return None

    i = sign_change[0]

    if abs(diff[i]) < abs(diff[i+1]):
        return i
    else:
        return i+1

def compute_width(wavelengths, power, level=0.5):
    if len(wavelengths) == 0 or len(power) == 0:
        raise ValueError("compute_width: pusta tablice wejsciowa")

    # znormalizuj spektrum
    intensities = normalize01(power)

    # Znajdz indeks maksimum
    idx_max = np.argmax(intensities)

    # szukaj punktow przeciecia po lewej i prawej stronie
    left_idx = find_nearest(power[:idx_max], level)
    right_idx = idx_max + find_nearest(power[idx_max:], level)

    # oblicz szerokosc
    width = np.abs(wavelengths[left_idx] - wavelengths[right_idx])
    return width

def compute_width_db(wavelengths, power, level=10):
    if len(wavelengths) == 0 or len(power) == 0:
        raise ValueError("compute_width: pusta tablice wejsciowa")

    intensities = power

    # Znajdz indeks maksimum
    max_val = np.max(intensities)
    idx_max = np.argmax(intensities)

    target = max_val - level

    # szukaj punktow przeciecia po lewej i prawej stronie
    # lewa strona
    left_p = intensities[:idx_max+1]
    left_w = wavelengths[:idx_max+1]

    left_cross = np.where(left_p < target)[0]

    if left_cross.size == 0:
        #raise ValueError("Brak przecięcia po lewej stronie")
        return -1e6

    i2 = left_cross[-1]     # ostatni punkt poniżej
    if i2 == 0:
        return -1e6
    i1 = i2-1               # punkt powyzej
    wl_left = np.interp(target, [left_p[i1], left_p[i2]], [left_w[i1], left_w[i2]])

    #prawa strona
    right_p = intensities[idx_max:]
    right_w = wavelengths[idx_max:]

    right_cross = np.where(right_p < target)[0]
    if right_cross.size == 0:
        return -1e6

    j2 = right_cross[0]
    if j2 == 0:
        return -1e6
    j1 = j2-1
    wl_right = np.interp(target, [right_p[j1], right_p[j2]], [right_w[j1], right_w[j2]])

    # oblicz szerokosc
    width = abs(wl_right - wl_left)
    return width

def normalize01(x):
    x = np.array(x, dtype=float)

    x_min = x.min()
    x_max = x.max()
    denom = x_max - x_min

    if denom == 0:
        return np.zeros_like(x)

    return (x - x_min) / denom

def compute_spectral_flatness_in_range(wavelength, spectrum_lin, center_wavelength_nm, span_nm):
    """
    Oblicza spectral flatness
    """
    wavelength = np.asarray(wavelength, dtype=float)
    spectrum_lin = np.asarray(spectrum_lin, dtype=float)

    # Filtruj dane wokół interesującego zakresu
    mask = (wavelength >= center_wavelength_nm - span_nm) & (wavelength <= center_wavelength_nm + span_nm)
    interest_vector = spectrum_lin[mask]

    interest_wavelengths = wavelength[mask]

    if len(interest_vector) == 0:
        raise ValueError("Brak danych w zadanym zakresie długości fali!")

    spectrum = np.asarray(interest_vector, dtype=float)

    arith = np.mean(spectrum)

    # --- krok 3: zabezpieczenie log() ---
    eps = 1e-12
    spectrum = np.where(spectrum <= 0, eps, spectrum)

    # zabezpieczenie: geo mean tylko dla dodatnich
    #if np.any(spectrum <= 0):
        #raise ValueError("Średnia geometryczna wymaga wszystkich wartości > 0")

    # średnia geometryczna
    geo = np.exp(np.mean(np.log(spectrum)))
    flatness = geo/arith

    '''
    #for dB
    # Oblicz średnią w dB (to jest logarytm średniej geometrycznej)
    mean_dB = np.mean(spectrum)
    mean_lin_dB = 10 * np.log10(np.mean(10 ** (spectrum / 10)))

    # Flatness = exp(mean(log(P))) / mean(P)
    # więc w dB to: flatness_dB = mean_dB - 10*log10(mean(10^(P/10)))
    flatness_dB = mean_dB - mean_lin_dB
    '''

    return flatness

def sech_squared(x, fwhm):
    fwhm/=1000 #change to ps
    x_parameter = fwhm / (2 * np.log(2))
    return (1 / np.cosh(x / x_parameter)) ** 2

def normalize_delay(delay, acf):
    delayn = delay
    idx = np.argmax(acf)
    offset = delay[idx]
    for i in range(len(delayn)):
        delayn[i]-=offset

    return delayn

def calculate_fwhm(delay, acf):
    # zwraca FWHM w ps
    delay = normalize_delay(delay, acf)

    normalized = (acf - np.min(acf)) / (np.max(acf) - np.min(acf))

    # find the index of peak value
    i = np.where(normalized == 1)
    i = i[0][0]

    arr_left = normalized[0:i]
    arr_right = normalized[i:]

    try:
        # find the half values
        #i_left = find_nearest(np.flip(arr_left), 0.5)
        #i_right = find_nearest(arr_right, 0.5)
        i_left = find_crossing(np.flip(arr_left), 0.5)
        i_right = find_crossing(arr_right, 0.5)
    except ValueError:
        return 100000   # penalty

    if i_left==None or i_right==None:
        return 100000

    left_delay = np.flip(delay[0:i])
    right_delay = delay[i:]
    fwhm = abs(right_delay[i_right] - left_delay[i_left])

    return fwhm

def calculate_fit(delay, acf, fit_function):
    #calculate the fit

    fwhm = calculate_fwhm(delay, acf)

    match fit_function:
        case "sech2":
            fit = (1 / (np.cosh((1.762 / fwhm)*np.array(delay)))) ** 2
        case "gaussian":
            fit = np.exp(-4*np.log(2) * (np.array(delay) / fwhm)**2)
        case "lorentzian":
            fit = 1 / (1 + (2*np.array(delay) / fwhm)**2)

    return fit

def calc_pulse_qual(acf, delay, scan_range, fit_function):
    # normalize the ACF

    norm_delay = normalize_delay(delay, acf)
    norm_acf = (acf - np.min(acf)) / (np.max(acf) - np.min(acf))
    fwhm = calculate_fwhm(delay, acf) * 1000    # for FWHM in fs
    fit = calculate_fit(delay, acf, fit_function)

    step = scan_range / len(norm_acf)
    start = -1 * scan_range / 2
    stop = scan_range / 2

    # calculate the integral of ACF
    area = trapezoid(norm_acf, dx = step)

    # calculate the new coefficient
    # integral of the fit
    area_fit = trapezoid(fit, dx=step)
    pulse_qual = fwhm * ((1 + abs(1 - (area_fit / area)))**2)

    '''for oscillator measurements'''
    '''
    fwhm_limit = 150

    if fwhm < fwhm_limit:
        pulse_qual = pulse_qual + 100000  # penalty for wrong autocorrelation measurement
    '''

    return fwhm, fit, pulse_qual, area

def save_to_csv(parent_dir, genes, population_size, n_iter, AP, fl, fitness_list, best, delay, acf, fit):
    now = datetime.datetime.now()
    date = now.strftime(("%d%m%y_%H%M%S"))

    dir_name = f'cs_optim_{date}_{genes}_stripes_{population_size}_pop_{n_iter}_iter_{AP}_ap_{fl}_fl'
    path = os.path.join(parent_dir, dir_name)
    os.mkdir(path)

    np.savetxt(f'{path}/fitness_list.csv', fitness_list, delimiter=';')
    np.savetxt(f'{path}/vec.csv', best, delimiter=';')
    np.savetxt(f'{path}/delay.csv', delay, delimiter=';')
    np.savetxt(f'{path}/acf.csv', acf, delimiter=';')
    np.savetxt(f'{path}/fit.csv', fit, delimiter=';')

def save_to_csv(parent_dir, genes, population_size, n_iter, AP, fl, fitness_list, best):
    now = datetime.datetime.now()
    date = now.strftime(("%d%m%y_%H%M%S"))

    dir_name = f'cs_optim_{date}_{genes}_stripes_{population_size}_pop_{n_iter}_iter_{AP}_ap_{fl}_fl'
    path = os.path.join(parent_dir, dir_name)
    os.mkdir(path)

    np.savetxt(f'{path}/fitness_list.csv', fitness_list, delimiter=';')
    np.savetxt(f'{path}/vec.csv', best, delimiter=';')

def save_to_csv_iteration(parent_dir, vector, n_iter, crow_idx, fitness, delay, acf, fit):
    dir_name = f'iteration_{n_iter}_crow_{crow_idx}'
    path = os.path.join(parent_dir, dir_name)
    os.mkdir(path)

    np.savetxt(f'{path}/fitness.csv', [fitness], delimiter=';')
    np.savetxt(f'{path}/vec.csv', vector, delimiter=';')
    np.savetxt(f'{path}/delay.csv', delay, delimiter=';')
    np.savetxt(f'{path}/acf.csv', acf, delimiter=';')
    np.savetxt(f'{path}/fit.csv', fit, delimiter=';')

def plot_fitness(fitness, title):
    plt.plot(fitness)
    plt.xlabel('Iterations')
    plt.ylabel('Fitness')
    plt.title(title)
    plt.show()

