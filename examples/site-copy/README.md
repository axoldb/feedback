# Examples page copy (prepared; not deployed)

## DEAP

### One population. Two evolutionary paths.

**Problem:** Comparing evolutionary strategies normally means manually copying fragile process
state and losing a durable record of how each continuation began.

**DEAP does:** Candidate initialization, knapsack fitness, tournament selection, crossover and
mutation.

**AxolDB adds:** Complete generation checkpoints, canonical candidate membership and multiplicity,
RNG/configuration context, and application-level provenance connecting two ordinary Population
continuations to the same generation-20 source. This is not native Fork lineage.

Use `../deap-knapsack/results/comparison.png`, link the walkthrough at
`../deap-knapsack/README.md`, and link `../downloads/axoldb-deap-knapsack-1.0.0.zip` after the
license/repository-policy blocker is resolved.

## Mesa

### Same starting point. Different futures.

**Problem:** Scenario comparisons are difficult to audit when agent identities, activation order,
RNG state and the exact shared starting grid are not preserved together.

**Mesa does:** Agent activation, neighborhood satisfaction and moves on a toroidal grid.

**AxolDB adds:** Per-agent identity/state, historical Generations, a complete step-30 checkpoint,
and application-level provenance for two ordinary Population continuations with different
thresholds. This is not native Fork lineage.

Use `../mesa-schelling/results/scenarios.png`, link the walkthrough at
`../mesa-schelling/README.md`, and link `../downloads/axoldb-mesa-schelling-1.0.0.zip` after the
license/repository-policy blocker is resolved.
