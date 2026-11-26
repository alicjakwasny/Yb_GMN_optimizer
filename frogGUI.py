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
        self.treshold_line = self.frog_ax.axhline(
            y=np.nan, linestyle="--", color="red", alpha=0.8
        )
        self.treshold_text = self.frog_ax.text(
            0.95, 0, "3dB: ",
            color="red",
            ha="right", va="bottom",
            transform=self.frog_ax.get_yaxis_transform()
        )

        self.frog_canvas = FigureCanvasTkAgg(self.frog_figure, master=self.left_frame)
        self.frog_canvas.draw()
        self.frog_canvas.get_tk_widget().grid(row=0, column=0)

    def setup_best_feedback_plot(self):
        self.best_frog_figure = Figure(figsize=self.get_figure_size(), dpi=100, tight_layout=True)
        self.best_frog_ax = self.best_frog_figure.add_subplot(111)
        self.best_frog_ax.set_title("Best FROG Spectrum")
        self.best_frog_ax.set_xlabel("Wavelength (nm)")
        self.best_frog_ax.set_ylabel(r"Intensity")
        self.best_frog_line, = self.best_frog_ax.plot([], [], color="darkviolet")
        self.best_frog_ax.grid(True, color="darkviolet", alpha=0.3)

        self.best_frog_ax2 = self.best_frog_ax.twinx()
        self.best_frog_ax2.set_ylabel("Phase [rad]")
        self.best_frog_line2, = self.best_frog_ax2.plot([], [], color="hotpink")
        self.best_frog_ax2.grid(True, color="hotpink", alpha=0.3)

        self.best_treshold_line = self.best_frog_ax.axhline(
            y=np.nan, linestyle="--", color="red", alpha=0.8
        )
        self.best_treshold_text = self.best_frog_ax.text(
            0.95, 0, "3 dB: ",
            color="red",
            ha="right", va="bottom",
            transform=self.best_frog_ax.get_yaxis_transform()
        )

        self.best_frog_canvas = FigureCanvasTkAgg(self.best_frog_figure, master=self.left_frame)
        self.best_frog_canvas.draw()
        self.best_frog_canvas.get_tk_widget().grid(row=0, column=1)

    def setup_feedback_panel(self):
        read_frame = ttk.LabelFrame(self.right_frame, text="FROG")
        read_frame.pack(fill='x', pady=5)

        ttk.Label(read_frame, text="Min wavelength:").grid(row=0, column=0, sticky='w')
        self.lambda_min_entry = ttk.Entry(read_frame, width=10)
        self.lambda_min_entry.insert(0, 800)
        self.lambda_min_entry.grid(row=0, column=1)

        ttk.Label(read_frame, text="Max wavelength:").grid(row=1, column=0, sticky='w')
        self.lambda_max_entry = ttk.Entry(read_frame, width=10)
        self.lambda_max_entry.insert(0, 1250)
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
        self.frog_retrieved_data = retrieved_data.get("retrievedData", {})

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

    def frog_read_measurement(self, feedback_device=None):
        self.read_frog(update_plot=False)
        return self.frog_xdata, self.frog_ydata, self.frog_phase_ydata

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

        # Lewa oś (ax): Widmo + próg szerokości
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

            else:
                self.frog_line.set_visible(False)
                self.treshold_line.set_visible(False)
                self.treshold_text.set_visible(False)
                self.frog_ax.get_yaxis().set_visible(False)

            # 2. Prawa oś (ax2): Faza widmowa tylko tam, gdzie intensywność > 0.1 * max
            has_phase = (
                    hasattr(self, "frog_phase_ydata")
                    and len(self.frog_phase_ydata) == len(wavelengths)
            )
            if self.show_phase.get() and has_phase and len(intensities) > 0:
                phases = np.array(self.frog_phase_ydata, dtype=float)

                # Próg 0.1 względem maksimum widma (jeśli widmo jest znormalizowane do 1, to dokładnie 0.1)
                intensity_threshold = 0.1 * np.max(intensities)
                phases_masked = np.where(intensities > intensity_threshold, phases, np.nan)

                self.frog_line2.set_xdata(wavelengths)
                self.frog_line2.set_ydata(phases_masked)
                self.frog_line2.set_visible(True)
                self.frog_ax2.set_xlim(xmin, xmax)

                p_filtered = phases_masked[mask]
                if np.any(~np.isnan(p_filtered)):
                    self.frog_ax2.set_ylim(np.nanmin(p_filtered) - 0.5, np.nanmax(p_filtered) + 0.5)
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

    def objective_gdd_tod_fod(self, gdd, tod, fod, c_lambda=None, filter_width=None):
        '''
        Calculates fitness of a pulse with given GDD, TOD, FOD (and optionally c_lambda and filter_width)
        '''

        gdd = float(np.clip(gdd, 0.0, 1.0))
        tod = float(np.clip(tod, 0.0, 1.0))
        fod = float(np.clip(fod, 0.0, 1.0))

        gdd = scale_0_1_to_limit(gdd, float(self.min_gdd_entry.get()), float(self.max_gdd_entry.get()))
        tod = scale_0_1_to_limit(tod, float(self.min_tod_entry.get()), float(self.max_tod_entry.get()))
        fod = scale_0_1_to_limit(fod, float(self.min_fod_entry.get()), float(self.max_fod_entry.get()))

        panel_lambda, panel_width = self._get_panel_filter_params()

        if c_lambda is not None:
            c_lambda = float(np.clip(c_lambda, 0.0, 1.0))
            c_lambda = scale_0_1_to_limit(
                c_lambda,
                float(self.min_central_lambda_entry.get()),
                float(self.max_central_lambda_entry.get())
            )
        else:
            c_lambda = panel_lambda

        if filter_width is not None:
            filter_width = float(np.clip(filter_width, 0.0, 1.0))
            filter_width = scale_0_1_to_limit(
                filter_width,
                float(self.min_filter_width_entry.get()),
                float(self.max_filter_width_entry.get())
            )
        else:
            filter_width = panel_width

        start_time = time.perf_counter()
        r = self.set_gdd_tod_fod(gdd, tod, fod, c_lambda, filter_width, update_plot=False)
        elapsed = time.perf_counter() - start_time
        print(f'Czas wykonania shaper: {elapsed:.6f} s, wiadomość {r}')

        # Pobranie świeżego pomiaru z FROG-a (odwraca oś X i zapisuje self.frog_retrieved_data)
        self.read_frog(update_plot=False)

        # Bezpieczne odświeżenie wykresów z wątku pobocznego
        self.root.after(0, self.show_waveshaper_plot)
        self.root.after(0, self.show_feedback_plot)

        wavelengths = np.array(self.frog_xdata, dtype=float)
        intensities = np.array(self.frog_ydata, dtype=float)

        xmin = float(self.lambda_min_entry.get())
        xmax = float(self.lambda_max_entry.get())
        mask = (wavelengths >= xmin) & (wavelengths <= xmax)

        w_filtered = wavelengths[mask]
        i_filtered = intensities[mask]

        if len(w_filtered) < 5 or np.max(i_filtered) <= 0:
            return self._return_penalty_fitness(gdd, tod, fod, c_lambda, filter_width, "Brak sygnału FROG")

        # 1. SZEROKOŚĆ WIDMA (3 dB)
        width = data.compute_width(w_filtered, i_filtered)
        if width < 0:
            return self._return_penalty_fitness(gdd, tod, fod, c_lambda, filter_width, f"Za wąskie widmo ({width:.2f} nm)")

        # 2. PŁASKOŚĆ WIDMA — dynamiczny środek i szerokość okna na podstawie mierzonego widma
        # Środek okna: środek ciężkości rdzenia widma (I > 0.5 * max) – stabilniejszy niż sam np.argmax przy płaskim szczycie
        fwhm_mask = i_filtered >= (0.5 * np.max(i_filtered))
        if np.any(fwhm_mask):
            peak_wavelength = float(np.average(w_filtered[fwhm_mask], weights=i_filtered[fwhm_mask]))
        else:
            peak_wavelength = float(w_filtered[np.argmax(i_filtered)])

        # Szerokość połówkowa okna: 40% zmierzonej szerokości widma (czyli 80% FWHM wokół środka),
        # przycięta tak, aby nie wyjść poza granice w_filtered
        max_available_half_range = min(peak_wavelength - w_filtered[0], w_filtered[-1] - peak_wavelength)
        half_range = float(np.clip(0.4 * width, 2.0, max(2.0, max_available_half_range)))

        flatness = data.compute_spectral_flatness_in_range(w_filtered, i_filtered, peak_wavelength, half_range)

        # 3. WYŻSZE RZĘDY FAZY Z FITU FROG-A (TOD = Order3, FOD = Order4; GDD = Order2 pomijamy!)
        fit_info = getattr(self, "frog_retrieved_data", {})
        order3 = fit_info.get("spectralPhaseFitOrder3", np.nan)
        order4 = fit_info.get("spectralPhaseFitOrder4", np.nan)

        # Awaryjny fit wielomianem 4. stopnia na masce I > 0.1 * max, gdyby FROG zwrócił NaN
        if np.isnan(order3) or np.isnan(order4):
            phases = np.array(getattr(self, "frog_phase_ydata", []), dtype=float)
            valid_mask = (intensities > 0.1 * np.max(intensities)) & mask
            if len(phases) == len(wavelengths) and np.sum(valid_mask) >= 6:
                c_light = 299792.458  # nm / ps
                omega = 2.0 * np.pi * c_light / wavelengths[valid_mask]
                omega_0 = np.mean(omega)
                phi_unwrapped = np.unwrap(phases[valid_mask])
                # Dopasowanie wielomianu 4. stopnia: p[0]*dw^4 + p[1]*dw^3 + p[2]*dw^2 + ...
                poly_coeffs = np.polyfit(omega - omega_0, phi_unwrapped, deg=4)
                # Przeliczenie z ps^3 / ps^4 na fs^3 / fs^4 (1 ps = 1000 fs)
                order4 = abs(poly_coeffs[0] * 24.0 * 1e12)
                order3 = abs(poly_coeffs[1] * 6.0 * 1e9)
            else:
                return self._return_penalty_fitness(gdd, tod, fod, c_lambda, filter_width, "NaN w ficie fazy FROG")

        # Normalizacja składników funkcji kosztu (wszystkie bezwymiarowe, cel: minimalizacja -> 0)
        target_width = 200.0   # nm (wartość odniesienia dla szerokości)
        tod_scale = 1e4       # fs^3 (wartość odniesienia dla Order3)
        fod_scale = 1e7       # fs^4 (wartość odniesienia dla Order4)

        cost_width = target_width / (width + 1e-3)
        cost_flatness = flatness
        cost_phase = (abs(order3) / tod_scale) ** 2 + (abs(order4) / fod_scale) ** 2

        w_width = float(self.inside_weight_entry.get())
        w_phase = float(self.outside_weight_entry.get())
        w_flat = 1.0

        fitness = (w_width * cost_width) + (w_flat * cost_flatness) + (w_phase * cost_phase)
        self._update_fitness_indicators(
            gdd,
            tod,
            fod,
            c_lambda=c_lambda,
            filter_width=filter_width,
            fitness=fitness,
            log_msg=(
                f"Peak: {peak_wavelength:.1f} nm, Width: {width:.2f} nm, "
                f"Flat: {flatness:.3f}, TOD_fit: {order3:.1f}, FOD_fit: {order4:.1f} -> Fit: {fitness:.4f}"
            ),
        )
        return float(fitness)

    def _return_penalty_fitness(self, gdd, tod, fod, c_lambda=1030.0, filter_width=5.0, reason=''):
        fitness = 1e6
        self._update_fitness_indicators(gdd, tod, fod, c_lambda, filter_width, fitness, f"Penalty ({reason})")
        return float(fitness)

    def _update_fitness_indicators(self, gdd, tod, fod, c_lambda=1030.0, filter_width=5.0, fitness=1e6, log_msg=''):
        def _ui_update():
            self.gdd_indicator.config(
                text=f'Current GDD: {gdd: .2f}, TOD: {tod: .2f}, FOD: {fod: .2f}, Lambda: {c_lambda: .2f}, Bandwidth: {filter_width: .2f}'
            )
            self.fitness_indicator.config(text=f'Current fitness: {fitness: .4f}')
            self.talk(log_msg)
        self.root.after(0, _ui_update)

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

        # 1. Lewa oś (best_frog_ax): Najlepsze widmo + próg 3 dB
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
        else:
            self.best_frog_line.set_visible(False)
            self.best_treshold_line.set_visible(False)
            self.best_treshold_text.set_visible(False)
            self.best_frog_ax.get_yaxis().set_visible(False)

        # 2. Prawa oś (best_frog_ax2): Faza widmowa najlepszego impulsu (I > 0.1 * max)
        has_phase = (
                hasattr(self, "best_frog_phase_ydata")
                and len(self.best_frog_phase_ydata) == len(wavelengths)
        )
        if self.show_phase.get() and has_phase and len(intensities) > 0:
            phases = np.array(self.best_frog_phase_ydata, dtype=float)
            intensity_threshold = 0.1 * np.max(intensities)
            phases_masked = np.where(intensities > intensity_threshold, phases, np.nan)

            self.best_frog_line2.set_xdata(wavelengths)
            self.best_frog_line2.set_ydata(phases_masked)
            self.best_frog_line2.set_visible(True)
            self.best_frog_ax2.set_xlim(xmin, xmax)

            p_filtered = phases_masked[mask]
            if np.any(~np.isnan(p_filtered)):
                self.best_frog_ax2.set_ylim(np.nanmin(p_filtered) - 0.5, np.nanmax(p_filtered) + 0.5)
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