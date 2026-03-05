"""
============================================================
  Genetic Algorithm - Based Study Plan Optimization
  Intelligent Student Performance Evaluation & Support System
============================================================
  Module  : Soft Computing (Micro Project)
  Method  : Genetic Algorithm (GA)
  Goal    : Optimize a weekly study schedule to maximize
            student performance under time constraints.
============================================================

 GA Concepts Used
 ─────────────────────────────────────────────────────────
  Chromosome  : 2-D matrix  [subjects × days]
                Each gene = study hours allocated to a
                subject on a given day.

  Fitness     : Weighted score rewarding
                  • Meeting target hours per subject
                  • Proportional coverage for harder subjects
                  • Not exceeding daily available hours
                  • Ensuring minimum hours for every subject

  Selection   : Tournament Selection (pressure = 3)

  Crossover   : Single-Point Crossover (column-wise, by day)

  Mutation    : Random-swap mutation on a random day's row

  Termination : Max generations  OR  fitness convergence
============================================================
"""

import random
import copy
import sys

# ─────────────────────────────── helpers ──────────────────────────────────────

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"]

DIFFICULTY_LABELS = {"1": "Easy", "2": "Medium", "3": "Hard"}

def clear_line():
    print()

# ─────────────────────────────── user input ───────────────────────────────────

def get_user_input():
    print("=" * 62)
    print("   GENETIC ALGORITHM – STUDY PLAN OPTIMIZER")
    print("=" * 62)

    # ── Subjects ──────────────────────────────────────────────────
    while True:
        try:
            n = int(input("\nHow many subjects do you study? (2–8): ").strip())
            if 2 <= n <= 8:
                break
            print("  Please enter a number between 2 and 8.")
        except ValueError:
            print("  Invalid input. Enter a whole number.")

    subjects = []
    difficulty = []
    exam_weight = []

    print("\nFor each subject enter: name | difficulty (1=Easy 2=Medium 3=Hard)"
          " | exam priority (1–5)")
    print("-" * 60)

    for i in range(n):
        while True:
            raw = input(f"  Subject {i+1}: ").strip()
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            if len(parts) != 3:
                # try space-separated fallback
                parts = raw.split()
            if len(parts) < 3:
                print("  Format: <name>, <difficulty 1-3>, <priority 1-5>")
                continue
            name = parts[0]
            try:
                diff = int(parts[-2]) if len(parts) > 3 else int(parts[1])
                prio = int(parts[-1])
            except ValueError:
                print("  Difficulty and priority must be integers.")
                continue
            if diff not in (1, 2, 3):
                print("  Difficulty must be 1, 2 or 3.")
                continue
            if not (1 <= prio <= 5):
                print("  Priority must be between 1 and 5.")
                continue
            subjects.append(name)
            difficulty.append(diff)
            exam_weight.append(prio)
            break

    # ── Daily available hours ──────────────────────────────────────
    print("\nEnter available study hours for each day  (0–12).")
    print("  (Press Enter to use the default shown in brackets.)")
    print("-" * 60)

    defaults = [6, 6, 6, 6, 5, 8, 8]        # Mon–Sun
    available_hours = []
    for i, day in enumerate(DAYS):
        while True:
            raw = input(f"  {day:<12} [default {defaults[i]}h]: ").strip()
            if raw == "":
                available_hours.append(defaults[i])
                break
            try:
                h = float(raw)
                if 0 <= h <= 12:
                    available_hours.append(h)
                    break
                print("  Must be between 0 and 12.")
            except ValueError:
                print("  Enter a number (e.g. 5 or 5.5).")

    # ── GA parameters ─────────────────────────────────────────────
    print("\nGA Parameters  (press Enter to accept defaults).")
    print("-" * 60)

    pop_size     = _int_input("  Population size       [default 80]: ",  80,  10, 500)
    generations  = _int_input("  Number of generations [default 200]: ", 200, 10, 2000)
    mut_rate     = _float_input("  Mutation rate 0–1     [default 0.15]: ", 0.15, 0.0, 1.0)
    elite_count  = _int_input("  Elite count           [default 2]: ",   2,   0,  10)

    print("\n" + "=" * 62)
    return {
        "subjects": subjects,
        "difficulty": difficulty,
        "exam_weight": exam_weight,
        "available_hours": available_hours,
        "pop_size": pop_size,
        "generations": generations,
        "mut_rate": mut_rate,
        "elite_count": elite_count,
    }


