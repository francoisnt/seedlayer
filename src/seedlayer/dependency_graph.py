from collections import deque
from typing import (
    Dict,
    List,
    Optional,
    Set,
    TypeAlias,
)

GraphType: TypeAlias = Dict[str, Set[str]]


class DependencyGraph:
    def __init__(self) -> None:
        self._graph: GraphType = {}

    def add(self, node: str, dependencies: Optional[Set[str]] = None) -> None:
        """Add a node with its dependencies."""
        if dependencies is None:
            dependencies = set()
        if node not in self._graph:
            self._graph[node] = set()

        self._graph[node].update(dependencies)

    def topological_sort(self) -> List[str]:
        graph = self._graph

        # 1. Ensure every dependency also appears as a key
        all_nodes = set(graph)
        for deps in graph.values():
            all_nodes.update(deps)
        graph = {n: set(graph.get(n, ())) for n in all_nodes}

        # 2. Compute reverse edges & incoming-edge counts
        incoming = {n: 0 for n in all_nodes}
        reverse: GraphType = {n: set() for n in all_nodes}
        for node, deps in graph.items():
            for d in deps:
                reverse[d].add(node)
                incoming[node] += 1

        # 3. Kahn’s algorithm
        queue = deque(n for n, deg in incoming.items() if deg == 0)
        order: List[str] = []

        while queue:
            n = queue.popleft()
            order.append(n)
            for m in reverse[n]:
                incoming[m] -= 1
                if incoming[m] == 0:
                    queue.append(m)

        if len(order) != len(all_nodes):
            cycles = [n for n in all_nodes if incoming[n] != 0]
            raise ValueError(f"Cycle detected in dependency graph involving nodes: {cycles}")

        return order

    def __repr__(self) -> str:
        return f"DependencyGraph({self._graph})"
