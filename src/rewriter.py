from qiskit import QuantumCircuit

class PatternRewriter:
    """Módulo de reescrita local de padrões (Peephole Optimization)

    para eliminação de portas lógicas inversas sequenciais.
    """

    def __init__(self, target_gates=None):
        if target_gates is None:
            self.target_gates = ['h', 'cx', 'x', 'z', 'y']
        else:
            self.target_gates = target_gates

    def simplify(self, qc: QuantumCircuit) -> QuantumCircuit:
        """Percorre o circuito e remove pares de portas autoinversas seguidas no mesmo qubit."""
        instructions = qc.data.copy()
        new_instructions = []
        i = 0

        while i < len(instructions):
            inst = instructions[i]
            if i + 1 < len(instructions):
                next_inst = instructions[i + 1]
                # Verifica se são duas portas idênticas aplicadas aos mesmos qubits
                if (inst.operation.name == next_inst.operation.name and
                    inst.qubits == next_inst.qubits and
                    inst.operation.name in self.target_gates):
                    # Cancela o par (ex: H-H = Identidade)
                    i += 2
                    continue
            new_instructions.append(inst)
            i += 1

        qc_simplified = QuantumCircuit(qc.num_qubits, qc.num_clbits)
        for inst in new_instructions:
            qc_simplified.append(inst.operation, inst.qubits, inst.clbits)

        return qc_simplified
                    
