import threading, time, asyncio
from BaseGUI import BaseGUI
import numpy as np
import tkinter as tk
import data_processing as data
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from waveshaper import scale_0_1_to_limit, thz_to_nm
from femtoeasy import frog
import ctypes

class frogGUI(BaseGUI):
    def setup_feedback_plot(self):
        #self.frog_figure = Figure(figsize=(5, 4), dpi=100, tight_layout = True)
        self.frog_figure = Figure(figsize=self.get_figure_size(), dpi=100, tight_layout=True)
        self.frog_ax = self.frog_figure.add_subplot(111)
        self.frog_ax.set_title("FROG spectrum")
        self.frog_ax.set_xlabel("Wavelength (nm)")
        self.frog_ax.set_ylabel("Intensity")
        self.frog_line, = self.frog_ax.plot([], [], color="darkviolet")
        self.frog_ax.grid(True, color="darkviolet", alpha=0.3)

        self.frog_ax2 = self.frog_ax.twinx()
        self.frog_ax2.set_ylabel("Spectral phase")
        self.frog_line2, = self.frog_ax2.plot([], [], color="hotpink")
        self.frog_ax2.grid(True, color="hotpink", alpha=0.3)
        self.treshold_line = self.frog_ax2.axhline(
            y=np.nan, linestyle="--", color="red", alpha=0.8
        )
        self.treshold_text = self.frog_ax2.text(
            0.95, 0, "15dB: ",
            color="red",
            ha="right", va="bottom",
            transform=self.frog_ax2.get_yaxis_transform()
        )
        self.rectangle_line, = self.frog_ax2.plot([], [], color="darkmagenta")

        self.frog_canvas = FigureCanvasTkAgg(self.frog_figure, master=self.left_frame)
        self.frog_canvas.draw()
        self.frog_canvas.get_tk_widget().grid(row=0, column=0)

    def setup_best_feedback_plot(self):
        #self.best_frog_figure = Figure(figsize=(5, 4), dpi=100, tight_layout=True)
        self.best_frog_figure = Figure(figsize=self.get_figure_size(), dpi=100, tight_layout=True)
        self.best_frog_ax = self.best_frog_figure.add_subplot(111)
        self.best_frog_ax.set_title("Frog")
        self.best_frog_ax.set_xlabel("Wavelength (nm)")
        self.best_frog_ax.set_ylabel(r"Intensity")
        self.best_frog_line, = self.best_frog_ax.plot([], [], color="darkviolet")
        self.best_frog_ax.grid(True, color="darkviolet", alpha=0.3)

        self.best_frog_ax2 = self.best_frog_ax.twinx()
        self.best_frog_ax2.set_ylabel("Phase [rad]")
        self.best_frog_line2, = self.best_frog_ax2.plot([], [], color="hotpink")
        self.best_frog_ax2.grid(True, color="hotpink", alpha=0.3)

        self.best_frog_canvas = FigureCanvasTkAgg(self.best_frog_figure, master=self.left_frame)
        self.best_frog_canvas.draw()
        self.best_frog_canvas.get_tk_widget().grid(row=0, column=1)

    def setup_feedback_panel(self):
        read_frame = ttk.LabelFrame(self.right_frame, text="FROG")
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
        self.frog_scale_lin = ttk.Checkbutton(read_frame, text = "Linear scale", variable=self.scale_lin)
        self.frog_scale_lin.grid(row=2, column=0)

        self.show_phase = tk.BooleanVar(value=True)
        self.frog_show_phase = ttk.Checkbutton(
            read_frame,
            text="Show phase",
            variable=self.show_phase,
            command=self.show_feedback_plot,
        )
        self.frog_show_phase.grid(row=2, column=1)

        ttk.Label(read_frame, text="Measurement frequency [Hz]:").grid(row=4, column=0, sticky='w')
        self.continuous_freq_entry = ttk.Entry(read_frame, width=10)
        self.continuous_freq_entry.insert(0, 10)
        self.continuous_freq_entry.grid(row=4, column=1)

        self.frog_continuous_button = ttk.Button(read_frame, text="Measure continuously",
                                                  command=self.start_continuous_read)
        self.frog_continuous_button.grid(row=5, column=0, pady=5)

        self.read_button = ttk.Button(read_frame, text="Read one measurement", command=self.read_frog)
        self.read_button.grid(row=5, column=1, pady=5)

    def connect_to_feedback(self):
        '''
        self.frog_dev = frog
        self.frog_dev.start_frog_runners()
        self.frog_dev.start_acquisition()
        '''
        # 1. Tworzymy instancję klasy frog podłączającą się do naszego serwera mocka (port 8000)
        self.frog_dev = frog(url="http://localhost:8000/")

        # 2. Uruchamiamy asynchroniczne uruchomienie serwera w pętli zdarzeń asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(self._async_connect())

    async def _async_connect(self):
        await self.frog_dev.start_frog_runners()
        await self.frog_dev.start_acquisition()

    def read_frog(self, update_plot=True):
        # Pobieranie danych w sposób synchroniczny dla interfejsu Tkinter
        acquired_data, retrieved_data = asyncio.run(
            self.frog_dev.get_frog_data()
        )

        # Inicjalizacja na wypadek chwilowego braku rekonstrukcji
        self.frog_xdata = getattr(self, "frog_xdata", [])
        self.frog_ydata = getattr(self, "frog_ydata", [])
        self.frog_phase_ydata = getattr(self, "frog_phase_ydata", [])

        # Wyciągamy punkty widma i fazy do zmiennych używanych przez wykres GUI
        if retrieved_data and "dataSeries" in retrieved_data:
            ds = retrieved_data["dataSeries"]
            spectrum = ds.get("spectralProfileMod", {})
            phase = ds.get("spectralProfilePhase", {})

            x_raw = spectrum.get("xValues", [])
            y_raw = spectrum.get("yValues", [])
            phase_raw = phase.get("yValues", [])

            # Odwracamy kolejność punktów, jeśli oś X jest malejąca (1620 nm -> 768 nm)
            if len(x_raw) > 1 and x_raw[0] > x_raw[-1]:
                self.frog_xdata = x_raw[::-1]
                self.frog_ydata = y_raw[::-1]
                self.frog_phase_ydata = phase_raw[::-1]
            else:
                self.frog_xdata = x_raw
                self.frog_ydata = y_raw
                self.frog_phase_ydata = phase_raw

        if update_plot:
            self.show_feedback_plot()

        return acquired_data, retrieved_data

    def frog_read_measurement(self, feedback_device):
        '''
        loop = asyncio.get_event_loop()
        acquired_data, retrieved_data = loop.run_until_complete(
            self.feedback_device.get_frog_data()
        )
        '''
        acquired_data, retrieved_data = asyncio.run(
            self.frog_dev.get_frog_data()
        )

        if retrieved_data and "dataSeries" in acquired_data:
            spectrum = retrieved_data["dataSeries"].get("retrievedSpectrum", {})
            phase = retrieved_data["dataSeries"].get("SpectralPhase", {})
            x = spectrum.get("xValues", [])
            y = spectrum.get("yValues", [])
            phase_y = phase.get("yValues", [])

        return x, y, phase_y

    def read_frog_background(self):
        '''działa w WĄTKU, nie blokuje Tkintera'''
        while self.feedback_continuous:
            delay = 1 / float(self.continuous_freq_entry.get())
            x, y, phase_y = self.frog_read_measurement(self.feedback_device)

            self.root.after(0, self.update_feedback_plot, x, y, phase_y)
            time.sleep(delay)

    def update_feedback_plot(self, x, y, phase_y=None):
        self.frog_xdata = x
        self.frog_ydata = y
        if phase_y is not None:
            self.frog_phase_ydata = phase_y
        self.show_feedback_plot()

    def start_continuous_read(self):
        '''wywołane przy kliknięciu checkbutton'''
        if not self.feedback_continuous:
            self.feedback_continuous = True
            self.frog_continuous_button.configure(style='Green.TButton')
            self.talk("Starting continuous FROG measurements")
            # uruchom nowy wątek
            t = threading.Thread(target=self.read_frog_background, daemon=True)
            t.start()
        else:
            # po odznaczeniu - po prostu pętla się przerwie
            self.feedback_continuous = False
            self.frog_continuous_button.configure(style="Black.TButton")
            self.talk("Stopped continuous FROG measurements")

    def show_feedback_plot(self):
        if not hasattr(self, "frog_xdata") or len(self.frog_xdata) == 0:
            return

        xmin = float(self.lambda_min_entry.get())
        xmax = float(self.lambda_max_entry.get())

        wavelengths = np.array(self.frog_xdata, dtype=float)
        intensities = np.array(self.frog_ydata, dtype=float)
        mask = (wavelengths >= xmin) & (wavelengths <= xmax)
        w_filtered = wavelengths[mask]
        i_filtered = intensities[mask]

        # Lewa oś (ax): Widmo + próg szerokości + prostokąt pasma 1550 nm
        if self.scale_lin.get():
            self.frog_line.set_xdata(wavelengths)
            self.frog_line.set_ydata(intensities)
            self.frog_line.set_visible(True)
            self.frog_ax.set_xlim(xmin, xmax)

            y_max = 1.1 * np.max(i_filtered) if len(i_filtered) > 0 else 1.0
            self.frog_ax.set_ylim(0, max(1e-9, y_max))
            self.frog_ax.get_yaxis().set_visible(True)

            if len(w_filtered) > 1 and np.max(i_filtered) > 0:
                # Obliczenie szerokości 3 dB
                width = data.compute_width_db(w_filtered, i_filtered, level=3)
                treshold_value = 0.5 * np.max(i_filtered)

                self.treshold_line.set_xdata([xmin, xmax])
                self.treshold_line.set_ydata([treshold_value, treshold_value])
                self.treshold_line.set_visible(True)

                self.treshold_text.set_y(treshold_value)
                self.treshold_text.set_text(f"3 dB: {width: .2f} nm")
                self.treshold_text.set_visible(True)

                # Prostokąt docelowego pasma wokół 150 nm
                lambda_min = 1520.0     # nm, może być do zmiany
                lambda_max = 1580.0     # nm, może być do zmiany
                rectangle = ((w_filtered >= lambda_min) & (w_filtered <= lambda_max)).astype(float)
                rectangle_scaled = rectangle * (0.9 * np.max(i_filtered))
                self.rectangle_line.set_xdata(w_filtered)
                self.rectangle_line.set_ydata(rectangle_scaled)
                self.rectangle_line.set_visible(True)
            else:
                self.frog_line.set_visible(False)
                self.treshold_line.set_visible(False)
                self.treshold_text.set_visible(False)
                self.rectangle_line.set_visible(False)
                self.frog_ax.get_yaxis().set_visible(False)

            # Prawa oś (ax2): Faza spektralna
            has_phase = (
                hasattr(self, "frog_phase_ydata")
                and len(self.frog_phase_ydata) == len(wavelengths)
            )
            if self.show_phase.get() and has_phase:
                phases = np.array(self.frog_phase_ydata, dtype=float)
                self.frog_line2.set_xdata(wavelengths)
                self.frog_line2.set_ydata(phases)
                self.frog_line2.set_visible(True)
                self.frog_ax2.set_xlim(xmin, xmax)

                p_filtered = phases[mask]
                if len(p_filtered) > 0:
                    self.frog_ax2.set_ylim(np.min(p_filtered) - 0.5, np.max(p_filtered) + 0.5)
                self.frog_ax2.get_yaxis().set_visible(True)

            else:
                self.frog_line2.set_visible(False)
                self.frog_ax2.get_yaxis().set_visible(False)

            self.frog_canvas.draw()

    def prepare_for_optimization(self):
        if self.frog_continuous_button["state"] == "disabled":
            # nie rob nic jeśli optymalizacja juz działa
            return

        # zablokuj przycisk
        self.frog_continuous_button.config(state="disabled")
        self.optimize_button.config(state="disabled")
        self.root.update_idletasks()

    def prepare_after_optimization(self):
        self.frog_continuous_button.after(0, lambda: self.frog_continuous_button.config(state="normal"))
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

        start_time = time.perf_counter()
        r = self.set_gdd_tod_fod(gdd, tod, fod, c_lambda, filter_width, update_plot=False)
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        print(f'Czas wykonania shaper: {elapsed:.6f} s, wiadomość {r}')
        # time.sleep(int(self.sample_delay.get())/1000)
        self.read_frog(update_plot=False)

        # zaktualizuj wykresy
        self.show_waveshaper_plot()
        self.show_feedback_plot()

        wavelengths = np.array(self.frog_xdata, dtype=float)
        intensities = np.array(self.frog_ydata, dtype=float)

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

        # USING TRAPZ
        energy_inside = np.trapezoid(i_filtered_e, w_filtered_e)
        energy_full = np.trapezoid(rectangle_scaled[e_mask], w_filtered_e)

        fulness = energy_inside / energy_full

        rev_mask = ~e_mask
        i_filtered_rev = lin[rev_mask]  # spectrum_cut[rev_mask]
        w_filtered_rev = w_filtered[rev_mask]

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

        fitness = -1 * (((1 + flatness) ** 2) * (inside_weight * fulness - outside_weight * fulness_background))
        self.gdd_indicator.config(
            text=f'Current GDD: {gdd: .2f}, TOD: {tod: .2f}, FOD: {fod: .2f}, Lambda: {c_lambda: .2f}, Bandwidth: {filter_width: .2f}')
        self.fitness_indicator.config(text=f'Current fitness: {fitness: .2f}')
        self.talk(
            f'Inside: {inside_weight * fulness: .4f} Outside: {outside_weight * fulness_background: .4f}, flatness: {flatness: .2f}')
        return fitness

    def show_best_feedback_plot(self):
        if not hasattr(self, "best_frog_xdata") or len(self.best_frog_xdata) == 0:
            return

        xmin = float(self.lambda_min_entry.get())
        xmax = float(self.lambda_max_entry.get())

        wavelengths = np.array(self.best_frog_xdata, dtype=float)
        intensities = np.array(self.best_frog_ydata, dtype=float)
        mask = (wavelengths >= xmin) & (wavelengths <= xmax)
        w_filtered = wavelengths[mask]
        i_filtered = intensities[mask]

        # 1. Lewa oś (best_frog_ax): Najlepsze widmo + próg 3 dB + prostokąt 1550 nm
        if self.scale_lin.get():
            self.best_frog_line.set_xdata(wavelengths)
            self.best_frog_line.set_ydata(intensities)
            self.best_frog_line.set_visible(True)
            self.best_frog_ax.set_xlim(xmin, xmax)

            y_max = 1.1 * np.max(i_filtered) if len(i_filtered) > 0 else 1.0
            self.best_frog_ax.set_ylim(0, max(1e-9, y_max))
            self.best_frog_ax.get_yaxis().set_visible(True)

            if len(w_filtered) > 1 and np.max(i_filtered) > 0:
                width = data.compute_width_db(w_filtered, i_filtered, level=3)
                treshold_value = 0.5 * np.max(i_filtered)

                self.best_treshold_line.set_xdata([xmin, xmax])
                self.best_treshold_line.set_ydata([treshold_value, treshold_value])
                self.best_treshold_line.set_visible(True)

                self.best_treshold_text.set_y(treshold_value)
                self.best_treshold_text.set_text(f"3 dB: {width:.2f} nm")
                self.best_treshold_text.set_visible(True)

                # Prostokąt pasma docelowego wokół 1550 nm
                lambda_min = 1520.0  # nm (dostosuj dolną granicę pasma)
                lambda_max = 1580.0  # nm (dostosuj górną granicę pasma)
                rectangle = ((w_filtered >= lambda_min) & (w_filtered <= lambda_max)).astype(float)
                rectangle_scaled = rectangle * (0.9 * np.max(i_filtered))
                self.best_rectangle_line.set_xdata(w_filtered)
                self.best_rectangle_line.set_ydata(rectangle_scaled)
                self.best_rectangle_line.set_visible(True)
        else:
            self.best_frog_line.set_visible(False)
            self.best_treshold_line.set_visible(False)
            self.best_treshold_text.set_visible(False)
            self.best_rectangle_line.set_visible(False)
            self.best_frog_ax.get_yaxis().set_visible(False)

        # 2. Prawa oś (best_frog_ax2): Najlepsza faza widmowa (spectralProfilePhase)
        has_phase = (
                hasattr(self, "best_frog_phase_ydata")
                and len(self.best_frog_phase_ydata) == len(wavelengths)
        )
        if self.show_phase.get() and has_phase:
            phases = np.array(self.best_frog_phase_ydata, dtype=float)
            self.best_frog_line2.set_xdata(wavelengths)
            self.best_frog_line2.set_ydata(phases)
            self.best_frog_line2.set_visible(True)
            self.best_frog_ax2.set_xlim(xmin, xmax)

            p_filtered = phases[mask]
            if len(p_filtered) > 0:
                self.best_frog_ax2.set_ylim(np.min(p_filtered) - 0.5, np.max(p_filtered) + 0.5)
            self.best_frog_ax2.get_yaxis().set_visible(True)
        else:
            self.best_frog_line2.set_visible(False)
            self.best_frog_ax2.get_yaxis().set_visible(False)

        self.best_frog_canvas.draw()

    def update_best_feedback_plot(self, gdd, tod, fod, central_lambda, filter_width):
        self.set_gdd_tod_fod(gdd, tod, fod, central_lambda, filter_width, update_plot=False)
        self.read_frog(update_plot=False)
        self.best_frog_xdata = list(getattr(self, "frog_xdata", []))
        self.best_frog_ydata = list(getattr(self, "frog_ydata", []))
        self.best_frog_phase_ydata = list(getattr(self, "frog_phase_ydata", []))
        # Odświeżamy wykres w głównym wątku Tkintera
        self.root.after(0, self.show_best_feedback_plot)

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
            "frog": {
                "xdata": getattr(self, "best_frog_xdata", getattr(self, "frog_xdata", [])),
                "ydata": getattr(self, "best_frog_ydata", getattr(self, "frog_ydata", [])),
                "phase_ydata": getattr(self, "best_frog_phase_ydata", getattr(self, "frog_phase_ydata", [])),
            },
            "fitness": best_fitness,
            "fitness_curve": self.fitness_list,
        }

        return results


if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1) #obsługa wysokiej rozdzielczości
    except Exception:
        pass

    root = tk.Tk()
    app = frogGUI(root)
    root.mainloop()