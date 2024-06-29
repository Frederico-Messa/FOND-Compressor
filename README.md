# FOND Compressor

The FOND Compressor is the compressor of FOND solutions used by the [AND* Project](https://github.com/Frederico-Messa/And-Star-Project).

- Messa and Pereira, *"Policy-Space Search: Equivalences, Improvements, and Compression"*, submitted to AIJ. [(arXiv)](https://arxiv.org/abs/2403.19883)

---

This project version was mainly tested in **Linux Mint 21.2**.

*Note:* A newer version of the FOND Compressor might be available in **[GitHub](https://github.com/Frederico-Messa/FOND-Compressor)**.

---

### Installing Python Dependencies

```
pip3 install -r requirements.txt
```

---

### Usage

```
./compressor.py
```

#### Optional Arguments

- **`--separator-token`** (default `" "`): Separates the facts and the actions in the input and the output.
- **`--null-fact-token`** (default `"-"`): Represents the null fact in the output.
- **`--goal-token`** (default `"GOAL"`): Represents the "goal" states in the input. These states are considered (so that no output mapping captures them), but they are not compressed.
- **`--ip-solver-label`** (default `"PULP_CBC_CMD"`): Label of the IP solver to be used.

#### Example Input and Output

Each line has `n+1` tokens, with `n` equal to the number of variables in the SAS+ task.

An empty line denotes the end of the input and the output.

- Input:
```
Fact1 Fact2 Fact3 Action1
Fact1 Fact2 not(Fact3) Action1
not(Fact1) not(Fact2) not(Fact3) Action2
not(Fact1) Fact2 Fact3 GOAL

```

- Output:
```
Fact1 - - Action1
- not(Fact2) - Action2

```

---

### Setting up a Custom IP Solver

[Here](https://coin-or.github.io/pulp/guides/how_to_configure_solvers.html) there is a guide on how to set up a custom IP solver.
