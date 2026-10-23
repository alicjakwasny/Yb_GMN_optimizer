import threading
from BaseGUI import BaseGUI
from qmini import *
import numpy as np
import tkinter as tk
import data_processing as data
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from waveshaper import scale_0_1_to_limit, thz_to_nm

class QminiGUI(BaseGUI):
    def setup_feedback_plot(self):
        self.qmini_figure = Figure(figsize=(5, 4), dpi=100, tight_layout=True)
        self.qmini_ax = self.qmini_figure.add_subplot(111)
        self.qmini_ax.set_title("Spectrum from Qmini")
        self.qmini_ax.set_xlabel("Wavelength (nm)")
        self.qmini_ax.set_ylabel(r"Intensity ($\mu$W/nm)")
        self.qmini_line, = self.qmini_ax.plot([], [], color="darkviolet")
        self.qmini_ax.grid(True, color="darkviolet", alpha=0.3)

        self.qmini_ax2 = self.qmini_ax.twinx()
        self.qmini_ax2.set_ylabel("Intensity [dBm]")
        self.qmini_line2, = self.qmini_ax2.plot([], [], color="hotpink")
        self.qmini_ax2.grid(True, color="hotpink", alpha=0.3)
        self.threshold_line = self.qmini_ax2.axhline(
            y=np.nan, linestyle="--", color="red", alpha=0.8
        )
        self.threshold_text = self.qmini_ax2.text(
            0.95, 0, "15dB: ",
            color="red",
            ha="right", va="bottom",
            transform=self.qmini_ax2.get_yaxis_transform()
        )
        self.rectangle_line, = self.qmini_ax2.plot([], [], color="darkmagenta")

        self.qmini_canvas = FigureCanvasTkAgg(self.qmini_figure, master=self.left_frame)
        self.qmini_canvas.draw()
        self.qmini_canvas.get_tk_widget().grid(row=0, column=0)

    def setup_best_feedback_plot(self):
        self.best_spectrum_figure = Figure(figsize=(5, 4), dpi=100, tight_layout=True)
        self.best_spectrum_ax = self.best_spectrum_figure.add_subplot(111)
        self.best_spectrum_ax.set_title("Best Spectrum")
        self.best_spectrum_ax.set_xlabel("Wavelength (nm)")
        self.best_spectrum_ax.set_ylabel(r"Intensity ($\mu$W/nm)")
        self.best_spectrum_line, = self.best_spectrum_ax.plot([], [], color="darkviolet")
        self.best_spectrum_ax.grid(True, color="darkviolet", alpha=0.3)

        self.best_spectrum_ax2 = self.best_spectrum_ax.twinx()
        self.best_spectrum_ax2.set_ylabel("Intensity [dB]")
        self.best_spectrum_line2, = self.best_spectrum_ax2.plot([], [], color="hotpink")
        self.best_spectrum_ax2.grid(True, color="hotpink", alpha=0.3)

        self.best_spectrum_canvas = FigureCanvasTkAgg(self.best_spectrum_figure, master=self.left_frame)
        self.best_spectrum_canvas.draw()
        self.best_spectrum_canvas.get_tk_widget().grid(row=0, column=1)

    def setup_feedback_panel(self):
        read_frame = ttk.LabelFrame(self.right_frame, text="Qmini")
        read_frame.pack(fill='x', pady=5)

        ttk.Label(read_frame, text="Min wavelength:").grid(row=0, column=0, sticky='w')
        self.lambda_min_entry = ttk.Entry(read_frame, width=10)
        self.lambda_min_entry.insert(0, 750)
        self.lambda_min_entry.grid(row=0, column=1)

        ttk.Label(read_frame, text="Max wavelength:").grid(row=1, column=0, sticky='w')
        self.lambda_max_entry = ttk.Entry(read_frame, width=10)
        self.lambda_max_entry.insert(0, 900)
        self.lambda_max_entry.grid(row=1, column=1)

        self.scale_lin = tk.BooleanVar(value=True)
        self.qmini_scale_lin = ttk.Checkbutton(read_frame, text="Linear scale", variable=self.scale_lin)
        self.qmini_scale_lin.grid(row=2, column=0)

        self.scale_log = tk.BooleanVar(value=True)
        self.qmini_scale_log = ttk.Checkbutton(read_frame, text="Logarythmic scale", variable=self.scale_log)
        self.qmini_scale_log.grid(row=2, column=1)

        ttk.Label(read_frame, text="Measurement frequency [Hz]:").grid(row=4, column=0, sticky='w')
        self.continuous_freq_entry = ttk.Entry(read_frame, width=10)
        self.continuous_freq_entry.insert(0, 10)
        self.continuous_freq_entry.grid(row=4, column=1)

        self.qmini_continuous_button = ttk.Button(read_frame, text="Measure continuously",
                                                  command=self.start_continuous_read)
        self.qmini_continuous_button.grid(row=5, column=0, pady=5)

        self.read_button = ttk.Button(read_frame, text="Read one spectrum", command=self.read_qmini)
        self.read_button.grid(row=5, column=1, pady=5)

    def connect_to_feedback(self):
        if not self.feedback_connected:
            self.feedback_device_name = "Qmini"
            try:
                self.feedback_device = Qmini_connect()
                # self.qmini_connect_button.configure(text = "Qmini Connected", style = "Green.TButton")
                self.talk("You connected to Qmini")
                self.feedback_connected = True
            except:
                # self.qmini_connect_button.configure(text = "Qmini Error", style = "Red.TButton")
                self.talk("Error when connecting to qmini")
        else:
            Qmini_close_connection(self.feedback_device)
            self.feedback_connected = False
            self.feedback_device = None
            # self.qmini_connect_button.configure(text="Qmini Connect", style="Black.TButton")
            self.talk("You disconnected from Qmini")

    def read_qmini(self, update_plot=True):
        self.qmini_xdata, self.qmini_ydata = Qmini_read_spectrum(self.feedback_device)
        if update_plot:
            self.root.after(0, self.show_feedback_plot)

    def read_qmini_background(self):
        '''działa w WĄTKU, nie blokuje Tkintera'''
        while self.feedback_continuous:
            delay = 1 / float(self.continuous_freq_entry.get())
            x, y = Qmini_read_spectrum(self.feedback_device)

            self.root.after(0, self.update_feedback_plot, x, y)
            time.sleep(delay)

    def update_feedback_plot(self, x, y):
        '''Wywoływane w wątku głównym'''
        self.qmini_xdata = x
        self.qmini_ydata = y
        self.show_feedback_plot()

    def start_continuous_read(self):
        '''wywołane przy kliknięciu checkbutton'''
        if not self.feedback_continuous:
            self.feedback_continuous = True
            self.qmini_continuous_button.configure(style='Green.TButton')
            self.talk("Starting continuous Qmini measurements")
            # uruchom nowy wątek
            t = threading.Thread(target=self.read_qmini_background, daemon=True)
            t.start()
        else:
            # po odznaczeniu - po prostu pętla się przerwie
            self.feedback_continuous = False
            self.qmini_continuous_button.configure(style="Black.TButton")
            self.talk("Stopped continuous Qmini measurement")

    def show_feedback_plot(self):
        xmin = float(self.lambda_min_entry.get())
        xmax = float(self.lambda_max_entry.get())

        if self.scale_lin.get():
            self.qmini_line.set_xdata(self.qmini_xdata)
            self.qmini_line.set_ydata(self.qmini_ydata)
            # self.qmini_ax.set_xlim(self.qmini_xdata[0], self.qmini_xdata[-1])
            self.qmini_line.set_visible(True)
            self.qmini_ax.set_xlim(xmin, xmax)
            self.qmini_ax.set_ylim(0, 1.1 * np.max(self.qmini_ydata))

            self.qmini_ax.get_yaxis().set_visible(True)
        else:
            self.qmini_line.set_visible(False)
            self.qmini_ax.get_yaxis().set_visible(False)

        if self.scale_log.get():
            self.qmini_line2.set_xdata(self.qmini_xdata)
            lin = np.array(self.qmini_ydata, dtype=float)
            lin[lin <= 0] = 1e-20
            self.qmini_ydata_log = 10 * np.log10(lin / 1000)
            self.qmini_line2.set_ydata(self.qmini_ydata_log)

            self.qmini_line2.set_visible(True)
            self.qmini_ax2.set_xlim(xmin, xmax)
            # self.qmini_ax2.set_ylim(np.min(self.qmini_ydata_log), np.max(self.qmini_ydata_log) * 1.1)
            self.qmini_ax2.set_ylim(-20, 20)
            threshold_value = max(self.qmini_ydata_log) - 9
            self.threshold_line.set_ydata([threshold_value, threshold_value])
            # aktualizacja napisu
            wavelengths = np.array(self.qmini_xdata, dtype=float)
            intensities = np.array(self.qmini_ydata_log, dtype=float)
            mask = (wavelengths >= xmin) & (wavelengths <= xmax)
            w_filtered = wavelengths[mask]
            i_filtered = intensities[mask]
            width = data.compute_width_db(w_filtered, i_filtered, level=9)
            self.threshold_text.set_y(threshold_value)

            self.threshold_text.set_text(f"3 dB: {width:.2f} nm")

            # prostokąt
            lambda_min = 782.5  # nm
            lambda_max = 837.5  # nm
            rectangle = ((w_filtered >= lambda_min) & (w_filtered <= lambda_max)).astype(float)  # zrob prostokat
            I_min = -15  # minimum value of intensity
            I_max = np.max(i_filtered)
            if I_max < -5:
                I_max = I_min
            elif I_max < 4:
                I_max = 4
            rectangle_scaled = rectangle * (I_max - I_min) + I_min  # wyskaluj prostokat
            self.rectangle_line.set_xdata(w_filtered)
            self.rectangle_line.set_ydata(rectangle_scaled)

            self.qmini_ax2.get_yaxis().set_visible(True)
        else:
            self.qmini_line2.set_visible(False)
            self.qmini_ax2.get_yaxis().set_visible(False)

        self.qmini_canvas.draw()

    def prepare_for_optimization(self):
        if self.qmini_continuous_button["state"] == "disabled":
            # nie rób nic jeśli optymalizacja już dziala
            return

        # zablokuj przycisk
        self.qmini_continuous_button.config(state="disabled")
        self.optimize_button.config(state="disabled")
        self.root.update_idletasks()

    def prepare_after_optimization(self):
        self.qmini_continuous_button.after(0, lambda: self.qmini_continuous_button.config(state="normal"))
        self.optimize_button.after(0, lambda: self.optimize_button.config(state="normal"))

    def objective_gdd_tod_fod(self, gdd, tod, fod, c_lambda, filter_width):
        '''
        Calculates fitness of a pulse with given GDD value
        :return:
        '''

        gdd = scale_0_1_to_limit(gdd, float(self.min_gdd_entry.get()), float(self.max_gdd_entry.get()))
        tod = scale_0_1_to_limit(tod, float(self.min_tod_entry.get()), float(self.max_tod_entry.get()))
        fod = scale_0_1_to_limit(fod, float(self.min_fod_entry.get()), float(self.max_fod_entry.get()))
        c_lambda = scale_0_1_to_limit(c_lambda, float(self.min_central_lambda_entry.get()),
                                      float(self.max_central_lambda_entry.get()))
        filter_width = scale_0_1_to_limit(filter_width, float(self.min_filter_width_entry.get()),
                                          float(self.max_filter_width_entry.get()))

        # lambda_center = float(self.central_lambda_entry.get())
        # atten_bandwidth = float(self.atten_filter_bandwidth_entry.get())

        start_time = time.perf_counter()
        r = self.set_gdd_tod_fod(gdd, tod, fod, c_lambda, filter_width, update_plot=False)
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        print(f'Czas wykonania shaper: {elapsed:.6f} s, wiadomość {r}')
        # time.sleep(int(self.sample_delay.get())/1000)
        self.read_qmini(update_plot=False)

        # zaktualizuj wykresy
        self.show_waveshaper_plot()
        self.show_feedback_plot()

        wavelengths = np.array(self.qmini_xdata, dtype=float)
        intensities = np.array(self.qmini_ydata, dtype=float)

        xmin = float(self.lambda_min_entry.get())
        xmax = float(self.lambda_max_entry.get())

        mask = (wavelengths >= xmin) & (wavelengths <= xmax)

        w_filtered = wavelengths[mask]
        i_filtered = intensities[mask]

        lin = i_filtered
        lin[lin <= 0] = 1e-20
        intensities_db = 10 * np.log10(lin / 1000)

        lambda_min = 782.5  # nm
        lambda_max = 837.5  # nm
        rectangle = ((w_filtered >= lambda_min) & (w_filtered <= lambda_max)).astype(float)  # zrob prostokat
        I_min = -15  # minimum value of intensity
        I_max = np.max(intensities_db)
        if I_max < -5:  # 7:
            fitness = 1000000
            self.gdd_indicator.config(
                text=f'Current GDD: {gdd: .2f}, TOD: {tod: .2f}, FOD: {fod: .2f}, Lambda: {c_lambda: .2f}, Bandwidth: {filter_width: .2f}')
            self.fitness_indicator.config(text=f'Current fitness: {fitness: .2f}')
            return fitness
        elif I_max < 10:
            I_max = 10

        I_max_lin = np.max(lin)
        I_min_lin = np.min(lin)
        rectangle_scaled = rectangle * (
                    I_max_lin - I_min_lin) + I_min_lin  # (I_max - I_min) + I_min   #wyskaluj prostokat

        background = 1.0 - rectangle
        background_scaled = background * (I_max_lin - I_min_lin) + I_min_lin  # (I_max - I_min) + I_min

        spectrum_cut = intensities_db.copy()  # odciecie na -15 dB
        spectrum_cut[intensities_db < -15] = -15

        print("wavelengths:", w_filtered.shape)
        print("intensities_db:", intensities_db.shape)
        print("spectrum_cut:", spectrum_cut.shape)

        energy_inside = 0.0
        e_mask = (w_filtered >= lambda_min) & (w_filtered <= lambda_max)
        w_filtered_e = w_filtered[e_mask]
        i_filtered_e = lin[e_mask]  # spectrum_cut[e_mask]

        ''' USING SUMS
        energy_inside = np.sum(i_filtered_e)
        energy_full = np.sum(rectangle_scaled[e_mask])
        '''

        # USING TRAPZ
        energy_inside = np.trapezoid(i_filtered_e, w_filtered_e)
        energy_full = np.trapezoid(rectangle_scaled[e_mask], w_filtered_e)

        fulness = energy_inside / energy_full

        rev_mask = ~e_mask
        i_filtered_rev = lin[rev_mask]  # spectrum_cut[rev_mask]
        w_filtered_rev = w_filtered[rev_mask]

        ''' USING SUMS
        energy_out_full = np.sum(background_scaled[rev_mask])
        energy_outside = np.sum(i_filtered_rev)
        '''

        # USING TRAPZ
        energy_outside = np.trapezoid(i_filtered_rev, w_filtered_rev)
        energy_out_full = np.trapezoid(background_scaled[rev_mask], w_filtered_rev)
        fulness_background = energy_outside / energy_out_full

        width = data.compute_width_db(w_filtered, spectrum_cut, level=3)
        if width < 5:  # 10:
            fitness = 1000000
            self.gdd_indicator.config(
                text=f'Current GDD: {gdd: .2f}, TOD: {tod: .2f}, FOD: {fod: .2f}, Lambda: {c_lambda: .2f}, Bandwidth: {filter_width: .2f}')
            self.fitness_indicator.config(text=f'Current fitness: {fitness: .2f}')
            return fitness

        flatness = data.compute_spectral_flatness_in_range(w_filtered, i_filtered, 805, 15)
        inside_weight = float(self.inside_weight_entry.get())
        outside_weight = float(self.outside_weight_entry.get())

        # fitness = -1*(width*fulness/energy_outside)
        # fitness = -1*flatness*(fulness-fulness_background)
        # fitness = -1*(flatness+(inside_weight*fulness - outside_weight*fulness_background))
        fitness = -1 * (((1 + flatness) ** 2) * (inside_weight * fulness - outside_weight * fulness_background))
        self.gdd_indicator.config(
            text=f'Current GDD: {gdd: .2f}, TOD: {tod: .2f}, FOD: {fod: .2f}, Lambda: {c_lambda: .2f}, Bandwidth: {filter_width: .2f}')
        self.fitness_indicator.config(text=f'Current fitness: {fitness: .2f}')
        self.talk(
            f'Inside: {inside_weight * fulness: .4f} Outside: {outside_weight * fulness_background: .4f}, flatness: {flatness: .2f}')
        return fitness

    def show_best_feedback_plot(self):
        xmin = float(self.lambda_min_entry.get())
        xmax = float(self.lambda_max_entry.get())

        self.best_spectrum_line.set_xdata(self.best_spectrum_xdata)
        self.best_spectrum_line.set_ydata(self.best_spectrum_ydata_lin)
        self.best_spectrum_line2.set_xdata(self.best_spectrum_xdata)
        lin = np.array(self.best_spectrum_ydata_lin, dtype=float)
        lin[lin <= 0] = 1e-20
        self.best_spectrum_ydata_log = 10 * np.log10(lin / 1000)
        self.best_spectrum_line2.set_ydata(self.best_spectrum_ydata_log)
        self.best_spectrum_ax.set_xlim(xmin, xmax)
        self.best_spectrum_ax.set_ylim(0, 1.1 * np.max(self.best_spectrum_ydata_lin))
        self.best_spectrum_ax2.set_xlim(xmin, xmax)
        self.best_spectrum_ax2.set_ylim(0, 1.1 * np.max(self.best_spectrum_ydata_log))
        self.best_spectrum_ax2.set_ylim(-20, 20)

        self.best_spectrum_line.set_visible(True)
        self.best_spectrum_line2.set_visible(True)
        self.best_spectrum_canvas.draw()

    def update_best_feedback_plot(self, gdd, tod, fod, central_lambda, filter_width):
        self.set_gdd_tod_fod(gdd, tod, fod, central_lambda, filter_width)
        # time.sleep(int(self.sample_delay.get()) / 1000)
        self.read_qmini()
        self.best_spectrum_xdata, self.best_spectrum_ydata_lin = self.qmini_xdata, self.qmini_ydata
        self.show_best_feedback_plot()

    def formulate_data_for_saving(self, best_gdd, best_tod, best_fod, best_lambda_c, best_filter_width, best_fitness):
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
            "qmini": {
                "xdata": self.best_spectrum_xdata,
                "ydata": self.best_spectrum_ydata_lin,
            },
            "fitness": best_fitness,
            "fitness_curve": self.fitness_list,
        }

        return results

if __name__ == "__main__":
    root = tk.Tk()
    app = QminiGUI(root)
    root.mainloop()