import threading
import time
from BaseGUI import BaseGUI
from qmini import *
import numpy as np
import tkinter as tk
import data_processing as data
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from waveshaper import scale_0_1_to_limit, thz_to_nm
import ape_com as ape

class AcGUI(BaseGUI):
    def setup_feedback_plot(self):
        self.ape_figure = Figure(figsize=(5, 4), dpi=100, tight_layout=True)
        self.ape_ax = self.ape_figure.add_subplot(111)
        self.ape_ax.set_title("Autocorrelation")
        self.ape_ax.set_xlabel("Time (ps)")
        self.ape_ax.set_ylabel(r"Intensity (a.u.)")
        self.ape_line, = self.ape_ax.plot([], [], color="darkviolet")
        self.fit_line, = self.ape_ax.plot([], [], color="hotpink")
        self.ape_ax.grid(True, color="darkviolet", alpha=0.3)

        self.ape_canvas = FigureCanvasTkAgg(self.ape_figure, master=self.left_frame)
        self.ape_canvas.draw()
        self.ape_canvas.get_tk_widget().grid(row=0, column=0)

    def setup_best_feedback_plot(self):
        self.best_autocorrelation_figure = Figure(figsize=(5, 4), dpi=100, tight_layout=True)
        self.best_autocorrelation_ax = self.best_autocorrelation_figure.add_subplot(111)
        self.best_autocorrelation_ax.set_title("Best Autocorrelation")
        self.best_autocorrelation_ax.set_xlabel("Time (ps)")
        self.best_autocorrelation_ax.set_ylabel(r"Intensity (a.u.)")
        self.best_autocorrelation_line, = self.best_autocorrelation_ax.plot([], [], color="darkviolet")
        self.best_autocorrelation_ax.grid(True, color="darkviolet", alpha=0.3)
        self.best_fit_line, = self.best_autocorrelation_ax.plot([], [], color="hotpink")

        self.best_autocorrelation_canvas = FigureCanvasTkAgg(self.best_autocorrelation_figure, master=self.left_frame)
        self.best_autocorrelation_canvas.draw()
        self.best_autocorrelation_canvas.get_tk_widget().grid(row=0, column=1)

    def setup_feedback_panel(self):
        read_frame = ttk.LabelFrame(self.right_frame, text="APE Autocorrelator")
        read_frame.pack(fill='x', pady=5)

        ttk.Label(read_frame, text="Fit function:").grid(row=0, column=0, sticky="w")
        self.fit_function = tk.StringVar()
        self.fit_dropdown = ttk.Combobox(
            read_frame,
            textvariable=self.fit_function,
            values=["Gaussian", "Sech2", "Lorentzian"],
            state="readonly",
            width=10,
        )
        self.fit_function.set("Gaussian")
        self.fit_dropdown.grid(row=0, column=1, sticky='w')

        ttk.Label(read_frame, text="Scan range:").grid(row=1, column=0, sticky='w')
        self.scan_range_entry = ttk.Entry(read_frame, width=10)
        self.scan_range_entry.insert(0, 5)
        self.scan_range_entry.grid(row=1, column=1)

        ttk.Label(read_frame, text="Measurement frequency [Hz]:").grid(row=2, column=0, sticky='w')
        self.continuous_freq_entry = ttk.Entry(read_frame, width=10)
        self.continuous_freq_entry.insert(0, 10)
        self.continuous_freq_entry.grid(row=2, column=1)

        self.ape_continuous_button = ttk.Button(read_frame, text="Measure continuously",
                                                  command=self.start_continuous_read)
        self.ape_continuous_button.grid(row=3, column=0, pady=5)

        self.read_button = ttk.Button(read_frame, text="Read one autocorrelation", command=self.read_ape)
        self.read_button.grid(row=3, column=1, pady=5)

    def connect_to_feedback(self):
        device_dns_name = "pulsecheck-S09797"
        tcp_port = 5025
        self.feedback_device = ape.connect(device_dns_name, tcp_port)
        self.feedback_device_name = "APE_AC"

    def read_ape(self, update_plot=True):
        self.ape_xdata, self.ape_ydata = ape.read_acf(self.feedback_device)
        if update_plot:
            self.root.after(0, self.show_feedback_plot)

    def read_ape_background(self):
        '''działa w WĄTKU, nie blokuje Tkintera'''
        while self.feedback_continuous:
            delay = 1 / float(self.continuous_freq_entry.get())
            x, y = ape.read_acf(self.feedback_device)

            self.root.after(0, self.update_feedback_plot, x, y)
            time.sleep(delay)

    def update_feedback_plot(self, x, y):
        '''Wywoływane w wątku głównym'''
        self.ape_xdata = x
        self.ape_ydata = y
        self.show_feedback_plot()

    def start_continuous_read(self):
        '''wywołane przy kliknięciu checkbutton'''
        if not self.feedback_continuous:
            self.feedback_continuous = True
            self.ape_continuous_button.configure(style='Green.TButton')
            self.talk("Starting continuous APE measurements")
            # uruchom nowy wątek
            t = threading.Thread(target=self.read_ape_background, daemon=True)
            t.start()
        else:
            # po odznaczeniu - po prostu pętla się przerwie
            self.feedback_continuous = False
            self.ape_continuous_button.configure(style="Black.TButton")
            self.talk("Stopped continuous APE measurement")

    def show_feedback_plot(self):

        norm_delay = data.normalize_delay(self.ape_xdata, self.ape_ydata)
        norm_acf = (self.ape_ydata - np.min(self.ape_ydata)) / (np.max(self.ape_ydata) - np.min(self.ape_ydata))
        fit = self.calculate_fit()

        xmin = -1*(float(self.scan_range_entry.get())/2)
        xmax = float(self.scan_range_entry.get())/2
        #print(f'xmin: {xmin}, xmax: {xmax}')

        self.ape_line.set_xdata(norm_delay)
        self.ape_line.set_ydata(norm_acf)
        self.ape_line.set_visible(True)

        self.fit_line.set_xdata(norm_delay)
        self.fit_line.set_ydata(fit)
        self.fit_line.set_visible(True)

        self.ape_ax.set_xlim(xmin, xmax)
        #self.ape_ax.set_xlim(norm_delay[0], norm_delay[-1])
        self.ape_ax.set_ylim(0, 1.1)
        #self.ape_ax.set_ylim(0, 1.1 * np.max(self.ape_ydata))
        self.ape_ax.get_yaxis().set_visible(True)

        self.ape_canvas.draw()

    def prepare_for_optimization(self):
        if self.ape_continuous_button["state"] == "disabled":
            # nie rób nic jeśli optymalizacja już dziala
            return

        # zablokuj przycisk
        self.ape_continuous_button.config(state="disabled")
        self.optimize_button.config(state="disabled")
        self.root.update_idletasks()

    def prepare_after_optimization(self):
        self.ape_continuous_button.after(0, lambda: self.ape_continuous_button.config(state="normal"))
        self.optimize_button.after(0, lambda: self.optimize_button.config(state="normal"))

    def calculate_fit(self, best = False):
        if not best:
            fit_function = self.fit_function.get().lower()
            fit = data.calculate_fit(self.ape_xdata, self.ape_ydata, fit_function)
        else:
            fit_function = self.fit_function.get().lower()
            fit = data.calculate_fit(self.best_autocorrelation_xdata, self.best_autocorrelation_ydata, fit_function)
        return fit

    def objective_gdd_tod_fod(self, gdd, tod, fod, c_lambda, filter_width):
        '''
        Calculates fitness of a pulse with given parameters
        :param gdd:
        :param tod:
        :param fod:
        :param c_lambda:
        :param filter_width:
        :return:
        '''

        gdd = scale_0_1_to_limit(gdd, float(self.min_gdd_entry.get()), float(self.max_gdd_entry.get()))
        tod = scale_0_1_to_limit(tod, float(self.min_tod_entry.get()), float(self.max_tod_entry.get()))
        fod = scale_0_1_to_limit(fod, float(self.min_fod_entry.get()), float(self.max_fod_entry.get()))
        c_lambda = scale_0_1_to_limit(c_lambda, float(self.min_central_lambda_entry.get()),
                                      float(self.max_central_lambda_entry.get()))
        filter_width = scale_0_1_to_limit(filter_width, float(self.min_filter_width_entry.get()),
                                          float(self.max_filter_width_entry.get()))

        start_time = time.perf_counter()
        r = self.set_gdd_tod_fod(gdd, tod, fod, c_lambda, filter_width, update_plot=False)
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        #print(f'Czas wykonania shaper: {elapsed:.6f} s, wiadomość {r}')
        time.sleep(1)
        self.read_ape(update_plot=False)

        # zaktualizuj wykresy
        self.show_waveshaper_plot()
        self.show_feedback_plot()

        # ADD CALCULATING FEEDBACK
        if np.max(self.ape_ydata) <= 0.3:
            return 5000000


        acf = self.ape_ydata
        delay = self.ape_xdata
        scan_range = float(self.scan_range_entry.get())
        fit_function = self.fit_function.get().lower()
        fwhm, fit, pulse_qual, area = data.calc_pulse_qual(acf, delay, scan_range, fit_function)

        return pulse_qual

    def show_best_feedback_plot(self):

        norm_delay = data.normalize_delay(self.best_autocorrelation_xdata, self.best_autocorrelation_ydata)
        fit = self.calculate_fit(best=True)
        norm_acf = ((self.best_autocorrelation_ydata - np.min(self.best_autocorrelation_ydata)) /
                    (np.max(self.best_autocorrelation_ydata) - np.min(self.best_autocorrelation_ydata)))

        xmin = -1 * (float(self.scan_range_entry.get()) / 2)
        xmax = float(self.scan_range_entry.get()) / 2

        self.best_autocorrelation_line.set_xdata(norm_delay)
        self.best_autocorrelation_line.set_ydata(norm_acf)
        self.best_autocorrelation_line.set_visible(True)

        self.best_fit_line.set_xdata(norm_delay)
        self.best_fit_line.set_ydata(fit)
        self.best_fit_line.set_visible(True)

        self.best_autocorrelation_ax.set_xlim(xmin, xmax)
        #self.best_autocorrelation_ax.set_xlim(norm_delay[0], norm_delay[-1])
        #self.best_autocorrelation_ax.set_ylim(0, 1.1 * np.max(self.best_autocorrelation_ydata))
        self.best_autocorrelation_ax.set_ylim(0, 1.1)
        self.best_autocorrelation_ax.get_yaxis().set_visible(True)

        self.best_autocorrelation_canvas.draw()

    def update_best_feedback_plot(self, gdd, tod, fod, central_lambda, filter_width):
        self.set_gdd_tod_fod(gdd, tod, fod, central_lambda, filter_width)
        # time.sleep(int(self.sample_delay.get()) / 1000)
        self.read_ape()
        self.best_autocorrelation_xdata, self.best_autocorrelation_ydata = self.ape_xdata, self.ape_ydata
        self.show_best_feedback_plot()

    def formulate_data_for_saving(self, best_gdd, best_tod, best_fod, best_lambda_c, best_filter_width, best_fitness):
        fit = self.calculate_fit(best=True)
        attenuation_xdata = [thz_to_nm(x) for x in self.attenuation_xdata]
        phase_xdata = [thz_to_nm(x) for x in self.phase_xdata]
        results = {
            "parameters": {
                "GDD": best_gdd,
                "TOD": best_tod,
                "FOD": best_fod,
                "center wavelength": best_lambda_c,
                "filter width": best_filter_width,
            },
            "attenuation": {
                "xdata": attenuation_xdata,
                "ydata": self.attenuation_ydata,
            },
            "phase": {
                "xdata": phase_xdata,
                "ydata": self.phase_ydata,
            },
            "APE": {
                "xdata": self.best_autocorrelation_xdata,
                "ydata": self.best_autocorrelation_ydata,
                "fit_function": self.fit_function.get(),
                "fit": fit,
            },
            "fitness": best_fitness,
            "fitness_curve": self.fitness_list,
        }

        return results

if __name__ == "__main__":
    root = tk.Tk()
    app = AcGUI(root)
    root.mainloop()