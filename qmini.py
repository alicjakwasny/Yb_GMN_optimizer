import rgbdriverkit as rgbdriverkit
from rgbdriverkit.qseriesdriver import Qseries
from rgbdriverkit.spectrometer import SpectrometerStatus
from rgbdriverkit.calibratedspectrometer import SpectrumData
from rgbdriverkit.calibratedspectrometer import SpectrometerProcessing
import time, sys

def Qmini_connect():
    dev = Qseries.search_devices()
    if (dev != None):
        print("Device found.")
    else:
        sys.exit("No device found.")

    q = Qseries(dev[0])  # Create instance of first spectrometer found
    q.open()  # Open device connection

    print("Software version: " + q.software_version)
    print("Hardware version: " + q.hardware_version)
    return q

def Qmini_read_spectrum(q):
    wavelengths = q.get_wavelengths()

    # Set exposure time and start exposure
    q.exposure_time = 0.1  # in seconds
    q.processing_steps = SpectrometerProcessing.AdjustOffset  # only adjust offset
    q.start_exposure(1)
    while not q.available_spectra:
        time.sleep(0.1)

    #print("Spectrum available")
    spec = q.get_spectrum_data()  # Get spectrum with meta data
    spectrum = spec.Spectrum
    return wavelengths, spectrum

def Qmini_close_connection(q):
    q.close()  # Close device connection
    print("Connection closed")