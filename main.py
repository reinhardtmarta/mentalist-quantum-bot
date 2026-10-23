import networkx as nx
import numpy as np
from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap
from src.bot import MentalistBot

def run_benchmark():
    # 1. Configuração do chip físico (Grade Quadrada 4x4 - 16 Qubits)
    grid = nx.grid_2d_graph(4, 4)
    nodes_map = {node: i for i, node in enumerate(grid.nodes())}
    grid = nx.relabel_nodes(grid, nodes_map)
    coupling_map = CouplingMap(list(grid.edges()))

    # 2. Criação do circuito bruto com redundâncias e conexões distantes
    qc = QuantumCircuit(16)
    np.random.seed(42)

    # Inserindo portas autoinversas para teste do rewriter
    qc.h(0)
    qc.h(0)

    # Inserindo 30 portas CNOT aleatórias
    for _ in range(30):
        q1, q2 = np.random.choice(16, size=2, replace=False)
        qc.cx(q1, q2)

    print("=== CIRCUITO DE ENTRADA ===")
    print(f"Instruções: {len(qc.data)} | Profundidade: {qc.depth()}\n")

    # 3. Execução do Mentalist Bot
    bot = MentalistBot(coupling_map=coupling_map, congestion_penalty=0.8)
    optimized_qc = bot.optimize(qc, iterations=25)

    swaps = optimized_qc.count_ops().get('swap', 0)

    print("=== RESULTADO MENTALIST BOT ===")
    print(f"SWAPs Inseridas: {swaps}")
    print(f"Instruções Finais: {len(optimized_qc.data)}")
    print(f"Profundidade Final: {optimized_qc.depth()}")

if __name__ == "__main__":
    run_benchmark()
  
