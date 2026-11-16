import threading
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from waveshaper import WaveShaper, attenuation_filter, thz_to_nm, polynomial_phase, scale_0_1_to_limit
import cs
import os, json
from pathlib import Path
from datetime import datetime


def _json_converter(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")

class BaseGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GMN Control Panel")
        self.root.state("zoomed")

        # tworzymy folder na pomiary
        self.base_folder = Path(__file__).parent
        self.data_folder = self.base_folder / "measurements"
        self.data_folder.mkdir(parents=True, exist_ok=True)

        self.feedback_connected = False
        self.feedback_continuous = False
        self.feedback_device = None
        self.feedback_device_name = None

        self.shaper_connected = False
        self.shaper = None

        self.stop_event = threading.Event()  # Event do zatrzymywania optymalizacji
        self.fitness = None

        # Layout
        #self.main_frame = ttk.Frame(root)
        #self.main_frame.pack(fill='both', expand=True)

        # Layout z suwakami
        outer_frame = ttk.Frame(self.root)
        outer_frame.pack(fill="both", expand=True)

        v_scroll = ttk.Scrollbar(outer_frame, orient="vertical")
        v_scroll.pack(side="right", fill="y")

        h_scroll = ttk.Scrollbar(outer_frame, orient="horizontal")
        h_scroll.pack(side="bottom", fill="x")

        self.main_canvas = tk.Canvas(
            outer_frame,
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
            highlightthickness=0,
        )
        self.main_canvas.pack(side="left", fill="both", expand=True)

        v_scroll.config(command=self.main_canvas.yview)
        h_scroll.config(command=self.main_canvas.xview)

        self.main_frame = ttk.Frame(self.main_canvas)
        self.main_canvas.create_window((0, 0), window=self.main_frame, anchor="nw")

        self.main_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")),
        )

        self.main_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.main_canvas.yview_scroll(int(-1*(e.delta/120)), "units"),
        )

        self.main_canvas.bind_all(
            "<Shift-MouseWheel>",
            lambda e: self.main_canvas.xview_scroll(int(-1*(e.delta/120)), "units"),
        )

        self.left_frame = ttk.Frame(self.main_frame)
        self.left_frame.pack(side='left', fill='both', expand=True)

        self.right_frame = ttk.Frame(self.main_frame, padding=10)
        self.right_frame.pack(side='right', fill='y')

        style = ttk.Style()
        bold_font = tk.font.Font(family="Helvetica", size=12, weight="bold")
        style.configure("Bold.TLabel", font=bold_font)
        style.configure("Red.TButton", foreground="red")
        style.configure("Green.TButton", foreground="green")
        style.configure("Black.TButton", foreground="black")

        self.setup_feedback_plot()
        self.setup_waveshaper_plot()
        self.setup_fitness_plot()
        self.setup_best_feedback_plot()
        # self.setup_connection_panel()
        self.setup_feedback_panel()
        self.setup_waveshaper_panel()
        self.setup_optimization_panel()
        # self.setup_save_panel()
        self.setup_term_panel()

        self.connect_to_waveshaper()
        self.connect_to_feedback()

    def get_figure_size(self):
        #Oblicza rozmiar figury Matplotlib proporcjonalnie do rozdzielczości ekranu.
        screen_h = self.root.winfo_screenheight()
        fig_w = max(5.5, min(8.5, (screen_h * 0.36) / 100))
        fig_h = max(3.8, min(5.5, (screen_h * 0.34) / 100))
        return (fig_w, fig_h)

    def setup_feedback_plot(self):
        raise NotImplementedError

    def setup_waveshaper_plot(self):
        self.waveshaper_figure = Figure(figsize=(5, 4), dpi=100, tight_layout=True)
        self.phase_ax = self.waveshaper_figure.add_subplot(111)
        self.phase_ax.set_title("Waveshaper filters")
        self.phase_ax.set_xlabel("Wavelength (nm)")
        self.phase_ax.set_ylabel(r"Phase [Rad]")
        self.phase_ax.invert_xaxis()

        self.phase_line, = self.phase_ax.plot([], [], color="darkviolet")
        self.phase_ax.grid(True, color="darkviolet", alpha=0.3)

        self.attenuation_ax = self.phase_ax.twinx()
        self.attenuation_ax.set_ylabel("Attenuation [dB]")
        self.attenuation_line, = self.attenuation_ax.plot([], [], color="hotpink")
        self.attenuation_ax.grid(True, color="hotpink", alpha=0.3)

        self.waveshaper_canvas = FigureCanvasTkAgg(self.waveshaper_figure, master=self.left_frame)
        self.waveshaper_canvas.draw()
        self.waveshaper_canvas.get_tk_widget().grid(row=1, column=0)

    def setup_fitness_plot(self):
        # iter = self.iterations_entry.get()
        self.fitness_figure = Figure(figsize=(5, 4), dpi=100, tight_layout=True)
        self.fitness_ax = self.fitness_figure.add_subplot(111)
        self.fitness_ax.set_title("Cost function")
        self.fitness_ax.set_xlabel("Iterations")
        self.fitness_ax.set_ylabel(r"Cost")

        self.fitness_line, = self.fitness_ax.plot([], [], color="darkviolet", marker="o")
        self.fitness_ax.grid()

        self.fitness_canvas = FigureCanvasTkAgg(self.fitness_figure, master=self.left_frame)
        self.fitness_canvas.draw()
        self.fitness_canvas.get_tk_widget().grid(row=1, column=1)

    def setup_best_feedback_plot(self):
        raise NotImplementedError

    def setup_connection_panel(self):
        conn_frame = ttk.LabelFrame(self.right_frame, text="Connection")
        conn_frame.pack(fill='x', pady=5)

        self.qmini_connect_button = ttk.Button(conn_frame, text="Qmini Connect", command=self.connect_to_qmini)
        self.qmini_connect_button.grid(row=2, column=0, columnspan=2, pady=5)

        self.shaper_connect_button = ttk.Button(conn_frame, text="Waveshaper Connect",
                                                command=self.connect_to_waveshaper)
        self.shaper_connect_button.grid(row=3, column=0, columnspan=2, pady=5)

    def setup_feedback_panel(self):
        raise NotImplementedError

    def setup_waveshaper_panel(self):
        control_frame = ttk.LabelFrame(self.right_frame, text="Waveshaper")
        control_frame.pack(fill='x', pady=5)

        ttk.Label(control_frame, text="Central wavelength:").grid(row=0, column=0, sticky='w')
        self.central_lambda_entry = ttk.Entry(control_frame, width=10)
        self.central_lambda_entry.insert(0, 1540)
        self.central_lambda_entry.grid(row=0, column=1)

        ttk.Label(control_frame, text="Attenuation filter:").grid(row=1, column=0, sticky="w")
        self.filter_shape = tk.StringVar()
        self.filter_dropdown = ttk.Combobox(
            control_frame,
            textvariable=self.filter_shape,
            values=["Gaussian", "Sech2"],
            state="readonly",
            width=10,
        )
        self.filter_shape.set("Gaussian")
        self.filter_dropdown.grid(row=1, column=1, sticky='w')

        ttk.Label(control_frame, text="Attenuation filter bw [nm]:").grid(row=2, column=0, sticky='w')
        self.atten_filter_bandwidth_entry = ttk.Entry(control_frame, width=10)
        self.atten_filter_bandwidth_entry.insert(0, 7)
        self.atten_filter_bandwidth_entry.grid(row=2, column=1)

        ttk.Label(control_frame, text="GDD:").grid(row=3, column=0, sticky='w')
        self.gdd_entry = ttk.Entry(control_frame, width=10)
        self.gdd_entry.insert(0, 0)
        self.gdd_entry.grid(row=3, column=1)

        ttk.Label(control_frame, text="TOD:").grid(row=3, column=2, sticky='w')
        self.tod_entry = ttk.Entry(control_frame, width=10)
        self.tod_entry.insert(0, 0)
        self.tod_entry.grid(row=3, column=3)

        ttk.Label(control_frame, text="FOD:").grid(row=4, column=0, sticky='w')
        self.fod_entry = ttk.Entry(control_frame, width=10)
        self.fod_entry.insert(0, 0)
        self.fod_entry.grid(row=4, column=1)

        ttk.Label(control_frame, text="Phase central wavelength:").grid(row=5, column=0, sticky='w')
        self.phase_central_lambda_entry = ttk.Entry(control_frame, width=10)
        self.phase_central_lambda_entry.insert(0, 1540)
        self.phase_central_lambda_entry.grid(row=5, column=1)

        self.set_gdd_button = ttk.Button(control_frame, text="Set", command=self.set_manual_gdd)
        self.set_gdd_button.grid(row=6, column=0, columnspan=2, pady=5)

    def setup_optimization_panel(self):
        optim_frame = ttk.LabelFrame(self.right_frame, text="Optimization")
        optim_frame.pack(fill='x', pady=5)

        ttk.Label(optim_frame, text="Algorithm:").grid(row=0, column=0, sticky='w')
        self.optim_algorithm = tk.StringVar()
        self.optim_dropdown = ttk.Combobox(
            optim_frame,
            textvariable=self.optim_algorithm,
            values=["Crow Search"],
            state="readonly",
            width=20,
        )
        self.optim_algorithm.set("Crow Search")
        self.optim_dropdown.grid(row=0, column=1, sticky='w')  # pack(padx=10, pady=10)

        self.time_indicator = tk.Label(optim_frame, text="Estimated time of optimization: ")
        self.time_indicator.grid(row=10, column=0, columnspan=4)

        self.iterations_var = tk.StringVar(value="20")
        self.population_var = tk.StringVar(value="150")
        self.delay_var = tk.StringVar(value="3000")

        self.iterations_var.trace_add("write", self.time_estimation_change)
        ttk.Label(optim_frame, text="Number of iterations:").grid(row=1, column=0, sticky='w')
        self.iterations_entry = ttk.Entry(optim_frame, textvariable=self.iterations_var, width=10)
        # self.iterations_entry.insert(0, 20)
        self.iterations_entry.grid(row=1, column=1)

        self.population_var.trace_add("write", self.time_estimation_change)
        ttk.Label(optim_frame, text="Population size:").grid(row=2, column=0, sticky='w')
        self.population_entry = ttk.Entry(optim_frame, textvariable=self.population_var, width=10)
        # self.population_entry.insert(0, 150)
        self.population_entry.grid(row=2, column=1)

        ttk.Label(optim_frame, text="Min GDD:").grid(row=4, column=0, sticky='w')
        self.min_gdd_entry = ttk.Entry(optim_frame, width=10)
        self.min_gdd_entry.insert(0, '-1')
        self.min_gdd_entry.grid(row=4, column=1)

        ttk.Label(optim_frame, text="Max GDD:").grid(row=4, column=2, sticky='w')
        self.max_gdd_entry = ttk.Entry(optim_frame, width=10)
        self.max_gdd_entry.insert(0, 1)
        self.max_gdd_entry.grid(row=4, column=3)

        ttk.Label(optim_frame, text="Min TOD:").grid(row=5, column=0, sticky='w')
        self.min_tod_entry = ttk.Entry(optim_frame, width=10)
        self.min_tod_entry.insert(0, '-1')
        self.min_tod_entry.grid(row=5, column=1)

        ttk.Label(optim_frame, text="Max TOD:").grid(row=5, column=2, sticky='w')
        self.max_tod_entry = ttk.Entry(optim_frame, width=10)
        self.max_tod_entry.insert(0, 1)
        self.max_tod_entry.grid(row=5, column=3)

        ttk.Label(optim_frame, text="Min FOD:").grid(row=6, column=0, sticky='w')
        self.min_fod_entry = ttk.Entry(optim_frame, width=10)
        self.min_fod_entry.insert(0, '-1')
        self.min_fod_entry.grid(row=6, column=1)

        ttk.Label(optim_frame, text="Max FOD:").grid(row=6, column=2, sticky='w')
        self.max_fod_entry = ttk.Entry(optim_frame, width=10)
        self.max_fod_entry.insert(0, 1)
        self.max_fod_entry.grid(row=6, column=3)

        ttk.Label(optim_frame, text="Min lambda:").grid(row=7, column=0, sticky='w')
        self.min_central_lambda_entry = ttk.Entry(optim_frame, width=10)
        self.min_central_lambda_entry.insert(0, 1530)
        self.min_central_lambda_entry.grid(row=7, column=1)

        ttk.Label(optim_frame, text="Max lambda:").grid(row=7, column=2, sticky='w')
        self.max_central_lambda_entry = ttk.Entry(optim_frame, width=10)
        self.max_central_lambda_entry.insert(0, 1590)
        self.max_central_lambda_entry.grid(row=7, column=3)

        ttk.Label(optim_frame, text="Min filter width:").grid(row=8, column=0, sticky='w')
        self.min_filter_width_entry = ttk.Entry(optim_frame, width=10)
        self.min_filter_width_entry.insert(0, 6)
        self.min_filter_width_entry.grid(row=8, column=1)

        ttk.Label(optim_frame, text="Max filter width:").grid(row=8, column=2, sticky='w')
        self.max_filter_width_entry = ttk.Entry(optim_frame, width=10)
        self.max_filter_width_entry.insert(0, 10)
        self.max_filter_width_entry.grid(row=8, column=3)

        ttk.Label(optim_frame, text="Inside factor:").grid(row=9, column=0, sticky='w')
        self.inside_weight_entry = ttk.Entry(optim_frame, width=10)
        self.inside_weight_entry.insert(0, 1)
        self.inside_weight_entry.grid(row=9, column=1)
        ttk.Label(optim_frame, text="Outside factor:").grid(row=9, column=2, sticky='w')
        self.outside_weight_entry = ttk.Entry(optim_frame, width=10)
        self.outside_weight_entry.insert(0, 1)
        self.outside_weight_entry.grid(row=9, column=3)

        self.optimize_button = ttk.Button(optim_frame, text="Start", command=self.start_optimization)
        self.optimize_button.grid(row=11, column=0, columnspan=1, pady=0)

        self.stop_optimization_button = ttk.Button(optim_frame, text="STOP", command=self.stop_optimization)
        self.stop_optimization_button.grid(row=11, column=1, columnspan=1, pady=0)

        self.iter_indicator = tk.Label(optim_frame, text="Iteration: --")
        self.iter_indicator.grid(row=12, column=0)

        self.agent_indicator = tk.Label(optim_frame, text="Agent: --")
        self.agent_indicator.grid(row=13, column=0)

        self.gdd_indicator = tk.Label(optim_frame, text="Current GDD: --, TOD: --, FOD: --, Lambda: --, Bandwidth: --")
        self.gdd_indicator.grid(row=14, column=0, columnspan=4)

        self.fitness_indicator = tk.Label(optim_frame, text="Current fitness: --")
        self.fitness_indicator.grid(row=15, column=0)

    def setup_save_panel(self):
        save_frame = ttk.LabelFrame(self.right_frame, text="Save")
        save_frame.pack(fill='x', pady=5)

        self.save_button = ttk.Button(save_frame, text="Save", command=self.save_data)
        self.save_button.grid(row=10, column=0, columnspan=1, pady=0)

    def setup_term_panel(self):
        self.terminal_frame = ttk.Frame(self.right_frame)
        self.terminal_frame.pack(fill='x', pady=5)
        self.term_label = ttk.Label(self.terminal_frame,
                                    text="🤖: Hi! I will keep you updated!",
                                    wraplength=250,  # pixels
                                    justify="left",
                                    anchor="w")
        self.term_label.grid(row=0, column=0, columnspan=4)

    def talk(self, text):
        text_out = text
        if type(text) != type("string"):
            text_out = str(text)
        self.term_label.configure(text="🤖: " + text_out)

    def connect_to_feedback(self):
        raise NotImplementedError

    def update_feedback_plot(self, x, y):
        raise NotImplementedError

    def start_continuous_read(self):
        '''wywołane przy kliknięciu checkbutton'''
        raise NotImplementedError

    def show_feedback_plot(self):
        raise NotImplementedError

    def connect_to_waveshaper(self):
        if not self.shaper_connected:
            try:
                self.shaper = WaveShaper()
                # self.shaper_connect_button.configure(text = "Shaper Connected", style = "Green.TButton")
                self.talk("You connected to Waveshaper")
                self.shaper_connected = True
            except:
                # self.shaper_connect_button.configure(text = "Shaper Error", style = "Red.TButton")
                self.talk("Error when connecting to Waveshaper")
        else:
            # Waveshaper_close_connection(self.q)
            self.shaper_connected = False
            self.shaper = None
            # self.shaper_connect_button.configure(text="Shaper Connect", style="Black.TButton")
            self.talk("You disconnected from Waveshaper")

    def set_gdd_tod_fod(self, gdd, tod, fod, central_lambda, filter_width=4, update_plot=True):

        # self.phase_xdata, self.phase_ydata = parabolic_phase(self.shaper, float(self.central_lambda_entry.get()), gdd)
        # self.phase_xdata, self.phase_ydata = polynomial_phase(self.shaper, float(self.central_lambda_entry.get()), gdd, tod, fod)

        self.phase_xdata, self.phase_ydata = polynomial_phase(self.shaper, central_lambda, gdd,
                                                              tod, fod)
        attenuation_central_lambda = float(self.central_lambda_entry.get())
        self.attenuation_xdata, self.attenuation_ydata, phases = attenuation_filter(self.shaper,
                                                                                    type=self.filter_shape.get(),
                                                                                    lambda_center=attenuation_central_lambda,
                                                                                    bandwidth_nm=filter_width,
                                                                                    phase=self.phase_ydata,
                                                                                    num_points=1000)

        r = self.shaper.write(freq=self.attenuation_xdata, intens=self.attenuation_ydata, phase=phases)
        if r["rc"]:
            self.talk(f'Waveshaper error: {r["msg"]}')
        else:
            if update_plot:
                self.root.after(0, self.show_waveshaper_plot)

        return r

    def set_manual_gdd(self):
        gdd = float(self.gdd_entry.get())
        tod = float(self.tod_entry.get())
        fod = float(self.fod_entry.get())
        c_lambda = float(self.phase_central_lambda_entry.get())
        filter_width = float(self.atten_filter_bandwidth_entry.get())
        self.set_gdd_tod_fod(gdd, tod, fod, c_lambda, filter_width)

    def show_waveshaper_plot(self):
        xdata = [thz_to_nm(x) for x in self.phase_xdata]
        ydata = self.phase_ydata
        self.phase_line.set_xdata(xdata)
        self.phase_line.set_ydata(ydata)
        xmin = 1530  # nm
        xmax = 1549.5  # nm
        self.phase_ax.set_xlim(xmin, xmax)

        xdata = np.array(xdata)
        ydata = np.array(ydata)
        mask = (xdata >= xmin) & (xdata <= xmax)
        y_in_range = ydata[mask]
        #margin = 0.1 * (y_in_range.max() - y_in_range.min())
        #self.phase_ax.set_ylim(y_in_range.min() - margin, y_in_range.max() + margin)
        self.phase_ax.set_ylim(-40, 40)

        self.attenuation_line.set_xdata([thz_to_nm(x) for x in self.attenuation_xdata])
        self.attenuation_line.set_ydata(self.attenuation_ydata)
        # self.attenuation_ax.set_xlim(thz_to_nm(max(self.attenuation_xdata)), thz_to_nm(min(self.attenuation_xdata)))
        self.attenuation_ax.set_xlim(xmin, xmax)
        self.attenuation_ax.set_ylim(0, 1.1 * np.max(self.attenuation_ydata))

        self.waveshaper_canvas.draw()

    def time_estimation_change(self, *args):
        # zabezpieczenie: jak pole jest puste
        try:
            pop = int(self.population_var.get())
            it = int(self.iterations_var.get())
            delay = 3000
        except ValueError:
            self.time_indicator.config(text="Estimated time of optimization: --")
            return
        estimated_time_ms = pop * it * delay
        seconds = estimated_time_ms // 1000
        minutes = seconds // 60
        hours = minutes // 60
        seconds = seconds % 60
        minutes = minutes % 60
        self.time_indicator.config(text=f"Estimated time of optimization: "
                                        f"{hours} hours {minutes} minutes {seconds} seconds")

    def prepare_for_optimization(self):
        raise NotImplementedError

    def prepare_after_optimization(self):
        raise NotImplementedError

    def start_optimization(self):
        self.prepare_for_optimization()

        self.stop_event.clear()  # reset flagi przed startem
        t = threading.Thread(target=self.optimize_background, daemon=True)
        t.start()

    def stop_optimization(self):
        self.stop_event.set()  # sygnał do zatrzymania wątku

    def optimize_background(self):
        try:
            match self.optim_algorithm.get():
                case "Crow Search":
                    self.crow_search()
                case _:
                    pass
        finally:
            self.prepare_after_optimization()


    def objective_gdd_tod_fod(self, gdd, tod, fod, c_lambda, filter_width):
        '''
        Calculates fitness of a pulse with given GDD value
        :return:
        '''
        raise NotImplementedError

    def show_fitness_plot(self):
        iter = int(self.iterations_entry.get())
        self.fitness_line.set_xdata(np.arange(len(self.fitness_list)))
        self.fitness_line.set_ydata(self.fitness_list)
        self.fitness_ax.set_ylim(np.min(self.fitness_list), np.max(self.fitness_list))
        # self.fitness_ax.set_ylim(-300, 0)
        self.fitness_ax.set_xlim(0, iter)
        self.fitness_canvas.draw()

    def show_best_feedback_plot(self):
        raise NotImplementedError

    def update_best_feedback_plot(self, gdd, tod, fod, central_lambda, filter_width):
        raise NotImplementedError

    def formulate_data_for_saving(self, best_gdd, best_tod, best_fod, best_lambda_c, best_filter_width, best_fitness):
        raise NotImplementedError

    def crow_search(self):
        '''
        Crow search algorithm
        :param pd: problem dimension -> number of stripes
        :param N: Flock (population) size
        :param AP: Awareness probability
        :param fl: flight length
        :param iter: max number of iterations
        :param lb: lower bound
        :param ub: upper bound
        :return: fitness list, best mask
        '''

        # x - crows positions
        # mem - memory storing the hiding-food locations
        # ft - fitness array, stores the fitness of the hiding-food locations
        # ft_mem - memory storing fitness values of the positions in memory
        iter = int(self.iterations_entry.get())
        pop_size = int(self.population_entry.get())
        prob_dim = 5  # because we have only GDD, TOD and FOD and lambda and filter bandwidth
        lb = 0
        ub = 1
        AP = 0.3
        fl = 0.5

        x = cs.init(pop_size, prob_dim, lb, ub)  # initial population
        self.fitness_list = []  # fitness list
        # ft = (objective(pulseCheck, scan_range, v, pd) for v in x)
        ft = []
        for idx, position in enumerate(x):
            # warunek zatrzymania
            if self.stop_event.is_set():
                self.talk(f'Optimization stopped')
                ft = []
                x = []
                return

            self.iter_indicator.config(text=f'Iteration: 0')
            self.agent_indicator.config(text=f'Crow: {idx}')
            fitness = self.objective_gdd_tod_fod(position[0], position[1], position[2], position[3],
                                                 position[4])
            ft.append(fitness)  # wypełnienie fitness

            self.gdd_indicator.config(
                text=f'Current GDD: {position[0]: .2f}, TOD: {position[1]: .2f}, FOD: {position[2]: .2f},'
                     f'Lambda: {position[3]: .2f}, Bandwidth: {position[4]: .2f}')
            self.fitness_indicator.config(text=f'Current fitness: {fitness: .2f}')


        # initialize the memory
        mem = np.copy(x)  # first hiding-food locations are
        fit_mem = np.copy(ft)  # first fitness memory

        min_fit = np.min(fit_mem)
        # print(f'The best fitness, iteration {i}: {min_fit}')
        min_fit_idx = np.argmin(fit_mem)
        self.fitness_list.append(min_fit)
        self.root.after(0, self.show_fitness_plot)

        gdd = scale_0_1_to_limit(mem[min_fit_idx][0], float(self.min_gdd_entry.get()), float(self.max_gdd_entry.get()))
        tod = scale_0_1_to_limit(mem[min_fit_idx][1], float(self.min_tod_entry.get()), float(self.max_tod_entry.get()))
        fod = scale_0_1_to_limit(mem[min_fit_idx][2], float(self.min_fod_entry.get()), float(self.max_fod_entry.get()))
        central_lambda = scale_0_1_to_limit(mem[min_fit_idx][3], float(self.min_central_lambda_entry.get()),
                                            float(self.max_central_lambda_entry.get()))
        filter_width = scale_0_1_to_limit(mem[min_fit_idx][4], float(self.min_filter_width_entry.get()),
                                          float(self.max_filter_width_entry.get()))

        self.update_best_feedback_plot(gdd, tod, fod, central_lambda, filter_width)

        for i in range(iter):
            # num = np.random.randint(low=0, high=N, size = N) #Generation of random candidate crows for following (chasing)
            # xnew = np.zeros((N, pd))

            # warunek zatrzymania
            if self.stop_event.is_set():
                self.talk(f'Optimization stopped')
                ft = []
                x = []
                return

            best_fitness = self.fitness_list[-1]

            # for crow_idx in range(x.shape[0]-1):
            for crow_i in range(pop_size):
                # Pick a crow to follow
                crow_j = np.random.randint(low=0,
                                           high=pop_size)  # Generation of random candidate crows for following (chasing)
                rand_num = np.random.rand()  # Generate a random number between 0 and 1 for awareness probability
                if rand_num > AP:
                    # crow i chases crow j
                    # xnew[crow_idx, :] = x[crow_idx, :] + fl*rand_num*(mem[num[crow_idx], :]-x[crow_idx, :]) # Generation of a new position for crow i (state 1)
                    # xnew[crow_i, :] = x[crow_i, :] + fl * rand_num * (mem[num[crow_i], :] - x[crow_i, :])  # Generation of a new position for crow i (state 1)
                    x[crow_i, :] = x[crow_i, :] + fl * rand_num * (
                            mem[crow_j, :] - x[crow_i, :])  # Generation of a new position for crow i (state 1)
                    # tu powinno być chyba sprawdzenie czy maska jest w bounds?
                else:
                    # crow j is aware, goes to random position
                    x[crow_i, :] = np.random.randint(lb, ub, prob_dim)

            # xn = xnew
            # ft = (objective(pulseCheck, scan_range, v, pd) for v in xn)  # Function for fitness evaluation of new solutions
            ft = []  # fitness values placeholder
            for idx, position in enumerate(x):
                # warunek zatrzymania
                if self.stop_event.is_set():
                    self.talk(f'Optimization stopped')
                    ft = []
                    x = []
                    return

                # ft.append(objective(q, waveshaper, position, pd)) #check the fitness
                # self.talk(f'Iteration {i} crow {idx}')
                self.iter_indicator.config(text=f'Iteration: {i + 1}')  # +1 bo iteracją 0 są losowe maski
                self.agent_indicator.config(text=f'Crow: {idx}')

                fitness = self.objective_gdd_tod_fod(position[0], position[1], position[2], position[3], position[4])
                ft.append(fitness)

                self.gdd_indicator.config(
                    text=f'Current GDD: {position[0]: .2f}, TOD: {position[1]: .2f}, FOD: {position[2]: .2f},'
                         f'Lambda: {position[3]: .2f}, Bandwidth: {position[4]: .2f}')
                self.fitness_indicator.config(text=f'Current fitness: {fitness: .2f}')


            for crow in range(pop_size):  # Update position and memory
                if np.all(x[crow, :] >= lb) and np.all(x[crow, :] <= ub):  # Check if within bounds
                    # x[j, :] = xnew[j,:] #xnew[i, :]    # Update position
                    new_place = ft[crow]
                    best_spot = fit_mem[crow]
                    # if ft[crow] < fit_mem[crow]:
                    if new_place < best_spot:
                        mem[crow, :] = x[crow, :]
                        fit_mem[crow] = ft[crow]
                else:
                    print(f'not within bounds')

            min_fit = np.min(fit_mem)
            min_fit_idx = np.argmin(fit_mem)
            self.fitness_list.append(min_fit)
            self.root.after(0, self.show_fitness_plot)

            if min_fit < best_fitness:
                gdd = scale_0_1_to_limit(mem[min_fit_idx][0], float(self.min_gdd_entry.get()),
                                         float(self.max_gdd_entry.get()))
                tod = scale_0_1_to_limit(mem[min_fit_idx][1], float(self.min_tod_entry.get()),
                                         float(self.max_tod_entry.get()))
                fod = scale_0_1_to_limit(mem[min_fit_idx][2], float(self.min_fod_entry.get()),
                                         float(self.max_fod_entry.get()))
                lambda_c = scale_0_1_to_limit(mem[min_fit_idx][3], float(self.min_central_lambda_entry.get()),
                                              float(self.max_central_lambda_entry.get()))
                filter_width = scale_0_1_to_limit(mem[min_fit_idx][4], float(self.min_filter_width_entry.get()),
                                                  float(self.max_filter_width_entry.get()))

                self.update_best_feedback_plot(gdd, tod, fod, lambda_c, filter_width)

        global_best = np.min(fit_mem)
        print(f'The best fitness, overall: {global_best: .2f}')

        # g_best = mem[ngbest[0], :]  # global best position (mask)
        min_fit_idx = np.argmin(fit_mem)
        global_best_position = mem[min_fit_idx]
        best_gdd = scale_0_1_to_limit(global_best_position[0], float(self.min_gdd_entry.get()),
                                      float(self.max_gdd_entry.get()))
        best_tod = scale_0_1_to_limit(global_best_position[1], float(self.min_tod_entry.get()),
                                      float(self.max_tod_entry.get()))
        best_fod = scale_0_1_to_limit(global_best_position[2], float(self.min_fod_entry.get()),
                                      float(self.max_fod_entry.get()))
        best_lambda_c = scale_0_1_to_limit(global_best_position[3], float(self.min_central_lambda_entry.get()),
                                           float(self.max_central_lambda_entry.get()))
        best_filter_width = scale_0_1_to_limit(global_best_position[4], float(self.min_filter_width_entry.get()),
                                               float(self.max_filter_width_entry.get()))
        print(
            f'Best GDD: {best_gdd}, Best TOD: {best_tod}, Best FOD: {best_fod}, Central lambda: {best_lambda_c}, Best filter width: {best_filter_width}')
        self.talk(
            f'The best fitness, overall: {global_best: .2f}, for GDD: {best_gdd}, TOD: {best_tod}, FOD: {best_fod},'
            f' lambda: {best_lambda_c}, filter_width: {best_filter_width}')
        # print(f'Fitness measured rn with the best mask: {objective(q, waveshaper, mem[min_fit_idx], pd)}')

        fitness = self.objective_gdd_tod_fod(global_best_position[0], global_best_position[1], global_best_position[2],
                                             global_best_position[3], global_best_position[4])
        self.gdd_indicator.config(
            text=f'Current GDD: {position[0]: .2f}, TOD: {position[1]: .2f}, FOD: {position[2]: .2f},'
                 f'Lambda: {position[3]: .2f}, Bandwidth: {position[4]: .2f}')
        self.fitness_indicator.config(text=f'Current fitness: {fitness: .2f}')

        print(f'Fitness measured rn with the best mask so far: {fitness: .2f}')

        self.update_best_feedback_plot(best_gdd, best_tod, best_fod, best_lambda_c, best_filter_width)

        results = self.formulate_data_for_saving(best_gdd, best_tod, best_fod, best_lambda_c, best_filter_width,
                                                 global_best)
        self.save_data(results, self.feedback_device_name)

        return [global_best_position, global_best, self.fitness_list]

    def save_data(self, data, device):
        # zapisuje dict z danymi do pliku json
        if not isinstance(data, dict):
            raise TypeError(f'Argument data must be a dict, got {type(data).__name__}')

        # saves data to a json file in chosen directory
        result = data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.data_folder, f'measurement_{timestamp}_{device}.json')
        with open(filename, 'w') as f:
            json.dump(result, f, indent=4, default=_json_converter)
