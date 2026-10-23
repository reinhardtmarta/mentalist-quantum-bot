from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap
from .rewriter import PatternRewriter
from .router import SmartGridRouter


class MentalistBot:
    """Orquestrador do compilador usando otimização estocástica (Monte Carlo Sampling)."""

    def __init__(self, coupling_map: CouplingMap, congestion_penalty: float = 0.8):
        self.coupling_map = coupling_map
        self.rewriter = PatternRewriter()
        self.router = SmartGridRouter(coupling_map, congestion_penalty=congestion_penalty)

    def optimize(self, qc: QuantumCircuit, iterations: int = 20) -> QuantumCircuit:
        """Executa o pipeline de simplificação lógica, roteamento e seleção do melhor candidato."""
        # Step 1: Limpeza lógica inicial
        clean_qc = self.rewriter.simplify(qc)

        best_circuit = clean_qc.copy()
        min_cost = float('inf')

        if iterations <= 0:
            return best_circuit

        # Step 2: Amostragem estocástica de rotas
        for seed in range(iterations):
            candidate = self.router.route(clean_qc, seed=seed)
            candidate = self.rewriter.simplify(candidate)

            # Função de custo: Profundidade (passos temporais) + Total de instruções
            cost = candidate.depth() + len(candidate.data)

            if cost < min_cost:
                min_cost = cost
                best_circuit = candidate

        return best_circuit
