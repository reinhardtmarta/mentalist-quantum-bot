from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap
from .rewriter import PatternRewriter
from .router import SmartGridRouter
from .layout import InitialLayoutSelector

class MentalistBot:
    """Orquestrador do compilador com seleção de layout, reescrita e amostragem Monte Carlo."""

    def __init__(self, coupling_map: CouplingMap, congestion_penalty: float = 0.3, lookahead_window: int = 3):
        self.coupling_map = coupling_map
        self.rewriter = PatternRewriter()
        self.layout_selector = InitialLayoutSelector(coupling_map)
        self.router = SmartGridRouter(
            coupling_map, 
            congestion_penalty=congestion_penalty, 
            lookahead_window=lookahead_window
        )

    def optimize(self, qc: QuantumCircuit, iterations: int = 20) -> QuantumCircuit:
        """Executa a compilação completa do circuito."""
        # Fase 1: Limpeza de padrões redundantes
        clean_qc = self.rewriter.simplify(qc)

        # Fase 2: Seleção de Layout Inicial
        initial_layout = self.layout_selector.get_initial_layout(clean_qc)

        best_circuit = None
        min_cost = float('inf')

        # Fase 3: Amostragem de Monte Carlo
        for seed in range(iterations):
            candidate = self.router.route(clean_qc, initial_layout=initial_layout, seed=seed)
            candidate = self.rewriter.simplify(candidate)

            cost = candidate.depth() + len(candidate.data)

            if cost < min_cost:
                min_cost = cost
                best_circuit = candidate

        return best_circuit
        
