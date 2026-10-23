import random
import networkx as nx
import numpy as np
from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap


class SmartGridRouter:
    """Roteador de tráfego em grafos de acoplamento (Coupling Graphs)
    utilizando penalização por congestionamento acumulado.
    """

    def __init__(self, coupling_map: CouplingMap, congestion_penalty: float = 0.8):
        self.coupling_map = coupling_map
        self.graph = nx.Graph()
        self.graph.add_weighted_edges_from(
            [(u, v, 1.0) for u, v in coupling_map.get_edges()]
        )
        self.congestion_penalty = congestion_penalty

    def route(self, qc: QuantumCircuit, seed: int = 42) -> QuantumCircuit:
        """Executa o roteamento de portas de 2 qubits sobre o chip ajustando os pesos das arestas."""
        random.seed(seed)
        np.random.seed(seed)

        routed_qc = QuantumCircuit(qc.num_qubits, qc.num_clbits)
        hardware_map = list(range(qc.num_qubits))
        working_graph = self.graph.copy()

        for u, v in working_graph.edges():
            working_graph[u][v]["weight"] = 1.0

        for inst in qc.data:
            if inst.operation.name == 'cx':
                q_log1, q_log2 = inst.qubits[0]._index, inst.qubits[1]._index
                q_phys1 = hardware_map[q_log1]
                q_phys2 = hardware_map[q_log2]

                # Se não forem vizinhos diretos no chip, calcula a rota ponderada
                if not working_graph.has_edge(q_phys1, q_phys2):
                    path = nx.shortest_path(
                        working_graph,
                        source=q_phys1,
                        target=q_phys2,
                        weight='weight'
                    )

                    # Insere portas SWAP ao longo da rota
                    for k in range(len(path) - 2):
                        u_node, v_node = path[k], path[k + 1]
                        routed_qc.swap(u_node, v_node)

                        if working_graph.has_edge(u_node, v_node):
                            working_graph[u_node][v_node]['weight'] += self.congestion_penalty

                        # Atualiza as posições físicas de AMBOS os qubits lógicos envolvidos
                        q_log_at_u = hardware_map.index(u_node)
                        q_log_at_v = hardware_map.index(v_node)
                        hardware_map[q_log_at_u] = v_node
                        hardware_map[q_log_at_v] = u_node

                    q_phys1 = hardware_map[q_log1]
                    q_phys2 = hardware_map[q_log2]

                routed_qc.cx(q_phys1, q_phys2)
            else:
                phys_qubits = [hardware_map[q._index] for q in inst.qubits]
                routed_qc.append(inst.operation, phys_qubits, inst.clbits)

        return routed_qc
