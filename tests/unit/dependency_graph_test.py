import pytest

from seedlayer.dependency_graph import DependencyGraph


@pytest.fixture
def graph() -> DependencyGraph:
    """Set up a fresh DependencyGraph instance for each test."""
    return DependencyGraph()


def test_add_node_no_dependencies(graph: DependencyGraph) -> None:
    """Test adding a node with no dependencies."""
    graph.add("A")
    assert graph._graph == {"A": set()}


def test_add_node_with_dependencies(graph: DependencyGraph) -> None:
    """Test adding a node with dependencies."""
    graph.add("A", {"B", "C"})
    assert graph._graph == {"A": {"B", "C"}}


def test_add_same_node_multiple_times(graph: DependencyGraph) -> None:
    """Test adding the same node multiple times updates dependencies."""
    graph.add("A", {"B"})
    graph.add("A", {"C"})
    assert graph._graph == {"A": {"B", "C"}}


def test_topological_sort_empty_graph(graph: DependencyGraph) -> None:
    """Test topological sort on an empty graph."""
    result = graph.topological_sort()
    assert result == []


def test_topological_sort_single_node(graph: DependencyGraph) -> None:
    """Test topological sort with a single node."""
    graph.add("A")
    result = graph.topological_sort()
    assert result == ["A"]


def test_topological_sort_linear_graph(graph: DependencyGraph) -> None:
    """Test topological sort on a linear graph (A -> B -> C)."""
    graph.add("A", {"B"})
    graph.add("B", {"C"})
    graph.add("C")
    result = graph.topological_sort()
    assert result == ["C", "B", "A"]


def test_topological_sort_tree_graph(graph: DependencyGraph) -> None:
    """Test topological sort on a tree-like graph (A -> {B, C})."""
    graph.add("A", {"B", "C"})
    graph.add("B")
    graph.add("C")
    result = graph.topological_sort()
    # Either B or C can come first, but A must be last
    assert result[-1] == "A"
    assert set(result[:2]) == {"B", "C"}


def test_topological_sort_disconnected_components(graph: DependencyGraph) -> None:
    """Test topological sort with disconnected components."""
    graph.add("A", {"B"})
    graph.add("B")
    graph.add("C", {"D"})
    graph.add("D")
    result = graph.topological_sort()
    # Check that B comes before A and D before C
    assert result.index("B") < result.index("A")
    assert result.index("D") < result.index("C")


def test_topological_sort_dependency_only_node(graph: DependencyGraph) -> None:
    """Test topological sort when a node only appears as a dependency."""
    graph.add("A", {"B"})  # B is a dependency but not a key
    result = graph.topological_sort()
    assert set(result) == {"A", "B"}
    assert result.index("B") < result.index("A")


def test_topological_sort_direct_cycle(graph: DependencyGraph) -> None:
    """Test topological sort with a direct cycle (A -> B -> A)."""
    graph.add("A", {"B"})
    graph.add("B", {"A"})
    with pytest.raises(ValueError):
        graph.topological_sort()


def test_topological_sort_indirect_cycle(graph: DependencyGraph) -> None:
    """Test topological sort with an indirect cycle (A -> B -> C -> A)."""
    graph.add("A", {"B"})
    graph.add("B", {"C"})
    graph.add("C", {"A"})
    with pytest.raises(ValueError):
        graph.topological_sort()


def test_topological_sort_complex_graph(graph: DependencyGraph) -> None:
    """Test topological sort on a complex graph with multiple dependencies."""
    graph.add("A", {"B", "C"})
    graph.add("B", {"D"})
    graph.add("C", {"D", "E"})
    graph.add("D", {"E"})
    graph.add("E")
    result = graph.topological_sort()
    # Validate order: E before D, D before B and C, B and C before A
    assert result.index("E") < result.index("D")
    assert result.index("D") < result.index("B")
    assert result.index("D") < result.index("C")
    assert result.index("B") < result.index("A")
    assert result.index("C") < result.index("A")
    assert set(result) == {"A", "B", "C", "D", "E"}
