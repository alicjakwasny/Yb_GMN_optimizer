import threading, time
from BaseGUI import BaseGUI
from osa import OsaDevice
import numpy as np
import tkinter as tk
import data_processing as data
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from waveshaper import scale_0_1_to_limit, thz_to_nm

class OsaGUI(BaseGUI):
    def setup_feedback_plot(self):
        self.osa_figure = Figure(figsize=(5, 4), dpi=100, tight_layout=True)
        self.osa_ax = self.osa_figure.add_subplot(111)
        self.osa_ax.set_title("Spectrum from OSA")
        self.osa_ax.set_xlabel("Wavelength (nm)")
        self.osa_ax.set_ylabel(r"Intensity ($\mu$W/nm)")
        self.osa_line, = self.osa_ax.plot([], [], color="darkviolet")
        self.osa_ax.grid(True, color="darkviolet", alpha=0.3)

        self.osa_ax2 = self.osa_ax.twinx()
        self.osa_ax2.set_ylabel("Intensity [dBm]")
        self.osa_line2, = self.osa_ax2.plot([], [], color="hotpink")
        self.osa_ax2.grid(True, color="hotpink", alpha=0.3)
        self.threshold_line = self.osa_ax2.axhline(
            y=np.nan, linestyle="--", color="red", alpha=0.8
        )
        self.threshold_text = self.osa_ax2.text(
            0.95, 0, "15dB: ",
            color="red",
            ha="right", va="bottom",
            transform=self.osa_ax2.get_yaxis_transform()
        )
        self.rectangle_line, = self.osa_ax.plot([], [], color="darkmagenta")

        self.osa_canvas = FigureCanvasTkAgg(self.osa_figure, master=self.left_frame)
        self.osa_canvas.draw()
        self.osa_canvas.get_tk_widget().grid(row=0, column=0)

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
        read_frame = ttk.LabelFrame(self.right_frame, text="OSA")
        read_frame.pack(fill='x', pady=5)

        ttk.Label(read_frame, text="Min wavelength:").grid(row=0, column=0, sticky='w')
        self.lambda_min_entry = ttk.Entry(read_frame, width=10)
        self.lambda_min_entry.insert(0, 1500)
        self.lambda_min_entry.grid(row=0, column=1)

        ttk.Label(read_frame, text="Max wavelength:").grid(row=1, column=0, sticky='w')
        self.lambda_max_entry = ttk.Entry(read_frame, width=10)
        self.lambda_max_entry.insert(0, 1720)
        self.lambda_max_entry.grid(row=1, column=1)

        self.scale_lin = tk.BooleanVar(value=True)
        self.osa_scale_lin = ttk.Checkbutton(read_frame, text="Linear scale", variable=self.scale_lin)
        self.osa_scale_lin.grid(row=2, column=0)

        self.scale_log = tk.BooleanVar(value=True)
        self.osa_scale_log = ttk.Checkbutton(read_frame, text="Logarythmic scale", variable=self.scale_log)
        self.osa_scale_log.grid(row=2, column=1)

        ttk.Label(read_frame, text="Measurement frequency [Hz]:").grid(row=4, column=0, sticky='w')
        self.continuous_freq_entry = ttk.Entry(read_frame, width=10)
        self.continuous_freq_entry.insert(0, 10)
        self.continuous_freq_entry.grid(row=4, column=1)

        self.osa_continuous_button = ttk.Button(read_frame, text="Measure continuously",
                                                  command=self.start_continuous_read)
        self.osa_continuous_button.grid(row=5, column=0, pady=5)

        self.read_button = ttk.Button(read_frame, text="Read one spectrum", command=self.read_osa)
        self.read_button.grid(row=5, column=1, pady=5)

    def connect_to_feedback(self):
        self.feedback_device = OsaDevice()
        self.feedback_device_name = "OSA"

    def read_osa(self, update_plot=True):
        xdata, ydata = self.feedback_device.single()
        self.osa_xdata = xdata
        self.osa_ydata = ydata*1000

        if update_plot:
            self.root.after(0, self.show_feedback_plot)

    def read_osa_background(self):
        '''działa w WĄTKU, nie blokuje Tkintera'''
        while self.feedback_continuous:
            delay = 1 / float(self.continuous_freq_entry.get())
            x, y = self.feedback_device.single()
            y2 = y*1000

            self.root.after(0, self.update_feedback_plot, x, y2)
            time.sleep(delay)

    def update_feedback_plot(self, x, y):
        '''Wywoływane w wątku głównym'''
        self.osa_xdata = x
        self.osa_ydata = y
        self.show_feedback_plot()

    def start_continuous_read(self):
        '''wywołane przy kliknięciu checkbutton'''
        if not self.feedback_continuous:
            self.feedback_continuous = True
            self.osa_continuous_button.configure(style='Green.TButton')
            self.talk("Starting continuous OSA measurements")
            # uruchom nowy wątek
            t = threading.Thread(target=self.read_osa_background, daemon=True)
            t.start()
        else:
            # po odznaczeniu - po prostu pętla się przerwie
            self.feedback_continuous = False
            self.osa_continuous_button.configure(style="Black.TButton")
            self.talk("Stopped continuous OSA measurement")

    def show_feedback_plot(self):
        xmin = float(self.lambda_min_entry.get())
        xmax = float(self.lambda_max_entry.get())

        if self.scale_lin.get():
            self.osa_line.set_xdata(self.osa_xdata)
            self.osa_line.set_ydata(self.osa_ydata)
            self.osa_line.set_visible(True)
            self.osa_ax.set_xlim(xmin, xmax)
            self.osa_ax.set_ylim(0, 1.1 * np.max(self.osa_ydata))

            self.osa_ax.get_yaxis().set_visible(True)

        else:
            self.osa_line.set_visible(False)
            self.osa_ax.get_yaxis().set_visible(False)

        if self.scale_log.get():
            self.osa_line2.set_xdata(self.osa_xdata)
            lin = np.array(self.osa_ydata, dtype=float)
            lin[lin <= 0] = 1e-20
            self.osa_ydata_log = 10 * np.log10(lin / 1000)
            self.osa_line2.set_ydata(self.osa_ydata_log)

            self.osa_line2.set_visible(True)
            self.osa_ax2.set_xlim(xmin, xmax)
            #self.osa_ax2.set_ylim(-20, 20)
            self.osa_ax2.set_ylim(-60, 0)
            threshold_value = max(self.osa_ydata_log) - 9
            self.threshold_line.set_ydata([threshold_value, threshold_value])
            # aktualizacja napisu
            wavelengths = np.array(self.osa_xdata, dtype=float)
            intensities = np.array(self.osa_ydata_log, dtype=float)
            mask = (wavelengths >= xmin) & (wavelengths <= xmax)
            w_filtered = wavelengths[mask]
            i_filtered = intensities[mask]

            width = data.compute_width_db(w_filtered, i_filtered, level=9)
            self.threshold_text.set_y(threshold_value)

            self.threshold_text.set_text(f"9 dB: {width:.2f} nm")

            
            # prostokąt
            lambda_min = 1565  # nm
            lambda_max = 1675  # nm
            rectangle = ((w_filtered >= lambda_min) & (w_filtered <= lambda_max)).astype(float)  # zrob prostokat
            I_min = 0  # minimum value of intensity
            intensities_lin = np.array(self.osa_ydata, dtype=float)
            i_filtered_lin = intensities_lin[mask]
            I_max = np.max(i_filtered_lin)
            I_max_db = np.max(i_filtered)
            #if I_max < -5:
            if I_max_db < -40:
                #kara
                I_max = I_min
            elif I_max < 5:
                I_max = 5
            rectangle_scaled = rectangle * (I_max - I_min) + I_min  # wyskaluj prostokat
            self.rectangle_line.set_xdata(w_filtered)
            self.rectangle_line.set_ydata(rectangle_scaled)

            self.osa_ax2.get_yaxis().set_visible(True)
        else:
            self.osa_line2.set_visible(False)
            self.osa_ax2.get_yaxis().set_visible(False)


        self.osa_canvas.draw()

    def prepare_for_optimization(self):
        if self.osa_continuous_button["state"] == "disabled":
            # nie rób nic jeśli optymalizacja już dziala
            return

        # zablokuj przycisk
        self.osa_continuous_button.config(state="disabled")
        self.optimize_button.config(state="disabled")
        self.root.update_idletasks()

    def prepare_after_optimization(self):
        self.osa_continuous_button.after(0, lambda: self.osa_continuous_button.config(state="normal"))
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
        self.read_osa(update_plot=False)

        # zaktualizuj wykresy
        self.show_waveshaper_plot()
        self.show_feedback_plot()

        wavelengths = np.array(self.osa_xdata, dtype=float)
        intensities = np.array(self.osa_ydata, dtype=float)

        xmin = float(self.lambda_min_entry.get())
        xmax = float(self.lambda_max_entry.get())

        mask = (wavelengths >= xmin) & (wavelengths <= xmax)

        w_filtered = wavelengths[mask]
        i_filtered = intensities[mask]

        lin = i_filtered
        lin[lin <= 0] = 1e-20
        intensities_db = 10 * np.log10(lin / 1000)

        lambda_min = 1565  # nm
        lambda_max = 1675  # nm
        rectangle = ((w_filtered >= lambda_min) & (w_filtered <= lambda_max)).astype(float)  # zrob prostokat
        I_min = -40  # minimum value of intensity
        I_max = np.max(intensities_db)
        if I_max < -40:  # 7:
            fitness = 1000000
            self.talk('Kara za zbyt słaby sygnał!')
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
        spectrum_cut[intensities_db < -47] = -47

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

        #width = data.compute_width_db(w_filtered, spectrum_cut, level=3)
        width = data.compute_width_db(w_filtered, spectrum_cut, level=9)
        if width < 3:  # 10:
            fitness = 1000000
            self.talk(f'Kara za zbyt wąskie widmo! {width}')
            self.gdd_indicator.config(
                text=f'Current GDD: {gdd: .2f}, TOD: {tod: .2f}, FOD: {fod: .2f}, Lambda: {c_lambda: .2f}, Bandwidth: {filter_width: .2f}')
            self.fitness_indicator.config(text=f'Current fitness: {fitness: .2f}')
            return fitness

        # warunek, czy jest CW
        idx = np.argmax(intensities)
        if not rectangle[idx]:
            fitness = 1000000
            self.talk(f'Kara za max poza prostokątem!')
            return fitness

        flatness = data.compute_spectral_flatness_in_range(w_filtered, i_filtered, 1610, 30)
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
        #self.best_spectrum_ax2.set_ylim(-20, 20)
        self.best_spectrum_ax2.set_ylim(-60, 0)

        self.best_spectrum_line.set_visible(True)
        self.best_spectrum_line2.set_visible(True)
        self.best_spectrum_canvas.draw()

    def update_best_feedback_plot(self, gdd, tod, fod, central_lambda, filter_width):
        self.set_gdd_tod_fod(gdd, tod, fod, central_lambda, filter_width)
        # time.sleep(int(self.sample_delay.get()) / 1000)
        self.read_osa()
        self.best_spectrum_xdata, self.best_spectrum_ydata_lin = self.osa_xdata, self.osa_ydata
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
            "OSA": {
                "xdata": self.best_spectrum_xdata,
                "ydata": self.best_spectrum_ydata_lin,
            },
            "fitness": best_fitness,
            "fitness_curve": self.fitness_list,
        }

        #TODO: fix the format

        return results

if __name__ == "__main__":
    root = tk.Tk()
    app = OsaGUI(root)
    root.mainloop()