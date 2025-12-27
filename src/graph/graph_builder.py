"""
Graph Database Layer - NetworkX Implementation

Builds and manages knowledge graphs from extracted entities and relationships.
"""

import networkx as nx
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import matplotlib.pyplot as plt
from datetime import datetime


@dataclass
class GraphStats:
    """Statistics about the knowledge graph"""
    total_nodes: int
    total_edges: int
    node_types: Dict[str, int]
    relationship_types: Dict[str, int]
    avg_degree: float
    density: float
    connected_components: int
    largest_component_size: int


class GraphBuilder:
    """
    Build and analyze knowledge graphs from entities and relationships

    Features:
    - NetworkX-based graph storage
    - Entity and relationship addition with validation
    - Graph algorithms (shortest path, centrality, communities)
    - Export to multiple formats (GraphML, GEXF, JSON)
    - Graph statistics and analysis
    - Visualization support
    """

    def __init__(self, graph_name: str = "knowledge_graph"):
        """
        Initialize graph builder

        Args:
            graph_name: Name for the graph
        """
        self.graph_name = graph_name
        self.graph = nx.MultiDiGraph()  # Directed graph with multiple edges allowed
        self.entity_index = {}  # Fast lookup: entity_text -> node_id
        self.created_date = datetime.now().isoformat()

    def add_entity(self, entity: Dict) -> str:
        """
        Add entity as a node in the graph

        Args:
            entity: Entity dict with keys: id, type, text, confidence, etc.

        Returns:
            Node ID in graph
        """
        node_id = entity['id']

        # Add node with all entity attributes
        self.graph.add_node(
            node_id,
            entity_type=entity['type'],
            text=entity['text'],
            confidence=entity['confidence'],
            source_document=entity.get('source_document', ''),
            page_number=entity.get('page_number'),
            metadata=entity.get('metadata', {})
        )

        # Index for lookup
        key = (entity['text'].lower(), entity['type'])
        self.entity_index[key] = node_id

        return node_id

    def add_entities_batch(self, entities: List[Dict]) -> List[str]:
        """
        Add multiple entities at once

        Args:
            entities: List of entity dicts

        Returns:
            List of node IDs added
        """
        node_ids = []
        for entity in entities:
            node_id = self.add_entity(entity)
            node_ids.append(node_id)
        return node_ids

    def add_relationship(self, relationship: Dict) -> bool:
        """
        Add relationship as an edge in the graph

        Args:
            relationship: Relationship dict with keys: source_id, target_id, relationship_type, etc.

        Returns:
            True if added successfully, False otherwise
        """
        source_id = relationship['source_id']
        target_id = relationship['target_id']

        # Validate that both nodes exist
        if source_id not in self.graph.nodes or target_id not in self.graph.nodes:
            print(f"Warning: Skipping relationship - nodes not found: {source_id} -> {target_id}")
            return False

        # Add edge with relationship attributes
        self.graph.add_edge(
            source_id,
            target_id,
            relationship_type=relationship['relationship_type'],
            confidence=relationship['confidence'],
            evidence=relationship.get('evidence', ''),
            source_document=relationship.get('source_document', ''),
            page_number=relationship.get('page_number'),
            metadata=relationship.get('metadata', {})
        )

        return True

    def add_relationships_batch(self, relationships: List[Dict]) -> int:
        """
        Add multiple relationships at once

        Args:
            relationships: List of relationship dicts

        Returns:
            Number of relationships successfully added
        """
        added_count = 0
        for relationship in relationships:
            if self.add_relationship(relationship):
                added_count += 1
        return added_count

    def merge_entities(self, entity_id_1: str, entity_id_2: str, keep_id: Optional[str] = None) -> str:
        """
        Merge two entities (e.g., "John Smith" and "J. Smith" are same person)

        Args:
            entity_id_1: First entity ID
            entity_id_2: Second entity ID
            keep_id: Which ID to keep (default: entity_id_1)

        Returns:
            ID of merged entity
        """
        if entity_id_1 not in self.graph.nodes or entity_id_2 not in self.graph.nodes:
            raise ValueError("Both entities must exist in graph")

        keep_id = keep_id or entity_id_1
        remove_id = entity_id_2 if keep_id == entity_id_1 else entity_id_1

        # Redirect all edges from remove_id to keep_id
        # Incoming edges
        for source, _, edge_data in self.graph.in_edges(remove_id, data=True):
            self.graph.add_edge(source, keep_id, **edge_data)

        # Outgoing edges
        for _, target, edge_data in self.graph.out_edges(remove_id, data=True):
            self.graph.add_edge(keep_id, target, **edge_data)

        # Merge metadata (combine mentions, etc.)
        kept_node = self.graph.nodes[keep_id]
        removed_node = self.graph.nodes[remove_id]

        # Update metadata
        if 'merged_from' not in kept_node:
            kept_node['merged_from'] = []
        kept_node['merged_from'].append(remove_id)

        # Remove the duplicate node
        self.graph.remove_node(remove_id)

        return keep_id

    def find_entity(self, text: str, entity_type: Optional[str] = None) -> Optional[str]:
        """
        Find entity node ID by text (case-insensitive)

        Args:
            text: Entity text to search for
            entity_type: Optional entity type filter

        Returns:
            Node ID if found, None otherwise
        """
        if entity_type:
            key = (text.lower(), entity_type)
            return self.entity_index.get(key)
        else:
            # Search all types
            for (entity_text, etype), node_id in self.entity_index.items():
                if entity_text == text.lower():
                    return node_id
        return None

    def shortest_path(self, entity_1: str, entity_2: str) -> Optional[List[str]]:
        """
        Find shortest path between two entities (6 degrees of separation)

        Args:
            entity_1: First entity text or ID
            entity_2: Second entity text or ID

        Returns:
            List of node IDs in path, or None if no path exists
        """
        # Convert text to IDs if needed
        if entity_1 not in self.graph.nodes:
            entity_1 = self.find_entity(entity_1)
        if entity_2 not in self.graph.nodes:
            entity_2 = self.find_entity(entity_2)

        if not entity_1 or not entity_2:
            return None

        try:
            # Use underlying undirected graph for path finding
            undirected = self.graph.to_undirected()
            path = nx.shortest_path(undirected, entity_1, entity_2)
            return path
        except nx.NetworkXNoPath:
            return None

    def get_neighbors(self, entity_id: str, depth: int = 1) -> Set[str]:
        """
        Get all neighbors of an entity up to given depth

        Args:
            entity_id: Entity node ID
            depth: How many hops to explore (default: 1 = direct neighbors)

        Returns:
            Set of neighbor node IDs
        """
        if entity_id not in self.graph.nodes:
            return set()

        neighbors = set()
        current_level = {entity_id}

        for _ in range(depth):
            next_level = set()
            for node in current_level:
                # Get both incoming and outgoing neighbors
                next_level.update(self.graph.successors(node))
                next_level.update(self.graph.predecessors(node))
            neighbors.update(next_level)
            current_level = next_level

        neighbors.discard(entity_id)  # Remove the original entity
        return neighbors

    def calculate_centrality(self, algorithm: str = "degree") -> Dict[str, float]:
        """
        Calculate centrality scores for all nodes

        Args:
            algorithm: "degree", "betweenness", "closeness", or "eigenvector"

        Returns:
            Dict mapping node_id -> centrality score
        """
        if algorithm == "degree":
            return dict(self.graph.degree())
        elif algorithm == "betweenness":
            return nx.betweenness_centrality(self.graph)
        elif algorithm == "closeness":
            return nx.closeness_centrality(self.graph)
        elif algorithm == "eigenvector":
            try:
                return nx.eigenvector_centrality(self.graph, max_iter=1000)
            except:
                return {}
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

    def detect_communities(self) -> List[Set[str]]:
        """
        Detect communities/clusters in the graph

        Returns:
            List of sets, each set contains node IDs in a community
        """
        # Convert to undirected for community detection
        undirected = self.graph.to_undirected()

        # Use Louvain algorithm
        try:
            from networkx.algorithms import community
            communities = community.greedy_modularity_communities(undirected)
            return [set(c) for c in communities]
        except ImportError:
            # Fallback: connected components
            components = nx.connected_components(undirected)
            return [set(c) for c in components]

    def get_subgraph(self, node_ids: List[str]) -> 'GraphBuilder':
        """
        Extract subgraph containing only specified nodes

        Args:
            node_ids: List of node IDs to include

        Returns:
            New GraphBuilder with subgraph
        """
        subgraph_builder = GraphBuilder(graph_name=f"{self.graph_name}_subgraph")
        subgraph_builder.graph = self.graph.subgraph(node_ids).copy()
        return subgraph_builder

    def get_statistics(self) -> GraphStats:
        """Calculate and return graph statistics"""
        node_types = {}
        for node, data in self.graph.nodes(data=True):
            entity_type = data.get('entity_type', 'UNKNOWN')
            node_types[entity_type] = node_types.get(entity_type, 0) + 1

        relationship_types = {}
        for _, _, data in self.graph.edges(data=True):
            rel_type = data.get('relationship_type', 'unknown')
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1

        # Calculate metrics
        num_nodes = self.graph.number_of_nodes()
        num_edges = self.graph.number_of_edges()

        avg_degree = sum(dict(self.graph.degree()).values()) / num_nodes if num_nodes > 0 else 0
        density = nx.density(self.graph)

        # Connected components (use undirected)
        undirected = self.graph.to_undirected()
        components = list(nx.connected_components(undirected))
        num_components = len(components)
        largest_component = max(len(c) for c in components) if components else 0

        return GraphStats(
            total_nodes=num_nodes,
            total_edges=num_edges,
            node_types=node_types,
            relationship_types=relationship_types,
            avg_degree=avg_degree,
            density=density,
            connected_components=num_components,
            largest_component_size=largest_component
        )

    def save(self, output_path: str, format: str = "graphml"):
        """
        Save graph to file

        Args:
            output_path: Path to save file
            format: "graphml", "gexf", "json", or "pickle"
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "graphml":
            nx.write_graphml(self.graph, output_path)
        elif format == "gexf":
            nx.write_gexf(self.graph, output_path)
        elif format == "json":
            from networkx.readwrite import json_graph
            data = json_graph.node_link_data(self.graph)
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
        elif format == "pickle":
            nx.write_gpickle(self.graph, output_path)
        else:
            raise ValueError(f"Unknown format: {format}")

        print(f"✓ Graph saved to {output_path}")

    @classmethod
    def load(cls, input_path: str, format: str = "graphml") -> 'GraphBuilder':
        """
        Load graph from file

        Args:
            input_path: Path to graph file
            format: "graphml", "gexf", "json", or "pickle"

        Returns:
            GraphBuilder instance with loaded graph
        """
        builder = cls()

        if format == "graphml":
            builder.graph = nx.read_graphml(input_path)
        elif format == "gexf":
            builder.graph = nx.read_gexf(input_path)
        elif format == "json":
            from networkx.readwrite import json_graph
            with open(input_path, 'r') as f:
                data = json.load(f)
            builder.graph = json_graph.node_link_graph(data)
        elif format == "pickle":
            builder.graph = nx.read_gpickle(input_path)
        else:
            raise ValueError(f"Unknown format: {format}")

        # Rebuild entity index
        for node, data in builder.graph.nodes(data=True):
            text = data.get('text', '')
            entity_type = data.get('entity_type', 'UNKNOWN')
            key = (text.lower(), entity_type)
            builder.entity_index[key] = node

        print(f"✓ Graph loaded from {input_path}")
        return builder

    def visualize(self, output_path: Optional[str] = None, layout: str = "spring"):
        """
        Create a visualization of the graph

        Args:
            output_path: Path to save image (if None, displays instead)
            layout: "spring", "circular", "kamada_kawai", or "shell"
        """
        plt.figure(figsize=(16, 12))

        # Choose layout algorithm
        if layout == "spring":
            pos = nx.spring_layout(self.graph, k=0.5, iterations=50)
        elif layout == "circular":
            pos = nx.circular_layout(self.graph)
        elif layout == "kamada_kawai":
            pos = nx.kamada_kawai_layout(self.graph)
        elif layout == "shell":
            pos = nx.shell_layout(self.graph)
        else:
            pos = nx.spring_layout(self.graph)

        # Color nodes by type
        node_colors = []
        color_map = {
            'PERSON': '#FF6B6B',
            'ORGANIZATION': '#4ECDC4',
            'LOCATION': '#45B7D1',
            'EVENT': '#FFA07A',
            'DATE': '#98D8C8',
            'DOCUMENT': '#F7DC6F',
            'PHONE': '#BB8FCE',
            'EMAIL': '#85C1E2',
            'MONEY': '#52BE80',
            'LEGAL': '#F8B739'
        }

        for node in self.graph.nodes():
            entity_type = self.graph.nodes[node].get('entity_type', 'UNKNOWN')
            node_colors.append(color_map.get(entity_type, '#CCCCCC'))

        # Draw graph
        nx.draw_networkx_nodes(self.graph, pos, node_color=node_colors, node_size=300, alpha=0.9)
        nx.draw_networkx_edges(self.graph, pos, alpha=0.3, arrows=True, arrowsize=10)

        # Draw labels (only for high-degree nodes to avoid clutter)
        degrees = dict(self.graph.degree())
        threshold = sorted(degrees.values(), reverse=True)[min(30, len(degrees)-1)] if degrees else 0
        labels = {node: self.graph.nodes[node]['text']
                 for node, degree in degrees.items() if degree >= threshold}
        nx.draw_networkx_labels(self.graph, pos, labels, font_size=8)

        plt.title(f"{self.graph_name} - {self.graph.number_of_nodes()} entities, {self.graph.number_of_edges()} relationships", fontsize=16)
        plt.axis('off')
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"✓ Visualization saved to {output_path}")
        else:
            plt.show()


# Example usage
if __name__ == "__main__":
    # Create example graph
    builder = GraphBuilder("example_intelligence_graph")

    # Add entities
    entities = [
        {"id": "e_001", "type": "PERSON", "text": "John Smith", "confidence": 0.95},
        {"id": "e_002", "type": "ORGANIZATION", "text": "ACME Corp", "confidence": 0.92},
        {"id": "e_003", "type": "LOCATION", "text": "New York", "confidence": 0.98},
        {"id": "e_004", "type": "PERSON", "text": "Jane Doe", "confidence": 0.94},
    ]
    builder.add_entities_batch(entities)

    # Add relationships
    relationships = [
        {"source_id": "e_001", "target_id": "e_002", "relationship_type": "works_at", "confidence": 0.90, "evidence": "John Smith is CEO of ACME Corp"},
        {"source_id": "e_002", "target_id": "e_003", "relationship_type": "located_in", "confidence": 0.88, "evidence": "ACME Corp headquarters in New York"},
        {"source_id": "e_004", "target_id": "e_002", "relationship_type": "employed_by", "confidence": 0.85, "evidence": "Jane Doe works at ACME Corp"},
    ]
    builder.add_relationships_batch(relationships)

    # Get statistics
    stats = builder.get_statistics()
    print(f"\nGraph Statistics:")
    print(f"  Nodes: {stats.total_nodes}")
    print(f"  Edges: {stats.total_edges}")
    print(f"  Entity types: {stats.node_types}")
    print(f"  Relationship types: {stats.relationship_types}")

    # Find path
    path = builder.shortest_path("John Smith", "Jane Doe")
    print(f"\nShortest path: {path}")

    # Save graph
    # builder.save("data/graphs/example.graphml")
