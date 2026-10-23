import networkx as nx
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT
from qiskit.transpiler import CouplingMap
from src.bot import MentalistBot

def run_benchmark():
    # 1. Hardware de Teste (Grade Quadrada 4x4 - 16 Qubits)
    grid = nx.grid_2d_graph(4, 4)
    nodes_map = {node: i for i, node in enumerate(grid.nodes())}
    grid = nx.relabel_nodes(grid, nodes_map)
    coupling_map = CouplingMap(list(grid.edges()))

    # 2. Circuito de Teste Estruturado (QFT de 16 Qubits)
    qc = QFT(num_qubits=16).decompose()

    print("=== CIRCUITO DE ENTRADA (QFT 16 Qubits) ===")
    print(f"Instruções Lógicas: {len(qc.data)} | Profundidade: {qc.depth()}\n")

    # 3. Execução do Mentalist Bot (com Negociação Bidirecional de Fronteira)
    bot = MentalistBot(
        coupling_map=coupling_map, 
        congestion_penalty=0.3, 
        window_size=20
    )
    optimized_qc = bot.optimize(qc, iterations=10, top_k=3)

    swaps = optimized_qc.count_ops().get('swap', 0)

    print("=== RESULTADO: MENTALIST BOT (NEGOCIAÇÃO DE FRONTEIRA) ===")
    print(f"SWAPs Inseridas: {swaps}")
    print(f"Instruções Finais: {len(optimized_qc.data)}")
    print(f"Profundidade Final: {optimized_qc.depth()}")

if __name__ == "__main__":
    run_benchmark()
    
