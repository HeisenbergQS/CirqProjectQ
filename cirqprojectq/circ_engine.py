# Copyright 2018 Heisenberg Quantum Simulations
# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Provides a projectq engine that translates a projectq circuit to a cirq circuit.
"""
from projectq import ops as pqo
from projectq.cengines import BasicEngine
from projectq.meta import get_control_count, QubitPlacementTag
from .common_rules import common_gates_ruleset
from . import xmon_rules
import cirq

class CIRQ(BasicEngine):
    r"""
    A projectq backend designated to translating to cirq.

    Args:
        - device (:class:`cirq.devices.Device`) - a device that provides the qubits.
        - rules (cirqprojectq._rules_pq_to_cirq.Ruleset_pq_to_cirq)
    """
    def __init__(self, qubits=None, device=None, rules=None):
        BasicEngine.__init__(self)
        #TODO: Make rules an input.
        if rules is None:
            self._rules = common_gates_ruleset
            self._rules.add_rules(xmon_rules.ALL_RULES)

        assert not (qubits is None and device is None), "Please specify one of qubits or device!"
        self._device = device
        self._qubits = qubits or device.qubits
        self._reset()
        self._new = True

    @property
    def circuit(self):
        r"""
        :class:`cirq.Circuit` - the circuit stored in the engine.
        """
        return self._circuit

# TODO: use a device?
    @property
    def device(self):
        r"""
        :class:`cirq.devices.Device`
        """
        return self._device

    @property
    def qubits(self):
        r"""
        list(:class:`cirq.QubitID`)
        """
        return self._qubits

    def _reset(self):
        r"""
        Reset the circuit.
        """
        self._circuit = cirq.circuits.Circuit()
        self._operations = []
        self._mapping = dict()
        self._inverse_mapping = dict()

    def is_available(self, cmd):
        """
        Returns true if the command can be translated.

        Args:
            cmd (Command): Command for which to check availability
        """
        if cmd.gate in (pqo.Measure, pqo.Allocate, pqo.Deallocate, pqo.Barrier):
            return True
        else:
            if type(cmd.gate) in self._rules.known_rules:
                return True
            else:
                return False


    def _store(self, cmd):
        r"""
        Append operations given in cmd to the :class:`cirq.Circuit`.
        """
        if self._new:
            self._new = False
            self._operations = []
        if cmd.gate == pqo.Allocate:
            qb_id = cmd.qubits[0][0].id
            for tag in cmd.tags:
                if isinstance(tag, QubitPlacementTag):
                    self._mapping[qb_id] = tag.position
                    self._inverse_mapping[tag.position] = qb_id
                    break
            if qb_id not in self._mapping:
                self._mapping[qb_id] = qb_id
#                raise Exception("No qubit placement info found in Allocate.\n"
#                                "Please make sure you are using the CIRQ Mapper")
            # TODO check if id in device.qubits
            return
        elif cmd.gate in (pqo.Allocate, pqo.Deallocate, pqo.Barrier):
            return
        else:
            try:
                self._operations.append(self._rules.translate(cmd, self._mapping, self._qubits))
            except:
                raise TypeError("Gate {} not known".format(cmd.gate.__class__))

    def _run(self):
        self.circuit.append(self._operations)

    def receive(self, command_list):
        """
        Receives a command list and, for each command, stores it until
        completion.

        Args:
            command_list: List of commands to execute
        """
        for cmd in command_list:
            if not cmd.gate == pqo.FlushGate():
                self._store(cmd)
            else:
                self._run()
                self._new = True
