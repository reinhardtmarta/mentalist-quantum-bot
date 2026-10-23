from collections import deque
from itertools import combinations

import networkx as nx
from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap


class InitialLayoutSelector:
    """Seletor de layout inicial com busca de subgrafo contíguo

    (Contiguous Subgraph Isolation / Isolamento de Subgrafo Contíguo).
    """

    def __init__(self, coupling_map: CouplingMap):
        self.coupling_map = coupling_map
        self.hardware_graph = nx.Graph(list(coupling_map.get_edges()))

    def _find_compact_subgraph(self, num_qubits: int) -> list[int]:
        """Encontra uma região compacta e contínua de N qubits físicos no chip."""
        best_nodes = []
        min_total_dist = float("inf")

        for root in self.hardware_graph.nodes():
            # Executa BFS para coletar N qubits vizinhos
            visited = []
            queue = deque([root])
            seen = {root}

            while queue and len(visited) < num_qubits:
                curr = queue.popleft()
                visited.append(curr)
                for neighbor in self.hardware_graph.neighbors(curr):
                    if neighbor not in seen:
                        seen.add(neighbor)
                        queue.append(neighbor)

            if len(visited) == num_qubits:
                subgraph = self.hardware_graph.subgraph(visited)
                if nx.is_connected(subgraph):
                    total_dist = sum(
                        nx.shortest_path_length(subgraph, u, v)
                        for u, v in combinations(visited, 2)
                    )
                    if total_dist < min_total_dist:
                        min_total_dist = total_dist
                        best_nodes = visited

        return best_nodes if best_nodes else list(range(num_qubits))

    def build_interaction_graph(self, qc: QuantumCircuit) -> nx.Graph:
        """Constrói o grafo de interação ponderado do circuito."""
        interaction_graph = nx.Graph()
        for i in range(qc.num_qubits):
            interaction_graph.add_node(i)

        for inst in qc.data:
            if len(inst.qubits) == 2:
                q1, q2 = inst.qubits[0]._index, inst.qubits[1]._index
                if interaction_graph.has_edge(q1, q2):
                    interaction_graph[q1][q2]["weight"] += 1.0
                else:
                    interaction_graph.add_edge(q1, q2, weight=1.0)

        return interaction_graph

    def get_initial_layout(self, qc: QuantumCircuit) -> list[int]:
        """Mapeia os qubits lógicos estritamente dentro do subgrafo físico mais compacto."""
        n_qubits = qc.num_qubits

        # 1. Isola um subgrafo contíguo no chip
        compact_physical_nodes = self._find_compact_subgraph(n_qubits)
        sub_hardware_graph = self.hardware_graph.subgraph(compact_physical_nodes)

        # 2. Constrói o grafo de interações lógicas
        interaction_graph = self.build_interaction_graph(qc)

        logical_degrees = dict(interaction_graph.degree(weight="weight"))
        sorted_logical = sorted(
            logical_degrees.items(), key=lambda item: item[1], reverse=True
        )

        physical_degrees = dict(sub_hardware_graph.degree())
        sorted_physical = sorted(
            physical_degrees.items(), key=lambda item: item[1], reverse=True
        )

        hardware_map = [0] * n_qubits
        assigned_physical = set()

        # 3. Mapeia os qubits lógicos apenas dentro dos nós do subgrafo isolado
        for log_q, _ in sorted_logical:
            for phys_q, _ in sorted_physical:
                if phys_q not in assigned_physical:
                    hardware_map[log_q] = phys_q
                    assigned_physical.add(phys_q)
                    break

        return hardware_map
