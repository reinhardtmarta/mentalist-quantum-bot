from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap
from .rewriter import PatternRewriter
from .router import SmartGridRouter
from .layout import InitialLayoutSelector

class MentalistBot:
    """Orquestrador do compilador com negociação bidirecional de fronteira

    (Bidirectional Boundary Negotiation) entre blocos temporais.
    """

    def __init__(self, coupling_map: CouplingMap, congestion_penalty: float = 0.3, window_size: int = 20):
        self.coupling_map = coupling_map
        self.rewriter = PatternRewriter()
        self.layout_selector = InitialLayoutSelector(coupling_map)
        self.router = SmartGridRouter(coupling_map, congestion_penalty=congestion_penalty)
        self.window_size = window_size

    def _fatiar_circuito(self, qc: QuantumCircuit) -> list[QuantumCircuit]:
        """Divide o circuito em fatias temporais menores."""
        fatias = []
        instructions = list(qc.data)
        
        for i in range(0, len(instructions), self.window_size):
            bloco = instructions[i:i + self.window_size]
            sub_qc = QuantumCircuit(qc.num_qubits, qc.num_clbits)
            for inst in bloco:
                sub_qc.append(inst.operation, inst.qubits, inst.clbits)
            fatias.append(sub_qc)
            
        return fatias

    def _extrair_layout_final(self, circuit: QuantumCircuit, initial_layout: list[int]) -> list[int]:
        """Rastreia a posição física final dos qubits após a aplicação de portas SWAP."""
        hardware_map = list(initial_layout)
        for inst in circuit.data:
            if inst.operation.name == 'swap':
                u_node = inst.qubits[0]._index
                v_node = inst.qubits[1]._index
                q_log_at_u = hardware_map.index(u_node)
                q_log_at_v = hardware_map.index(v_node)
                hardware_map[q_log_at_u] = v_node
                hardware_map[q_log_at_v] = u_node
        return hardware_map

    def optimize(self, qc: QuantumCircuit, iterations: int = 10, top_k: int = 3) -> QuantumCircuit:
        """Executa a compilação com consenso de fronteira entre blocos consecutivos."""
        clean_qc = self.rewriter.simplify(qc)
        current_layout = self.layout_selector.get_initial_layout(clean_qc)
        fatias = self._fatiar_circuito(clean_qc)
        circuito_final = QuantumCircuit(qc.num_qubits, qc.num_clbits)

        for i in range(len(fatias)):
            fatia_atual = fatias[i]
            
            # 1. Gera candidatos para o bloco atual
            candidatos = []
            for seed in range(iterations):
                cand = self.router.route(fatia_atual, initial_layout=current_layout, seed=seed)
                cand = self.rewriter.simplify(cand)
                cost = cand.depth() + len(cand.data)
                candidatos.append((cost, cand))
            
            candidatos.sort(key=lambda x: x[0])
            top_candidatos = candidatos[:top_k]

            # 2. Negocia com o bloco seguinte
            if i + 1 < len(fatias):
                fatia_seguinte = fatias[i + 1]
                melhor_custo_conjunto = float('inf')
                vencedor_atual = top_candidatos[0][1]
                layout_vencedor = current_layout

                for _, cand_atual in top_candidatos:
                    layout_saida = self._extrair_layout_final(cand_atual, current_layout)
                    
                    # Teste preditivo no bloco subsequente
                    cand_proximo = self.router.route(fatia_seguinte, initial_layout=layout_saida, seed=42)
                    custo_conjunto = len(cand_atual.data) + len(cand_proximo.data)

                    if custo_conjunto < melhor_custo_conjunto:
                        melhor_custo_conjunto = custo_conjunto
                        vencedor_atual = cand_atual
                        layout_vencedor = layout_saida

                circuito_final.compose(vencedor_atual, inplace=True)
                current_layout = layout_vencedor
            else:
                vencedor_atual = top_candidatos[0][1]
                circuito_final.compose(vencedor_atual, inplace=True)

        return circuito_final
        
