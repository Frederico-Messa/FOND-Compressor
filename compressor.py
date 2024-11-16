#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import collections
import pulp
import argcomplete
import natsort
import tap

Fact = tuple[int, str]
Action = str
State = tuple[Fact]

def is_null_fact(fact: Fact) -> bool:
    return fact[1] == apn.null_fact_token

from collections import OrderedDict
class PseudoConstraint(OrderedDict):
    pass
def efficiently_create_constraint(lhs: dict[pulp.LpVariable, float], sense: int, rhs: float) -> pulp.LpConstraint:
    lp_constraint = PseudoConstraint(lhs)
    lp_constraint.__class__ = pulp.LpConstraint
    lp_constraint.name = None
    lp_constraint.constant = -rhs
    lp_constraint.sense = sense
    lp_constraint.pi = None
    lp_constraint.slack = None
    lp_constraint.modified = True
    return lp_constraint

_maximum_i = -1
_do_partial_states_contain_facts: dict[int, dict[Fact, pulp.LpVariable]] = {}
_do_partial_states_represent_states: dict[int, dict[State, pulp.LpVariable]] = {}
_partial_states_number_of_facts: dict[int, pulp.LpVariable] = {}
def get_variables(k: int) -> tuple[dict[Fact, pulp.LpVariable], dict[State, pulp.LpVariable]]:
    global _maximum_i, _do_partial_states_contain_facts, _do_partial_states_represent_states, _partial_states_number_of_facts
    for i in range(_maximum_i + 1, k):
        _do_partial_states_contain_facts[i] = {fact: pulp.LpVariable(f"does_partial_state_{i}_contain_fact_{fact}", cat=pulp.LpBinary) for fact in facts}
        _do_partial_states_represent_states[i] = {state: pulp.LpVariable(f"does_partial_state_{i}_represent_state_{states_ids[state]}", cat=pulp.LpBinary) for state in states}
        _partial_states_number_of_facts[i] = pulp.LpVariable(f"partial_state_{i}_number_of_facts", lowBound=0, upBound=n, cat=pulp.LpInteger)
        _maximum_i = i
    return _do_partial_states_contain_facts, _do_partial_states_represent_states, _partial_states_number_of_facts

_states_negative_constraints: dict[State, dict[int, pulp.LpConstraint]] = {}
def get_negative_constraint(state: State, partial_state: int) -> pulp.LpConstraint: # for these constraints, caching is relevant
    if state not in _states_negative_constraints:
        _states_negative_constraints[state] = {}
    if partial_state not in _states_negative_constraints[state]:
        _states_negative_constraints[state][partial_state] = _partial_states_number_of_facts[partial_state] - pulp.lpSum(_do_partial_states_contain_facts[partial_state][fact] for fact in state) >= 1
    return _states_negative_constraints[state][partial_state]

def get_positive_constraints(state: State, partial_state: int) -> list[pulp.LpConstraint]: # for these constraints, using the efficient creation function is relevant
    positive_contrainst: list[pulp.LpConstraint] = []
    for fact in facts:
        if fact not in state:
            positive_contrainst.append(efficiently_create_constraint({_do_partial_states_contain_facts[partial_state][fact]: 1, do_partial_states_represent_states[partial_state][state]: 1}, pulp.LpConstraintLE, 1))
    return positive_contrainst

class ArgParsingNamespace(tap.Tap):
    separator_token: str
    null_fact_token: str
    ip_solver_label: str

    def configure(self) -> None:
        self.add_argument("--separator-token", type=str, default=" ")
        self.add_argument("--null-fact-token", type=str, default="-")
        self.add_argument("--goal-token", type=str, default="GOAL")
        self.add_argument("--ip-solver-label", type=str, default=pulp.LpSolverDefault.name)

if __name__ == "__main__":
    apn = ArgParsingNamespace()
    argcomplete.autocomplete(apn)
    apn.parse_args()

    solver = pulp.getSolver(apn.ip_solver_label, msg=False)

    # Parse the input
    mappings: dict[State, Action] = {}
    while True:
        line = input()
        if line == "": break
        pre_facts_and_action = line.split(apn.separator_token)
        pre_facts, action = pre_facts_and_action[:-1], pre_facts_and_action[-1]
        facts = enumerate(pre_facts)
        state = tuple(facts)
        assert state not in mappings.keys(), "The same state cannot be mapped to multiple actions."
        mappings[state] = action

    assert len({len(facts) for facts in mappings.keys()}) <= 1, "All entries must have the same number of facts. Use the null fact (hyphen token by default) to denote a don't care."
    n = len(next(iter(mappings.keys()))) if len(mappings.keys()) > 0 else None

    assert all(all(not is_null_fact(fact) for fact in facts) for facts in mappings.keys()), "Currently, partial states are not supported in the input."

    # Structures to optimize the construction of the IP problem
    facts: set[Fact] = set.union(*(set(state) for state in mappings.keys()))
    states: set[State] = set(mappings.keys())
    actions: set[Action] = set(mappings.values())
    states_ids: dict[State, int] = {state: i for i, state in enumerate(states)}
    actions_statess: dict[Action, set[State]] = collections.defaultdict(set)
    actions_factss: dict[Action, set[Fact]] = collections.defaultdict(set)
    for state, action in mappings.items():
        actions_statess[action].add(state)
        actions_factss[action].update(state)

    # Contruct and solve the IP problems
    for key_action in natsort.natsorted(actions):
        if key_action == apn.goal_token:
            continue
        for k in range(1, len(actions_statess[key_action]) + 1):
            ip_problem = pulp.LpProblem("Compressor", pulp.LpMinimize)
            partial_states = range(k)
            relevant_facts = actions_factss[key_action]
            do_partial_states_contain_facts, do_partial_states_represent_states, partial_states_number_of_facts = get_variables(k)

            constraints: list[pulp.LpConstraint] = []
            for partial_state in partial_states:
                constraints.append(partial_states_number_of_facts[partial_state] == pulp.lpSum(do_partial_states_contain_facts[partial_state][fact] for fact in facts))

                for state, action in mappings.items():
                    if action == key_action:
                        constraints.extend(get_positive_constraints(state, partial_state))
                    else:
                        constraints.append(get_negative_constraint(state, partial_state))

            for state in actions_statess[key_action]:
                constraints.append(pulp.lpSum(do_partial_states_represent_states[partial_state][state] for partial_state in partial_states) >= 1)

            ip_problem.extend(constraints)
            ip_problem += sum(partial_states_number_of_facts[partial_state] for partial_state in partial_states)

            ip_problem.solve(solver)

            # Print the solution
            if ip_problem.status == pulp.LpStatusOptimal:
                for partial_state in partial_states:
                    next_i = 0
                    for fact in sorted(relevant_facts):
                        if do_partial_states_contain_facts[partial_state][fact].value() == 1:
                            while next_i < fact[0]:
                                print(apn.null_fact_token, end=apn.separator_token)
                                next_i += 1
                            print(fact[1], end=apn.separator_token)
                            next_i += 1
                    while next_i < n:
                        print(apn.null_fact_token, end=apn.separator_token)
                        next_i += 1
                    print(key_action, flush=True)
                break
            else:
                assert (k + 1) <= len(actions_statess[key_action]), "There is a bug in the program. Please create an issue."
    print(flush=True)
