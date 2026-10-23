import networkx as nx
from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap

class InitialLayoutSelector:
    """Seletor de layout inicial baseado em correspondência de grafos de interação."""

    def __init__(self, coupling_map: CouplingMap):
        self.coupling_map = coupling_map
        self.hardware_graph = nx.Graph(list(coupling_map.get_edges()))

    def build_interaction_graph(self, qc: QuantumCircuit) -> nx.Graph:
        """Constrói um grafo ponderado onde o peso da aresta é o número de interações entre qubits."""
        interaction_graph = nx.Graph()
        for i in range(qc.num_qubits):
            interaction_graph.add_node(i)

        for inst in qc.data:
            if len(inst.qubits) == 2:
                q1, q2 = inst.qubits[0]._index, inst.qubits[1]._index
                if interaction_graph.has_edge(q1, q2):
                    interaction_graph[q1][q2]['weight'] += 1.0
                else:
                    interaction_graph.add_edge(q1, q2, weight=1.0)

        return interaction_graph

    def get_initial_layout(self, qc: QuantumCircuit) -> list[int]:
        """Associa qubits lógicos mais ativos aos qubits físicos mais conectados do chip."""
        interaction_graph = self.build_interaction_graph(qc)

        # Ordena qubits lógicos pela soma das frequências de interação
        logical_degrees = dict(interaction_graph.degree(weight='weight'))
        sorted_logical = sorted(logical_degrees.items(), key=lambda x: x[1], reverse=True)

        # Ordena qubits físicos pela centralidade de grau (número de vizinhos no chip)
        physical_degrees = dict(self.hardware_graph.degree())
        sorted_physical = sorted(physical_degrees.items(), key=lambda x: x[1], reverse=True)

        hardware_map = [0] * qc.num_qubits
        assigned_physical = set()

        # Mapeia os qubits lógicos mais críticos para as melhores posições físicas
        for log_q, _ in sorted_logical:
            for phys_q, _ in sorted_physical:
                if phys_q not in assigned_physical:
                    hardware_map[log_q] = phys_q
                    assigned_physical.add(phys_q)
                    break

        return hardware_map
      
