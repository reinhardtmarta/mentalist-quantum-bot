import random
import networkx as nx
import numpy as np
from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap

class SmartGridRouter:
    """Roteador de tráfego em grafos de acoplamento (Coupling Graphs)
    utilizando penalidade por congestionamento acumulado.
    """

    def __init__(self, coupling_map: CouplingMap, congestion_penalty: float = 0.8):
        self.coupling_map = coupling_map
        # Converte as arestas do CouplingMap diretamente num grafo do NetworkX
        self.graph = nx.Graph(list(coupling_map.get_edges()))
        self.congestion_penalty = congestion_penalty

    def route(self, qc: QuantumCircuit, seed: int = 42) -> QuantumCircuit:
        """Executa o roteamento de portas de 2 qubits sobre o chip ajustando os pesos das arestas."""
        random.seed(seed)
        np.random.seed(seed)

        edge_weights = {edge: 1.0 for edge in self.graph.edges()}
        routed_qc = QuantumCircuit(qc.num_qubits, qc.num_clbits)
        hardware_map = list(range(qc.num_qubits)) # Mapeamento lógico -> físico

        for inst in qc.data:
            if inst.operation.name == 'cx':
                q_log1, q_log2 = inst.qubits[0]._index, inst.qubits[1]._index
                q_phys1 = hardware_map[q_log1]
                q_phys2 = hardware_map[q_log2]

                # Se não forem vizinhos diretos no chip, calcula a rota ponderada
                if not self.graph.has_edge(q_phys1, q_phys2):
                    for u, v in self.graph.edges():
                        edge_key = (u, v) if (u, v) in edge_weights else (v, u)
                        self.graph[u][v]['weight'] = edge_weights.get(edge_key, 1.0)

                    path = nx.shortest_path(
                        self.graph, 
                        source=q_phys1, 
                        target=q_phys2, 
                        weight='weight'
                    )

                    # Insere portas SWAP ao longo da rota
                    for k in range(len(path) - 2):
                        u_node, v_node = path[k], path[k+1]
                        routed_qc.swap(u_node, v_node)

                        edge = (u_node, v_node) if (u_node, v_node) in edge_weights else (v_node, u_node)
                        edge_weights[edge] += self.congestion_penalty

                        hardware_map[q_log1] = v_node
                        q_phys1 = v_node

                routed_qc.cx(q_phys1, q_phys2)
            else:
                phys_qubits = [hardware_map[q._index] for q in inst.qubits]
                routed_qc.append(inst.operation, phys_qubits, inst.clbits)

        return routed_qc
        
