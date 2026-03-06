"""
============================================================
  Genetic Algorithm – Study Plan Optimizer  (Tkinter UI)
  Intelligent Student Performance Evaluation & Support System
============================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import copy
import random
import os

# ─────────────────────────────── constants ────────────────────────────────────

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_DEFAULTS = [6, 6, 6, 6, 5, 8, 8]
DIFF_MAP = {1: "Easy", 2: "Medium", 3: "Hard"}

# ─────────────────────────────── colour palette ───────────────────────────────

BG        = "#1e1e2e"
BG2       = "#2a2a3e"
BG3       = "#313149"
ACCENT    = "#7c6af7"
ACCENT2   = "#a78bfa"
FG        = "#e2e8f0"
FG_DIM    = "#94a3b8"
GREEN     = "#4ade80"
RED       = "#f87171"
YELLOW    = "#fbbf24"
CARD      = "#252538"

FONT_H    = ("Segoe UI", 13, "bold")
FONT_N    = ("Segoe UI", 10)
FONT_S    = ("Segoe UI", 9)
FONT_MONO = ("Consolas", 9)

# ─────────────────────────────── GA core ──────────────────────────────────────

def compute_targets(config):
    total_hours = sum(config["available_hours"])
    scores = [d * w for d, w in zip(config["difficulty"], config["exam_weight"])]
    total_score = sum(scores) or 1
    return [(s / total_score) * total_hours for s in scores]


def random_chromosome(config):
    n = len(config["subjects"])
    schedule = [[0.0] * 7 for _ in range(n)]
    for d in range(7):
        budget = config["available_hours"][d]
        slots = list(range(n))
        random.shuffle(slots)
        remaining = budget
        for i, subj in enumerate(slots):
            if i == len(slots) - 1:
                allotted = round(random.uniform(0, remaining) * 2) / 2
            else:
                allotted = round(random.uniform(0, remaining * 0.6) * 2) / 2
            schedule[subj][d] = allotted
            remaining -= allotted
            if remaining <= 0:
                break
    return schedule


def fitness(schedule, config, targets):
    n = len(config["subjects"])
    score = 0.0
    weekly_totals = [sum(schedule[i]) for i in range(n)]

    for i in range(n):
        score -= abs(weekly_totals[i] - targets[i]) * 2.0

    for d in range(7):
        overflow = max(0, sum(schedule[i][d] for i in range(n)) - config["available_hours"][d])
        score -= overflow * 5.0

    for i in range(n):
        if weekly_totals[i] == 0:
            score -= 10.0

    for i in range(n):
        if weekly_totals[i] >= targets[i]:
            score += config["exam_weight"][i] * config["difficulty"][i] * 0.5
            excess = weekly_totals[i] - targets[i]
            if excess > 0:
                score -= excess * 1.5

    return score


def tournament_select(population, fitnesses, k=3):
    contestants = random.sample(range(len(population)), k)
    best = max(contestants, key=lambda i: fitnesses[i])
    return copy.deepcopy(population[best])


def crossover(p1, p2):
    point = random.randint(1, 6)
    n = len(p1)
    c1 = [[p1[i][d] if d < point else p2[i][d] for d in range(7)] for i in range(n)]
    c2 = [[p2[i][d] if d < point else p1[i][d] for d in range(7)] for i in range(n)]
    return c1, c2


def mutate(schedule, config, mut_rate):
    n = len(config["subjects"])
    for d in range(7):
        if random.random() < mut_rate:
            budget = config["available_hours"][d]
            slots = list(range(n))
            random.shuffle(slots)
            remaining = budget
            for idx, subj in enumerate(slots):
                if idx == len(slots) - 1:
                    allotted = round(random.uniform(0, remaining) * 2) / 2
                else:
                    allotted = round(random.uniform(0, remaining * 0.7) * 2) / 2
                schedule[subj][d] = allotted
                remaining -= allotted
                if remaining <= 0:
                    for rest in slots[idx + 1:]:
                        schedule[rest][d] = 0
                    break
    return schedule


def run_ga(config, progress_cb=None):
    targets = compute_targets(config)
    population = [random_chromosome(config) for _ in range(config["pop_size"])]
    best_schedule, best_fitness_val = None, float("-inf")
    history = []
    stagnation, prev_best = 0, float("-inf")

    for gen in range(1, config["generations"] + 1):
        fitnesses = [fitness(ind, config, targets) for ind in population]
        best_idx = max(range(len(population)), key=lambda i: fitnesses[i])
        gen_best = fitnesses[best_idx]
        history.append(gen_best)

        if gen_best > best_fitness_val:
            best_fitness_val = gen_best
            best_schedule = copy.deepcopy(population[best_idx])

        if progress_cb:
            progress_cb(gen, config["generations"], best_fitness_val)

        if abs(gen_best - prev_best) < 1e-6:
            stagnation += 1
        else:
            stagnation = 0
        prev_best = gen_best
        if stagnation >= 50:
            if progress_cb:
                progress_cb(config["generations"], config["generations"], best_fitness_val)
            break

        sorted_pop = sorted(range(len(population)), key=lambda i: fitnesses[i], reverse=True)
        next_gen = [copy.deepcopy(population[sorted_pop[e]])
                    for e in range(min(config["elite_count"], len(population)))]
        while len(next_gen) < config["pop_size"]:
            p1 = tournament_select(population, fitnesses)
            p2 = tournament_select(population, fitnesses)
            c1, c2 = crossover(p1, p2)
            next_gen.extend([mutate(c1, config, config["mut_rate"]),
                             mutate(c2, config, config["mut_rate"])])
        population = next_gen[:config["pop_size"]]

    return best_schedule, best_fitness_val, history, targets


# ─────────────────────────────── Tkinter App ──────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GA Study Plan Optimizer")
        self.geometry("1000x720")
        self.minsize(900, 640)
        self.configure(bg=BG)
        self._apply_style()

        self.subjects = []       # list of dicts {name, diff, weight}
        self.result   = None     # {schedule, fitness, history, targets, config}

        self._build_ui()

    # ── Style ──────────────────────────────────────────────────────────────────
    def _apply_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG, font=FONT_N,
                    fieldbackground=BG2, bordercolor=BG3, relief="flat")
        s.configure("TFrame",       background=BG)
        s.configure("Card.TFrame",  background=CARD, relief="flat")
        s.configure("TLabel",       background=BG,   foreground=FG)
        s.configure("Dim.TLabel",   background=BG,   foreground=FG_DIM, font=FONT_S)
        s.configure("Card.TLabel",  background=CARD, foreground=FG)
        s.configure("Head.TLabel",  background=BG,   foreground=ACCENT2, font=FONT_H)
        s.configure("TEntry",       fieldbackground=BG2, foreground=FG,
                    insertcolor=FG, bordercolor=BG3, relief="flat")
        s.configure("TSpinbox",     fieldbackground=BG2, foreground=FG,
                    arrowcolor=ACCENT, bordercolor=BG3)
        s.configure("TCombobox",    fieldbackground=BG2, foreground=FG,
                    selectbackground=BG3, arrowcolor=ACCENT)
        s.map("TCombobox", fieldbackground=[("readonly", BG2)])
        s.configure("TNotebook",            background=BG, bordercolor=BG)
        s.configure("TNotebook.Tab",        background=BG3, foreground=FG_DIM,
                    padding=[14, 6])
        s.map("TNotebook.Tab",
              background=[("selected", ACCENT)],
              foreground=[("selected", "#fff")])
        s.configure("Treeview",     background=BG2, foreground=FG,
                    fieldbackground=BG2, rowheight=26, bordercolor=BG3)
        s.configure("Treeview.Heading", background=BG3, foreground=ACCENT2,
                    font=("Segoe UI", 9, "bold"), relief="flat")
        s.map("Treeview", background=[("selected", ACCENT)])
        s.configure("TProgressbar", troughcolor=BG3, background=ACCENT,
                    bordercolor=BG3, lightcolor=ACCENT, darkcolor=ACCENT)
        s.configure("TScrollbar",   background=BG3, troughcolor=BG,
                    arrowcolor=FG_DIM, bordercolor=BG)

    # ── Build main layout ─────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Title bar ─────────────────────────────────────────────────────────
        title_bar = tk.Frame(self, bg=BG3, height=52)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text="  GA Study Plan Optimizer",
                 bg=BG3, fg=ACCENT2, font=("Segoe UI", 14, "bold")).pack(side="left", padx=10, pady=10)
        tk.Label(title_bar, text="Intelligent Student Performance & Support System",
                 bg=BG3, fg=FG_DIM, font=FONT_S).pack(side="left", padx=4, pady=10)

        # ── Notebook tabs ─────────────────────────────────────────────────────
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=10)

        self.tab_setup   = ttk.Frame(self.nb)
        self.tab_ga      = ttk.Frame(self.nb)
        self.tab_results = ttk.Frame(self.nb)

        self.nb.add(self.tab_setup,   text="  ① Subjects & Hours  ")
        self.nb.add(self.tab_ga,      text="  ② GA Parameters  ")
        self.nb.add(self.tab_results, text="  ③ Results  ")

        self._build_tab_setup()
        self._build_tab_ga()
        self._build_tab_results()

        # ── Bottom action bar ─────────────────────────────────────────────────
        bar = tk.Frame(self, bg=BG2, height=54)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.btn_run = tk.Button(
            bar, text="▶  Run Optimizer", command=self._start_ga,
            bg=ACCENT, fg="#fff", font=("Segoe UI", 11, "bold"),
            relief="flat", padx=22, pady=6, cursor="hand2",
            activebackground=ACCENT2, activeforeground="#fff"
        )
        self.btn_run.pack(side="right", padx=16, pady=10)

        self.btn_save = tk.Button(
            bar, text="💾  Save Schedule", command=self._save_schedule,
            bg=BG3, fg=FG_DIM, font=FONT_N, relief="flat",
            padx=14, pady=6, cursor="hand2", state="disabled"
        )
        self.btn_save.pack(side="right", padx=4, pady=10)

        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(bar, textvariable=self.status_var,
                 bg=BG2, fg=FG_DIM, font=FONT_S).pack(side="left", padx=16)

    # ── Tab 1: Subjects & Hours ───────────────────────────────────────────────
    def _build_tab_setup(self):
        f = self.tab_setup
        f.columnconfigure(0, weight=3)
        f.columnconfigure(1, weight=2)
        f.rowconfigure(1, weight=1)

        # ── Subjects section ───────────────────────────────────────
        ttk.Label(f, text="Subjects", style="Head.TLabel").grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 4))
        ttk.Label(f, text="Add up to 8 subjects with difficulty and exam priority.",
                  style="Dim.TLabel").grid(row=0, column=0, sticky="sw", padx=16, pady=(0, 0))

        subj_card = tk.Frame(f, bg=CARD, padx=10, pady=10)
        subj_card.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 12))
        subj_card.columnconfigure(0, weight=1)
        subj_card.rowconfigure(0, weight=1)

        # Treeview for subjects
        cols = ("name", "difficulty", "priority")
        self.subj_tree = ttk.Treeview(subj_card, columns=cols,
                                      show="headings", height=8)
        self.subj_tree.heading("name",       text="Subject")
        self.subj_tree.heading("difficulty", text="Difficulty")
        self.subj_tree.heading("priority",   text="Exam Priority")
        self.subj_tree.column("name",       width=180, anchor="w")
        self.subj_tree.column("difficulty", width=110, anchor="center")
        self.subj_tree.column("priority",   width=110, anchor="center")
        self.subj_tree.grid(row=0, column=0, columnspan=4, sticky="nsew", pady=(0, 8))

        sb = ttk.Scrollbar(subj_card, orient="vertical",
                           command=self.subj_tree.yview)
        self.subj_tree.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=4, sticky="ns", pady=(0, 8))

        # Input row
        tk.Label(subj_card, text="Name", bg=CARD, fg=FG_DIM, font=FONT_S).grid(
            row=1, column=0, sticky="w")
        self.ent_name = ttk.Entry(subj_card, width=18)
        self.ent_name.grid(row=2, column=0, sticky="ew", padx=(0, 6))

        tk.Label(subj_card, text="Difficulty", bg=CARD, fg=FG_DIM, font=FONT_S).grid(
            row=1, column=1, sticky="w")
        self.cmb_diff = ttk.Combobox(subj_card, values=["1 – Easy", "2 – Medium", "3 – Hard"],
                                     width=13, state="readonly")
        self.cmb_diff.current(1)
        self.cmb_diff.grid(row=2, column=1, sticky="ew", padx=(0, 6))

        tk.Label(subj_card, text="Exam Priority (1–5)", bg=CARD, fg=FG_DIM, font=FONT_S).grid(
            row=1, column=2, sticky="w")
        self.spn_prio = ttk.Spinbox(subj_card, from_=1, to=5, width=6)
        self.spn_prio.set(3)
        self.spn_prio.grid(row=2, column=2, sticky="w", padx=(0, 6))

        btn_row = tk.Frame(subj_card, bg=CARD)
        btn_row.grid(row=2, column=3, sticky="ew")
        self._btn(btn_row, "＋ Add",    self._add_subject,    ACCENT).pack(side="left", padx=(0, 4))
        self._btn(btn_row, "✕ Remove",  self._remove_subject, BG3).pack(side="left")
        self._btn(btn_row, "Clear All", self._clear_subjects, BG3).pack(side="left", padx=(4, 0))

        subj_card.columnconfigure(0, weight=2)
        subj_card.columnconfigure(1, weight=2)
        subj_card.columnconfigure(2, weight=1)
        subj_card.columnconfigure(3, weight=1)

        # ── Daily hours section ────────────────────────────────────
        ttk.Label(f, text="Daily Available Hours", style="Head.TLabel").grid(
            row=0, column=1, sticky="w", padx=(6, 16), pady=(12, 4))

        hours_card = tk.Frame(f, bg=CARD, padx=16, pady=14)
        hours_card.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))

        self.hours_vars = []
        for i, (day, default) in enumerate(zip(DAYS, DAY_DEFAULTS)):
            tk.Label(hours_card, text=day, bg=CARD, fg=FG, font=FONT_N,
                     width=11, anchor="w").grid(row=i, column=0, pady=3, sticky="w")
            var = tk.DoubleVar(value=default)
            self.hours_vars.append(var)
            slider = tk.Scale(hours_card, from_=0, to=12, resolution=0.5,
                              orient="horizontal", variable=var,
                              bg=CARD, fg=FG, highlightthickness=0,
                              troughcolor=BG3, activebackground=ACCENT,
                              sliderrelief="flat", length=180,
                              font=FONT_S)
            slider.grid(row=i, column=1, padx=(8, 4), pady=2)
            lbl = tk.Label(hours_card, textvariable=var, bg=CARD, fg=ACCENT2,
                           font=("Consolas", 9, "bold"), width=4, anchor="e")
            lbl.grid(row=i, column=2, padx=(2, 0))

    # ── Tab 2: GA Parameters ──────────────────────────────────────────────────
    def _build_tab_ga(self):
        f = self.tab_ga
        f.columnconfigure(0, weight=1)
        f.columnconfigure(1, weight=1)

        params = [
            ("Population Size",  "pop_size",    80,   10,  500, 1,     "Number of candidate schedules per generation."),
            ("Generations",      "generations", 200,  10, 2000, 10,    "Maximum number of GA iterations."),
            ("Mutation Rate",    "mut_rate",    0.15, 0.0, 1.0, 0.01,  "Probability of mutating each day's allocation."),
            ("Elite Count",      "elite_count", 2,    0,   20,  1,     "Best individuals copied unchanged each generation."),
            ("Tournament k",     "tourn_k",     3,    2,   10,  1,     "Candidates compared in each tournament selection."),
        ]

        self.ga_vars = {}

        for idx, (label, key, default, lo, hi, inc, hint) in enumerate(params):
            col  = idx % 2
            row_base = (idx // 2) * 3

            card = tk.Frame(f, bg=CARD, padx=14, pady=10)
            card.grid(row=row_base, column=col, sticky="ew",
                      padx=(14 if col == 0 else 6, 6 if col == 0 else 14),
                      pady=(10 if row_base == 0 else 4, 4))

            tk.Label(card, text=label, bg=CARD, fg=ACCENT2,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w")
            tk.Label(card, text=hint, bg=CARD, fg=FG_DIM,
                     font=FONT_S, wraplength=350).pack(anchor="w", pady=(0, 6))

            var = tk.DoubleVar(value=default) if isinstance(default, float) else tk.IntVar(value=default)
            self.ga_vars[key] = var

            spn = ttk.Spinbox(card, from_=lo, to=hi, increment=inc,
                              textvariable=var, width=10, font=FONT_N)
            spn.pack(anchor="w")

        # Progress section at bottom
        prog_frame = tk.Frame(f, bg=BG, padx=14)
        prog_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=10)

        tk.Label(prog_frame, text="Progress", bg=BG, fg=ACCENT2,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.prog_var = tk.DoubleVar(value=0)
        self.progressbar = ttk.Progressbar(prog_frame, variable=self.prog_var,
                                           maximum=100, length=400)
        self.progressbar.pack(fill="x", pady=(4, 0))
        self.prog_label = tk.Label(prog_frame, text="", bg=BG, fg=FG_DIM, font=FONT_S)
        self.prog_label.pack(anchor="w", pady=(2, 0))

    # ── Tab 3: Results ────────────────────────────────────────────────────────
    def _build_tab_results(self):
        f = self.tab_results
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)
        f.rowconfigure(3, weight=1)

        ttk.Label(f, text="Optimized Schedule", style="Head.TLabel").grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 4))

        # Schedule treeview
        sched_card = tk.Frame(f, bg=CARD, padx=8, pady=8)
        sched_card.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 6))
        sched_card.columnconfigure(0, weight=1)
        sched_card.rowconfigure(0, weight=1)

        sched_cols = ("subject",) + tuple(DAY_SHORT) + ("total", "target", "match")
        self.sched_tree = ttk.Treeview(sched_card, columns=sched_cols,
                                       show="headings", height=7)
        col_widths = {"subject": 130, "total": 58, "target": 58, "match": 62}
        for c in sched_cols:
            self.sched_tree.heading(c, text=c.capitalize())
            w = col_widths.get(c, 52)
            anch = "w" if c == "subject" else "center"
            self.sched_tree.column(c, width=w, anchor=anch, stretch=(c == "subject"))
        self.sched_tree.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(sched_card, orient="vertical",
                      command=self.sched_tree.yview).grid(row=0, column=1, sticky="ns")

        # Stats row
        stats_frame = tk.Frame(f, bg=BG)
        stats_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=4)
        stats_frame.columnconfigure((0, 1, 2, 3), weight=1)

        self.stat_vars = {k: tk.StringVar(value="—") for k in
                         ("fitness", "study_hrs", "utilisation", "gen")}
        labels = [("Fitness Score", "fitness"), ("Study Hours", "study_hrs"),
                  ("Utilisation",   "utilisation"), ("Generations", "gen")]
        for col, (lbl, key) in enumerate(labels):
            card = tk.Frame(stats_frame, bg=CARD, padx=10, pady=8)
            card.grid(row=0, column=col, sticky="ew",
                      padx=(0 if col else 0, 6 if col < 3 else 0))
            tk.Label(card, text=lbl, bg=CARD, fg=FG_DIM, font=FONT_S).pack()
            tk.Label(card, textvariable=self.stat_vars[key], bg=CARD,
                     fg=ACCENT2, font=("Segoe UI", 13, "bold")).pack()

        # Fitness chart
        ttk.Label(f, text="Fitness Convergence", style="Head.TLabel").grid(
            row=3, column=0, sticky="nw", padx=16, pady=(8, 2))
        self.canvas = tk.Canvas(f, bg=CARD, highlightthickness=0, height=130)
        self.canvas.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        f.rowconfigure(3, weight=1)

    # ── Widget helpers ────────────────────────────────────────────────────────
    def _btn(self, parent, text, cmd, bg):
        return tk.Button(parent, text=text, command=cmd, bg=bg, fg=FG,
                         font=FONT_S, relief="flat", padx=8, pady=4,
                         cursor="hand2", activebackground=ACCENT2,
                         activeforeground="#fff")

    # ── Subject management ────────────────────────────────────────────────────
    def _add_subject(self):
        name = self.ent_name.get().strip()
        if not name:
            messagebox.showwarning("Missing Name", "Enter a subject name.", parent=self)
            return
        if len(self.subjects) >= 8:
            messagebox.showwarning("Limit Reached", "Maximum 8 subjects allowed.", parent=self)
            return
        if any(s["name"].lower() == name.lower() for s in self.subjects):
            messagebox.showwarning("Duplicate", f"'{name}' is already in the list.", parent=self)
            return

        diff_raw = self.cmb_diff.get()
        diff = int(diff_raw[0])
        prio = int(self.spn_prio.get())

        self.subjects.append({"name": name, "diff": diff, "weight": prio})
        self.subj_tree.insert("", "end", values=(name, DIFF_MAP[diff], f"★ {prio}"))
        self.ent_name.delete(0, "end")
        self.status_var.set(f"{len(self.subjects)} subject(s) added.")

    def _remove_subject(self):
        sel = self.subj_tree.selection()
        if not sel:
            return
        idx = self.subj_tree.index(sel[0])
        self.subj_tree.delete(sel[0])
        self.subjects.pop(idx)
        self.status_var.set(f"{len(self.subjects)} subject(s) remaining.")

    def _clear_subjects(self):
        if not self.subjects:
            return
        if messagebox.askyesno("Clear All", "Remove all subjects?", parent=self):
            self.subj_tree.delete(*self.subj_tree.get_children())
            self.subjects.clear()
            self.status_var.set("Subjects cleared.")

    # ── Build config dict ─────────────────────────────────────────────────────
    def _build_config(self):
        if len(self.subjects) < 2:
            messagebox.showwarning("Not Enough Subjects",
                                   "Add at least 2 subjects before running.", parent=self)
            return None

        config = {
            "subjects":       [s["name"]   for s in self.subjects],
            "difficulty":     [s["diff"]   for s in self.subjects],
            "exam_weight":    [s["weight"] for s in self.subjects],
            "available_hours": [v.get() for v in self.hours_vars],
            "pop_size":        int(self.ga_vars["pop_size"].get()),
            "generations":     int(self.ga_vars["generations"].get()),
            "mut_rate":        float(self.ga_vars["mut_rate"].get()),
            "elite_count":     int(self.ga_vars["elite_count"].get()),
        }
        return config

    # ── Run GA in background thread ───────────────────────────────────────────
    def _start_ga(self):
        config = self._build_config()
        if config is None:
            return

        self.btn_run.configure(state="disabled", text="Running…")
        self.btn_save.configure(state="disabled")
        self.prog_var.set(0)
        self.prog_label.configure(text="Initialising…")
        self.nb.select(self.tab_ga)
        self.status_var.set("Running GA…")

        def _progress(gen, total, best):
            pct = gen / total * 100
            self.after(0, lambda: self.prog_var.set(pct))
            self.after(0, lambda: self.prog_label.configure(
                text=f"Generation {gen}/{total}   Best fitness: {best:.3f}"))

        def _worker():
            schedule, best_fit, history, targets = run_ga(config, _progress)
            self.after(0, lambda: self._on_ga_done(
                schedule, best_fit, history, targets, config))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_ga_done(self, schedule, best_fit, history, targets, config):
        self.result = {"schedule": schedule, "fitness": best_fit,
                       "history": history, "targets": targets, "config": config}

        self._populate_results(schedule, best_fit, history, targets, config)
        self.nb.select(self.tab_results)
        self.btn_run.configure(state="normal", text="▶  Run Optimizer")
        self.btn_save.configure(state="normal", fg=FG)
        self.status_var.set(f"Done!  Fitness: {best_fit:.4f}")

    # ── Populate results tab ──────────────────────────────────────────────────
    def _populate_results(self, schedule, best_fit, history, targets, config):
        n = len(config["subjects"])

        # Clear old rows
        self.sched_tree.delete(*self.sched_tree.get_children())

        weekly_totals = [sum(schedule[i]) for i in range(n)]

        for i in range(n):
            vals = [config["subjects"][i]]
            for d in range(7):
                h = schedule[i][d]
                vals.append(f"{h:.1f}" if h > 0 else "–")
            vals.append(f"{weekly_totals[i]:.1f}")
            vals.append(f"{targets[i]:.1f}")
            match = min(100.0, weekly_totals[i] / targets[i] * 100 if targets[i] > 0 else 0)
            vals.append(f"{match:.0f}%")
            tag = "over" if match >= 95 else ("under" if match < 70 else "ok")
            self.sched_tree.insert("", "end", values=vals, tags=(tag,))

        self.sched_tree.tag_configure("over",  foreground=GREEN)
        self.sched_tree.tag_configure("ok",    foreground=YELLOW)
        self.sched_tree.tag_configure("under", foreground=RED)

        # Stats
        total_study = sum(weekly_totals)
        total_avail = sum(config["available_hours"])
        self.stat_vars["fitness"].set(f"{best_fit:.3f}")
        self.stat_vars["study_hrs"].set(f"{total_study:.1f} / {total_avail:.1f} h")
        self.stat_vars["utilisation"].set(f"{total_study/total_avail*100:.1f}%")
        self.stat_vars["gen"].set(str(len(history)))

        # Draw fitness chart
        self._draw_chart(history)

    def _draw_chart(self, history):
        self.canvas.update_idletasks()
        W = self.canvas.winfo_width()  or 700
        H = self.canvas.winfo_height() or 130
        self.canvas.delete("all")

        if not history:
            return

        pad_l, pad_r, pad_t, pad_b = 48, 16, 14, 28
        min_f, max_f = min(history), max(history)
        span = max_f - min_f or 1

        def to_x(i):
            return pad_l + (i / max(len(history) - 1, 1)) * (W - pad_l - pad_r)

        def to_y(v):
            return pad_t + (1 - (v - min_f) / span) * (H - pad_t - pad_b)

        # Grid lines
        for k in range(5):
            y = pad_t + k * (H - pad_t - pad_b) / 4
            val = max_f - k * span / 4
            self.canvas.create_line(pad_l, y, W - pad_r, y,
                                    fill=BG3, width=1, dash=(4, 4))
            self.canvas.create_text(pad_l - 4, y, text=f"{val:.1f}",
                                    fill=FG_DIM, font=FONT_S, anchor="e")

        # Smoothed line
        pts = [(to_x(i), to_y(v)) for i, v in enumerate(history)]
        for i in range(len(pts) - 1):
            self.canvas.create_line(pts[i][0], pts[i][1],
                                    pts[i+1][0], pts[i+1][1],
                                    fill=ACCENT, width=2, smooth=True)

        # Start / end dots
        self.canvas.create_oval(pts[0][0]-4, pts[0][1]-4,
                                pts[0][0]+4, pts[0][1]+4,
                                fill=RED, outline="")
        self.canvas.create_oval(pts[-1][0]-5, pts[-1][1]-5,
                                pts[-1][0]+5, pts[-1][1]+5,
                                fill=GREEN, outline="")

        # X-axis labels
        ticks = 5
        for k in range(ticks + 1):
            idx = int(k * (len(history) - 1) / ticks)
            x   = to_x(idx)
            self.canvas.create_line(x, H - pad_b, x, H - pad_b + 4,
                                    fill=FG_DIM)
            self.canvas.create_text(x, H - pad_b + 8, text=str(idx + 1),
                                    fill=FG_DIM, font=FONT_S, anchor="n")

        self.canvas.create_text(W // 2, H - 4, text="Generation",
                                fill=FG_DIM, font=FONT_S, anchor="s")

        # Bind resize
        self.canvas.bind("<Configure>", lambda e: self._draw_chart(history))

    # ── Save schedule ─────────────────────────────────────────────────────────
    def _save_schedule(self):
        if not self.result:
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="study_plan",
            title="Save Study Plan",
            parent=self,
        )
        if not path:
            return

        r      = self.result
        config = r["config"]
        sched  = r["schedule"]
        tgts   = r["targets"]
        n      = len(config["subjects"])
        weekly = [sum(sched[i]) for i in range(n)]
        width  = max(len(s) for s in config["subjects"]) + 2

        lines = []
        lines.append("=" * 62)
        lines.append("  OPTIMIZED WEEKLY STUDY SCHEDULE  –  GA Result")
        lines.append("=" * 62)
        hdr  = f"{'Subject':<{width}}" + "".join(f"{d[:3]:>6}" for d in DAYS)
        hdr += f"{'Total':>7}  {'Target':>7}  {'Match%':>7}"
        lines.append(hdr)
        lines.append("-" * len(hdr))
        for i in range(n):
            row = f"{config['subjects'][i]:<{width}}"
            for d in range(7):
                h = sched[i][d]
                row += f"{h:>6.1f}" if h > 0 else f"{'–':>6}"
            mp = min(100.0, weekly[i] / tgts[i] * 100 if tgts[i] > 0 else 0)
            row += f"{weekly[i]:>7.1f}  {tgts[i]:>7.1f}  {mp:>6.0f}%"
            lines.append(row)
        lines.append("-" * len(hdr))
        daily = [sum(sched[i][d] for i in range(n)) for d in range(7)]
        lines.append(f"{'Daily Hours':<{width}}" + "".join(f"{s:>6.1f}" for s in daily))
        lines.append(f"{'Available':<{width}}" + "".join(f"{h:>6.1f}" for h in config["available_hours"]))
        lines.append("=" * 62)
        lines.append(f"\nFitness : {r['fitness']:.4f}")
        lines.append(f"Total Study Hours : {sum(weekly):.1f} / {sum(config['available_hours']):.1f}")
        lines.append(f"Utilisation : {sum(weekly)/sum(config['available_hours'])*100:.1f}%")
        lines.append(f"Generations run : {len(r['history'])}")
        lines.append("\nGA Parameters:")
        for k in ("pop_size", "generations", "mut_rate", "elite_count"):
            lines.append(f"  {k:<16}: {config[k]}")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        self.status_var.set(f"Saved → {os.path.basename(path)}")
        messagebox.showinfo("Saved", f"Schedule saved to:\n{path}", parent=self)


# ─────────────────────────────── entry point ──────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