def _int_input(prompt, default, lo, hi):
    while True:
        raw = input(prompt).strip()
        if raw == "":
            return default
        try:
            v = int(raw)
            if lo <= v <= hi:
                return v
            print(f"  Must be between {lo} and {hi}.")
        except ValueError:
            print("  Enter a whole number.")


def _float_input(prompt, default, lo, hi):
    while True:
        raw = input(prompt).strip()
        if raw == "":
            return default
        try:
            v = float(raw)
            if lo <= v <= hi:
                return v
            print(f"  Must be between {lo} and {hi}.")
        except ValueError:
            print("  Enter a decimal number.")


# ─────────────────────────────── chromosome ───────────────────────────────────

def compute_targets(config):
    """
    Compute ideal weekly study hours per subject.
    Combines difficulty (1-3) and exam_weight (1-5) into a
    proportional target from the total available weekly hours.
    """
    total_hours = sum(config["available_hours"])
    scores = [d * w for d, w in zip(config["difficulty"], config["exam_weight"])]
    total_score = sum(scores)
    targets = [(s / total_score) * total_hours for s in scores]
    return targets


def random_chromosome(config):
    """
    Create a random schedule: matrix [n_subjects × 7 days].
    Each column (day) sums to ≤ available_hours[day].
    Hours are in 0.5-h increments.
    """
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


# ─────────────────────────────── fitness ──────────────────────────────────────

def fitness(schedule, config, targets):
    """
    Fitness score (higher = better).

    Components:
      F1 – Penalise deviation from target hours per subject.
      F2 – Penalise exceeding daily available hours.
      F3 – Penalise subjects that get 0 hours all week.
      F4 – Bonus for hard / high-priority subjects meeting their target.
    """
    n = len(config["subjects"])
    score = 0.0

    # ── F1: target coverage ────────────────────────────────────────
    weekly_totals = [sum(schedule[i]) for i in range(n)]
    for i in range(n):
        deviation = abs(weekly_totals[i] - targets[i])
        score -= deviation * 2.0                      # penalty

    # ── F2: daily capacity ────────────────────────────────────────
    for d in range(7):
        day_total = sum(schedule[i][d] for i in range(n))
        overflow = max(0, day_total - config["available_hours"][d])
        score -= overflow * 5.0                       # heavy penalty

    # ── F3: neglected subjects ────────────────────────────────────
    for i in range(n):
        if weekly_totals[i] == 0:
            score -= 10.0

    # ── F4: bonus for priority subjects ──────────────────────────
    for i in range(n):
        w = config["exam_weight"][i] * config["difficulty"][i]
        if weekly_totals[i] >= targets[i]:
            score += w * 0.5

    return score


# ─────────────────────────────── GA operators ─────────────────────────────────

def tournament_select(population, fitnesses, k=3):
    """Return the best individual from k random candidates."""
    contestants = random.sample(range(len(population)), k)
    best = max(contestants, key=lambda idx: fitnesses[idx])
    return copy.deepcopy(population[best])


def crossover(parent1, parent2):
    """
    Single-point crossover by day (column).
    A random cut-point splits the 7-day week; days before the
    cut come from parent1, days after from parent2.
    """
    if len(parent1[0]) < 2:
        return copy.deepcopy(parent1), copy.deepcopy(parent2)

    point = random.randint(1, 6)          # cut between day point-1 and point
    n = len(parent1)

    child1 = [[parent1[i][d] if d < point else parent2[i][d] for d in range(7)]
              for i in range(n)]
    child2 = [[parent2[i][d] if d < point else parent1[i][d] for d in range(7)]
              for i in range(n)]
    return child1, child2


def mutate(schedule, config, mut_rate):
    """
    Swap mutation: for each day independently (probability = mut_rate),
    randomly redistribute hours among subjects for that day.
    """
    n = len(config["subjects"])
    for d in range(7):
        if random.random() < mut_rate:
            budget = config["available_hours"][d]
            # re-randomise this day's column
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
                    for rest in slots[idx+1:]:
                        schedule[rest][d] = 0
                    break
    return schedule


# ─────────────────────────────── main GA loop ─────────────────────────────────

