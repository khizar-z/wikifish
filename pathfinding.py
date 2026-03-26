from graph import Graph

def jaccard_heuristic(current: int, target: int, categories: dict[int, set[str]]) -> float:
    current_cats = categories[current]
    target_cats = categories[target]

    if not current_cats or not target_cats:
        return 1.0

    # Jaccard similarity: size of intersection / size of union
    overlap = len(current_cats & target_cats) / len(current_cats | target_cats)
    return 1.0 - overlap  # invert so that closer = lower cost

def astar(graph: Graph, source: str, target: str, categories: dict[int, set[str]]) -> list[str]:
    pass

