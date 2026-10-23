import random
import networkx as nx
import numpy as np
from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap

class SmartGridRouter:
    """Roteador com penalização de tráfego e janela de visão futura (lookahead)."""

    def __init__(self, coupling_map: CouplingMap, congestion_penalty: float = 0.3, lookahead_window: int = 3):
        self.coupling_map = coupling_map
        self.graph = nx.Graph(list(coupling_map.get_edges()))
        self.congestion_penalty = congestion_penalty
        self.lookahead_window = lookahead_window

    def _calculate_future_cost(self, instructions: list, start_idx: int, hardware_map: list) -> float:
        """Calcula a distância física acumulada das próximas portas na janela de visão futura."""
        future_cost = 0.0
        count = 0
        for idx in range(start_idx, len(instructions)):
            if count >= self.lookahead_window:
                break
            inst = instructions[idx]
            if inst.operation.name == 'cx':
                q_log1, q_log2 = inst.qubits[0]._index, inst.qubits[1]._index
                q_phys1 = hardware_map[q_log1]
                q_phys2 = hardware_map[q_log2]
                future_cost += nx.shortest_path_length(self.graph, source=q_phys1, target=q_phys2)
                count += 1
        return future_cost

    def route(self, qc: QuantumCircuit, initial_layout: list[int], seed: int = 42) -> QuantumCircuit:
        """Executa o roteamento ciente de layout inicial e visão futura."""
        random.seed(seed)
        np.random.seed(seed)

        edge_weights = {edge: 1.0 for edge in self.graph.edges()}
        routed_qc = QuantumCircuit(qc.num_qubits, qc.num_clbits)
        hardware_map = list(initial_layout)

        instructions = list(qc.data)

        for i, inst in enumerate(instructions):
            if inst.operation.name == 'cx':
                q_log1, q_log2 = inst.qubits[0]._index, inst.qubits[1]._index
                q_phys1 = hardware_map[q_log1]
                q_phys2 = hardware_map[q_log2]

                if not self.graph.has_edge(q_phys1, q_phys2):
                    # Atualiza pesos do grafo com congestionamento acumulado
                    for u, v in self.graph.edges():
                        edge_key = (u, v) if (u, v) in edge_weights else (v, u)
                        self.graph[u][v]['weight'] = edge_weights.get(edge_key, 1.0)

                    path = nx.shortest_path(self.graph, source=q_phys1, target=q_phys2, weight='weight')

                    # Insere portas SWAP ao longo do caminho
                    for k in range(len(path) - 2):
                        u_node, v_node = path[k], path[k+1]
                        routed_qc.swap(u_node, v_node)

                        edge = (u_node, v_node) if (u_node, v_node) in edge_weights else (v_node, u_node)
                        edge_weights[edge] += self.congestion_penalty

                        # Atualiza o mapa de posições físicas
                        q_log_at_u = hardware_map.index(u_node)
                        q_log_at_v = hardware_map.index(v_node)
                        hardware_map[q_log_at_u] = v_node
                        hardware_map[q_log_at_v] = u_node

                        q_phys1 = v_node

                routed_qc.cx(q_phys1, q_phys2)
            else:
                phys_qubits = [hardware_map[q._index] for q in inst.qubits]
                routed_qc.append(inst.operation, phys_qubits, inst.clbits)

        return routed_qc
        