def run_ga(config):
    n_subj   = len(config["subjects"])
    targets  = compute_targets(config)

    # ── Initial population ────────────────────────────────────────
    population = [random_chromosome(config) for _ in range(config["pop_size"])]
    best_schedule = None
    best_fitness  = float("-inf")
    history       = []                    # best fitness per generation

    print("\n  Running Genetic Algorithm …")
    print(f"  Population: {config['pop_size']}  |  "
          f"Generations: {config['generations']}  |  "
          f"Mutation rate: {config['mut_rate']}")
    print("-" * 62)

    stagnation = 0
    prev_best  = float("-inf")

    for gen in range(1, config["generations"] + 1):
        # Evaluate fitness
        fitnesses = [fitness(ind, config, targets) for ind in population]

        # Track best
        gen_best_idx = max(range(len(population)), key=lambda i: fitnesses[i])
        gen_best_fit = fitnesses[gen_best_idx]
        history.append(gen_best_fit)

        if gen_best_fit > best_fitness:
            best_fitness  = gen_best_fit
            best_schedule = copy.deepcopy(population[gen_best_idx])

        # Progress display
        if gen % max(1, config["generations"] // 10) == 0 or gen == 1:
            bar_len = 30
            filled  = int(bar_len * gen / config["generations"])
            bar     = "█" * filled + "░" * (bar_len - filled)
            print(f"  Gen {gen:>5}/{config['generations']}  [{bar}]  "
                  f"Best fitness: {best_fitness:.2f}")

        # Early stopping on convergence
        if abs(gen_best_fit - prev_best) < 1e-6:
            stagnation += 1
        else:
            stagnation = 0
        prev_best = gen_best_fit

        if stagnation >= 50:
            print(f"\n  Converged early at generation {gen}.")
            break

        # ── Build next generation ──────────────────────────────────────
        # Elitism: keep top individuals
        sorted_pop = sorted(range(len(population)),
                            key=lambda i: fitnesses[i], reverse=True)
        next_gen = [copy.deepcopy(population[sorted_pop[e]])
                    for e in range(min(config["elite_count"], len(population)))]

        while len(next_gen) < config["pop_size"]:
            p1 = tournament_select(population, fitnesses)
            p2 = tournament_select(population, fitnesses)
            c1, c2 = crossover(p1, p2)
            c1 = mutate(c1, config, config["mut_rate"])
            c2 = mutate(c2, config, config["mut_rate"])
            next_gen.extend([c1, c2])

        population = next_gen[:config["pop_size"]]

    return best_schedule, best_fitness, history, targets


# ─────────────────────────────── output ───────────────────────────────────────

def print_schedule(schedule, config, targets, best_fitness):
    n     = len(config["subjects"])
    width = max(len(s) for s in config["subjects"]) + 2

    print("\n" + "=" * 62)
    print("   OPTIMIZED WEEKLY STUDY SCHEDULE")
    print("=" * 62)

    # Header row
    header = f"{'Subject':<{width}}" + "".join(f"{d[:3]:>6}" for d in DAYS) + f"{'Total':>7}  {'Target':>7}"
    print(header)
    print("-" * len(header))

    weekly_totals = [sum(schedule[i]) for i in range(n)]

    for i in range(n):
        row = f"{config['subjects'][i]:<{width}}"
        for d in range(7):
            h = schedule[i][d]
            row += f"{h:>6.1f}" if h > 0 else f"{'–':>6}"
        diff_label = DIFFICULTY_LABELS[str(config["difficulty"][i])]
        row += f"{weekly_totals[i]:>7.1f}  {targets[i]:>7.1f}"
        print(row)

    print("-" * len(header))

    # Totals row
    daily_sums = [sum(schedule[i][d] for i in range(n)) for d in range(7)]
    total_row = f"{'Daily Total':<{width}}"
    for d in range(7):
        avail = config["available_hours"][d]
        total_row += f"{daily_sums[d]:>6.1f}"
    print(total_row)

    avail_row = f"{'Available':<{width}}"
    for d in range(7):
        avail_row += f"{config['available_hours'][d]:>6.1f}"
    print(avail_row)
    print("=" * 62)

    # Summary stats
    print(f"\n  Fitness Score   : {best_fitness:.4f}")
    total_study = sum(weekly_totals)
    total_avail = sum(config["available_hours"])
    print(f"  Total Study Hrs : {total_study:.1f} / {total_avail:.1f} available")
    print(f"  Utilisation     : {(total_study/total_avail)*100:.1f}%")

    print("\n  Subject Summary:")
    print(f"  {'Subject':<{width}} {'Diff':>6}  {'Priority':>8}  "
          f"{'Assigned':>9}  {'Target':>8}  {'Match%':>7}")
    print("  " + "-" * (width + 45))
    for i in range(n):
        match_pct = (weekly_totals[i] / targets[i] * 100) if targets[i] > 0 else 0
        print(f"  {config['subjects'][i]:<{width}} "
              f"{DIFFICULTY_LABELS[str(config['difficulty'][i])]:>6}  "
              f"{config['exam_weight'][i]:>8}  "
              f"{weekly_totals[i]:>9.1f}  "
              f"{targets[i]:>8.1f}  "
              f"{match_pct:>6.1f}%")

    print("\n  Fitness history (every 10%):")
    step = max(1, len(history_global) // 10)
    sample = history_global[::step]
    for idx, val in enumerate(sample):
        bar = "█" * max(0, int((val - min(history_global)) /
                               max(1, max(history_global) - min(history_global)) * 20))
        print(f"    Gen ~{idx*step+1:>4} : {val:>8.2f}  {bar}")


# ─────────────────────────────── entry point ──────────────────────────────────

history_global = []   # accessible for display after run_ga

def main():
    global history_global

    print("\n  Welcome to the GA-Based Study Plan Optimizer!")
    print("  This tool builds a personalized weekly study schedule")
    print("  using a Genetic Algorithm to maximize your performance.\n")

    config = get_user_input()

    schedule, best_fit, history, targets = run_ga(config)
    history_global = history

    print_schedule(schedule, config, targets, best_fit)

    # ── Export option ─────────────────────────────────────────────
    print()
    save = input("  Save schedule to 'study_plan.txt'? (y/n) [y]: ").strip().lower()
    if save in ("", "y", "yes"):
        export_schedule(schedule, config, targets, best_fit, history)
        print("  Saved → study_plan.txt")

    print("\n  Good luck with your studies!")
    print("=" * 62 + "\n")


def export_schedule(schedule, config, targets, best_fitness, history):
    n     = len(config["subjects"])
    width = max(len(s) for s in config["subjects"]) + 2
    lines = []

    lines.append("=" * 62)
    lines.append("  OPTIMIZED WEEKLY STUDY SCHEDULE  (GA Result)")
    lines.append("=" * 62)
    lines.append("")

    header = f"{'Subject':<{width}}" + "".join(f"{d[:3]:>6}" for d in DAYS) + f"{'Total':>7}  {'Target':>7}"
    lines.append(header)
    lines.append("-" * len(header))

    weekly_totals = [sum(schedule[i]) for i in range(n)]
    for i in range(n):
        row = f"{config['subjects'][i]:<{width}}"
        for d in range(7):
            h = schedule[i][d]
            row += f"{h:>6.1f}" if h > 0 else f"{'–':>6}"
        row += f"{weekly_totals[i]:>7.1f}  {targets[i]:>7.1f}"
        lines.append(row)

    lines.append("-" * len(header))
    daily_sums = [sum(schedule[i][d] for i in range(n)) for d in range(7)]
    lines.append(f"{'Daily Total':<{width}}" + "".join(f"{s:>6.1f}" for s in daily_sums))
    lines.append(f"{'Available':<{width}}" + "".join(f"{h:>6.1f}" for h in config["available_hours"]))
    lines.append("=" * 62)
    lines.append(f"\nFitness Score   : {best_fitness:.4f}")
    lines.append(f"Total Study Hrs : {sum(weekly_totals):.1f} / {sum(config['available_hours']):.1f}")

    lines.append("\nSubject Summary:")
    lines.append(f"  {'Subject':<{width}} {'Diff':>6}  {'Priority':>8}  "
                 f"{'Assigned':>9}  {'Target':>8}  {'Match%':>7}")
    for i in range(n):
        match_pct = (weekly_totals[i] / targets[i] * 100) if targets[i] > 0 else 0
        lines.append(f"  {config['subjects'][i]:<{width}} "
                     f"{DIFFICULTY_LABELS[str(config['difficulty'][i])]:>6}  "
                     f"{config['exam_weight'][i]:>8}  "
                     f"{weekly_totals[i]:>9.1f}  "
                     f"{targets[i]:>8.1f}  "
                     f"{match_pct:>6.1f}%")

    lines.append("\nGA Parameters Used:")
    lines.append(f"  Population size : {config['pop_size']}")
    lines.append(f"  Generations     : {config['generations']}")
    lines.append(f"  Mutation rate   : {config['mut_rate']}")
    lines.append(f"  Elite count     : {config['elite_count']}")

    import os
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study_plan.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
