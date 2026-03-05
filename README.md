# Genetic Algorithm – Study Plan Optimizer
### Intelligent Student Performance Evaluation and Support System

A Python micro-project that uses a **Genetic Algorithm (GA)** to generate an optimized
weekly study timetable, maximizing student performance under real-world time constraints.
Available as both a **command-line tool** and a **Tkinter desktop UI**.

---

## Project Files

| File | Description |
|---|---|
| `genetic_study_planner.py` | Command-line version (no dependencies) |
| `study_planner_ui.py` | Desktop GUI version (Tkinter — stdlib only) |
| `STUDY_DOCUMENT.md` | Full theory, worked examples, and algorithm details |
| `requirements.txt` | Dependency list (stdlib only — nothing to install) |

---

## Requirements

- **Python 3.8 or higher**
- No third-party packages required — uses only the Python Standard Library

Verify your Python version:

```bash
python --version
```

Install dependencies (none required, but listed for reference):

```bash
pip install -r requirements.txt
```

---

## How to Run

### Option A — Command-Line Interface

```bash
python genetic_study_planner.py
```

Follow the interactive prompts:
1. Enter the number of subjects (2–8)
2. For each subject: `Name, Difficulty (1-3), Exam Priority (1-5)`
   - Example: `Maths, 3, 5`
3. Enter available study hours for each day (Mon–Sun) — press Enter for defaults
4. Set GA parameters (population, generations, mutation rate, elitism) — press Enter for defaults

The optimized schedule is printed to the terminal. You are then asked whether to save
it to `study_plan.txt`.

**Quick run with all defaults (3 subjects example):**
```
Subject 1: Maths, 3, 5
Subject 2: Physics, 2, 4
Subject 3: English, 1, 3
(press Enter for everything else)
```

---

### Option B — Graphical Desktop UI

```bash
python study_planner_ui.py
```

A dark-themed desktop window opens with three tabs:

| Tab | What to do |
|---|---|
| **① Subjects & Hours** | Add subjects (name + difficulty + priority), set daily hour sliders |
| **② GA Parameters** | Tune population size, generations, mutation rate, elitism, tournament size |
| **③ Results** | View the optimized timetable, stats, and fitness convergence chart |

Click **▶ Run Optimizer** (bottom right) to start.  
Click **💾 Save Schedule** to export the result to a `.txt` file.

---

## Input Parameters

| Parameter | Description | Default |
|---|---|---|
| Subject name | Free-text | — |
| Difficulty | 1 = Easy, 2 = Medium, 3 = Hard | — |
| Exam priority | 1 (low) to 5 (high) | — |
| Daily hours | Available study hours Mon–Sun | 6,6,6,6,5,8,8 |
| Population size | Candidate schedules per generation | 80 |
| Generations | Maximum GA iterations | 200 |
| Mutation rate | Per-day random mutation probability | 0.15 |
| Elite count | Top individuals preserved unchanged | 2 |
| Tournament k | Candidates per selection tournament | 3 |

---

## GA Design Summary

```
Chromosome  →  [n_subjects × 7 days] matrix of study hours (real-valued)
Targets     →  Proportional to difficulty × exam_priority / total
Fitness     →  F1 (target deviation) + F2 (daily overflow) +
               F3 (subject neglect) + F4 (priority bonus)
Selection   →  Tournament Selection  (k = 3)
Crossover   →  Single-Point  (cut by day column)
Mutation    →  Per-day random redistribution  (prob = mut_rate)
Elitism     →  Top E chromosomes copied unchanged each generation
Termination →  Max generations  OR  50-gen stagnation
```

### Fitness Function

| Term | Formula | Purpose |
|---|---|---|
| F1 | −2 × Σ\|assigned − target\| | Penalise deviation from ideal hours |
| F2 | −5 × Σ max(0, day_total − available) | Penalise exceeding daily budget |
| F3 | −10 × count(subject with 0 hours) | Penalise neglected subjects |
| F4 | +0.5 × Σ (diff × priority) for met targets | Reward important subjects on track |

---

## Output

**CLI:**
- Weekly timetable (hours per subject per day)
- Daily utilisation vs available hours  
- Per-subject assigned vs target vs match %  
- Fitness convergence trace (ASCII bar chart)
- Optional save to `study_plan.txt`

**GUI:**
- Interactive timetable with colour-coded match % (green/yellow/red)
- Stat cards: fitness score, total study hours, utilisation %, generations used
- Live fitness convergence line chart
- File-dialog save to any `.txt` path

---

## Further Reading

See [STUDY_DOCUMENT.md](STUDY_DOCUMENT.md) for:
- Full theoretical background on Genetic Algorithms
- Biological analogy and key terminology
- Detailed explanation of every GA operator used
- Step-by-step worked example
- Time and space complexity analysis
- Comparison with alternative approaches
- Limitations and possible extensions
- Academic references
