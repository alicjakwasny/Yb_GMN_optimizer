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

class frogGUI(BaseGUI):
    def setup_feedback_plot(self):
        self.frog_figure = Figure(figsize=(5, 4), dpi=100, tight_layout = True)
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
        self.best_frog_figure = Figure(figsize=(5, 4), dpi=100, tight_layout=True)
        self.best_frog_ax = self.best_frog_figure.add_subplot(111)
        self.best_frog_ax.set_title("Frog")
        self.best_frog_ax.set_xlabel("Wavelength (nm)")
        self.best_frog_ax.set_ylabel(r"Intensity")
        self.best_frog_line, = self.best_frog_ax.plot([], [], color="darkviolet")
        self.best_frog_ax.grid(True, color="darkviolet", alpha=0.3)

        self.best_frog_ax2 = self.best_frog_ax.twinx()
        self.best_frog_ax2.set_ylabel("Spectral phase")
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

        self.scale_log = tk.BooleanVar(value=True)
        #self.frog_scale_log = ttk.Checkbutton(read_frame, text="Logarythmic scale", variable=self.scale_log)
        #self.frog_scale_log.grid(row=2, column=1)

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
        '''
        acquired_data, retrieved_data = self.frog_dev.get_frog_data()
        return acquired_data, retrieved_data
        '''
        # Pobieranie danych w sposób synchroniczny dla interfejsu Tkinter
        loop = asyncio.get_event_loop()
        acquired_data, retrieved_data = loop.run_until_complete(
            self.frog_dev.get_frog_data()
        )

        '''
        # --- TYMCAZASOWY TEST ---
        print("ACQUIRED:", type(acquired_data),
              acquired_data.keys() if isinstance(acquired_data, dict) else acquired_data)
        print("RETRIEVED:", type(retrieved_data),
              retrieved_data.keys() if isinstance(retrieved_data, dict) else retrieved_data)
        if isinstance(retrieved_data, dict) and "dataSeries" in retrieved_data:
            print("RETRIEVED dataSeries keys:", retrieved_data["dataSeries"].keys())
        return acquired_data, retrieved_data
        # ------------------------
        '''

        # Wyciągamy punkty widma do zmiennych używanych przez wykres GUI
        if retrieved_data and "dataSeries" in retrieved_data:
            ds = retrieved_data["dataSeries"]
            print("Klucze w retrieved dataSeries:", list(ds.keys()))  # jednorazowy podgląd nazw kluczy

            # ----- TESTY ------
            print("retrievedSpectrum:", type(ds.get("retrievedSpectrum")),
                  ds.get("retrievedSpectrum", {}).keys() if isinstance(ds.get("retrievedSpectrum"), dict) else ds.get(
                      "retrievedSpectrum"))
            print("spectralProfileMod:", type(ds.get("spectralProfileMod")),
                  ds.get("spectralProfileMod", {}).keys() if isinstance(ds.get("spectralProfileMod"), dict) else ds.get(
                      "spectralProfileMod"))
            print("spectralProfilePhase:", type(ds.get("spectralProfilePhase")),
                  ds.get("spectralProfilePhase", {}).keys() if isinstance(ds.get("spectralProfilePhase"),
                                                                          dict) else ds.get("spectralProfilePhase"))


            spectrum = ds.get("spectralProfileMod", {})
            phase = ds.get("spectralProfilePhase", {})

            self.frog_xdata = spectrum.get("xValues", [])
            self.frog_ydata = spectrum.get("yValues", [])
            self.frog_phase_ydata = phase.get("yValues", [])

            if len(self.frog_xdata) > 0:
                print(
                    f"Jednostka X: {spectrum.get('xUnit')}, zakres: {np.min(self.frog_xdata)} .. {np.max(self.frog_xdata)}")

            # --- DO DIAGNOSTYKI ---
            if len(self.frog_xdata) > 0:
                x_min = np.min(self.frog_xdata)
                x_max = np.max(self.frog_xdata)
                print(f"[DIAGNOSTYKA FROG] Długość tablicy: {len(self.frog_xdata)}")
                print(f"[DIAGNOSTYKA FROG] Wartości x: min={x_min:.4e}, max={x_max:.4e}")
                print(f"[DIAGNOSTYKA FROG] Pierwsze 3 próbki: {self.frog_xdata[:3]}")
            else:
                print("[DIAGNOSTYKA FROG] Tablica self.frog_xdata jest PUSTA!")
            # ----------------------------------------

        if update_plot:
            self.show_feedback_plot()

        return acquired_data, retrieved_data

    def frog_read_measurement(self, feedback_device):
        loop = asyncio.get_event_loop()
        acquired_data, retrieved_data = loop.run_until_complete(
            self.feedback_device.get_frog_data()
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
            x, y = self.frog_read_measurement(self.feedback_device)

            self.root.after(0, self.update_feedback_plot, x, y)
            time.sleep(delay)

    def update_feedback_plot(self, x, y):
        self.frog_xdata = x
        self.frog_ydata = y
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
            self.talk("Stopped continuous Qmini measurement")
        pass

    def show_feedback_plot(self):
        xmin = float(self.lambda_min_entry.get())
        xmax = float(self.lambda_max_entry.get())

        if self.scale_lin.get():
            self.frog_line.set_xdata(self.frog_xdata)
            self.frog_line.set_ydata(self.frog_ydata)
            self.frog_line.set_visible(True)
            self.frog_ax.set_xlim(xmin, xmax)
            self.frog_ax.set_ylim(0, 1.1 * np.max(self.frog_ydata))

            self.frog_ax.get_yaxis().set_visible(True)
        else:
            self.frog_line.set_visible(False)
            self.frog_ax.get_yaxis().set_visible(False)

        if self.scale_log.get():
            self.frog_line2.set_xdata(self.frog_xdata)
            lin = np.array(self.frog_ydata, dtype=float)
            lin[lin <= 0] = 1e-20
            self.frog_ydata_log = 10 * np.log10(lin/1000)
            self.frog_line2.set_ydata(self.frog_ydata_log)

            self.frog_line2.set_visible(True)
            self.frog_line2.set_ydata(self.frog_ydata_log)

            self.frog_line2.set_visible(True)
            self.frog_ax2.set_xlim(xmin, xmax)

            self.frog_ax2.set_ylim(-20, 20)
            treshold_value = max(self.frog_ydata_log) - 9
            self.treshold_line.set_ydata([treshold_value, treshold_value])
            # aktualizacja napisu
            wavelengths = np.array(self.frog_xdata, dtype=float)
            intensities = np.array(self.frog_ydata_log, dtype=float)
            mask = (wavelengths >= xmin) & (wavelengths <= xmax)
            w_filtered = wavelengths[mask]
            i_filtered = intensities[mask]
            width = data.compute_width_db(w_filtered, i_filtered, level=9)
            self.treshold_text.set_y(treshold_value)

            self.treshold_text.set_text(f"3 dB: {width:.2f} nm")

            # prostokąt
            lambda_min = 782.5 #nm
            lambda_max = 837.5 #nm
            rectangle = ((w_filtered >= lambda_min) & (w_filtered <= lambda_max)).astype(float) # zrob prostokat
            I_min = -15 # minimum value of intensity
            I_max = np.max(i_filtered)
            if I_max < -5:
                I_max = I_min
            elif I_max < 4:
                I_max = 4
            rectangle_scaled = rectangle * (I_max - I_min) + I_min # wyskaluj prostokąt
            self.rectangle_line.set_xdata(w_filtered)
            self.rectangle_line.set_ydata(rectangle_scaled)

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
        xmin = float(self.lambda_min_entry.get())
        xmax = float(self.lambda_max_entry.get())

        self.best_spectrum_line.set_xdata(self.best_spectrum_xdata)
        self.best_spectrum_line.set_ydata(self.best_spectrum_ydata_lin)
        self.best_spectrum_line2.set_xdata(self.best_spectrum_xdata)
        lin = np.array(self.best_spectrum_ydata_lin, dtype=float)
        lin[lin <= 0] = 1e-20
        self.best_spectrum_ydata_log = 10*np.log10(lin/1000)
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
        self.read_frog()
        self.best_spectrum_xdata, self.best_spectrum_ydata_lin = self.frog_xdata, self.frog_ydata
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
    app = frogGUI(root)
    root.mainloop()