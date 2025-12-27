#!/usr/bin/env python3
"""
Intelligence Document Analyzer - Command Line Interface

Main entry point for document analysis, entity extraction, and graph visualization.
"""

import click
from pathlib import Path
import json
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from ingestion.document_processor import DocumentProcessor, DocumentChunk, DocumentMetadata
from extraction.spacy_extractor import SpacyEntityExtractor  # FREE local extractor
from graph.graph_builder import GraphBuilder

# Optional Claude extractor (only if user wants premium)
try:
    from extraction.entity_extractor import EntityExtractor as ClaudeEntityExtractor
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    🔍 Intelligence Document Analyzer

    AI-powered analysis of document dumps (PDFs, emails, scans) with
    entity extraction and interactive knowledge graph visualization.

    Examples:
      # Analyze a PDF file
      python cli.py analyze my_document.pdf

      # Analyze an entire directory
      python cli.py analyze data/raw/ --output my_analysis

      # Visualize existing graph
      python cli.py visualize data/graphs/my_analysis.graphml

      # Find connections between entities
      python cli.py query my_analysis.graphml "John Smith" "ACME Corp"
    """
    pass


@cli.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=str, help='Output name for graph (default: auto-generated)')
@click.option('--engine', type=click.Choice(['spacy', 'claude']), default='spacy', help='Extraction engine: spacy (FREE) or claude (premium, requires API key)')
@click.option('--api-key', type=str, envvar='ANTHROPIC_API_KEY', help='Anthropic API key (only needed if --engine=claude)')
@click.option('--model', type=str, default='claude-opus-4-5-20251101', help='Claude model to use (only if --engine=claude)')
@click.option('--confidence', type=float, default=0.7, help='Minimum confidence threshold (0-1)')
@click.option('--chunk-size', type=int, default=4000, help='Max characters per chunk')
@click.option('--format', type=click.Choice(['graphml', 'gexf', 'json']), default='json', help='Output format (json recommended)')
def analyze(input_path, output, engine, api_key, model, confidence, chunk_size, format):
    """
    Analyze documents and build knowledge graph

    INPUT_PATH can be a single file or directory of files.
    Supported formats: PDF, DOCX, TXT, EML
    """
    console.print("\n[bold cyan]🔍 Intelligence Document Analyzer[/bold cyan]\n")

    # Display extraction mode
    if engine == 'spacy':
        console.print("[bold green]🆓 Using FREE local extraction (spaCy)[/bold green]")
        console.print("[dim]No API costs, runs locally, 100% open-source[/dim]\n")
    else:
        console.print("[bold yellow]💰 Using premium extraction (Claude AI)[/bold yellow]")
        console.print("[dim]Requires API key and costs money per request[/dim]\n")

        # Validate API key for Claude
        if not api_key:
            console.print("[red]❌ Error: ANTHROPIC_API_KEY required for --engine=claude![/red]")
            console.print("Set it with: export ANTHROPIC_API_KEY=your_key")
            console.print("\n[cyan]TIP: Use --engine=spacy for FREE local extraction![/cyan]")
            sys.exit(1)

        # Check if Claude extractor is available
        if not CLAUDE_AVAILABLE:
            console.print("[red]❌ Error: Claude extractor not available![/red]")
            console.print("Install with: pip install anthropic")
            console.print("\n[cyan]TIP: Use --engine=spacy for FREE local extraction (no installation needed)![/cyan]")
            sys.exit(1)

    # Determine input files
    input_path = Path(input_path)
    if input_path.is_file():
        files = [input_path]
    else:
        # Scan directory for supported files
        extensions = ['.pdf', '.docx', '.txt', '.eml']
        files = [f for f in input_path.rglob('*') if f.suffix.lower() in extensions]

    if not files:
        console.print(f"[red]❌ No supported files found in {input_path}[/red]")
        sys.exit(1)

    console.print(f"[green]✓[/green] Found {len(files)} document(s) to process\n")

    # Initialize modules
    processor = DocumentProcessor(max_chunk_size=chunk_size)

    # Initialize appropriate extractor
    if engine == 'spacy':
        extractor = SpacyEntityExtractor(confidence_threshold=confidence)
    else:  # claude
        extractor = ClaudeEntityExtractor(api_key=api_key, model=model, confidence_threshold=confidence)

    graph_builder = GraphBuilder(graph_name=output or "analysis")

    total_entities = 0
    total_relationships = 0

    # Process each file
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        for file_path in files:
            task = progress.add_task(f"Processing {file_path.name}...", total=None)

            try:
                # Step 1: Ingest document
                progress.update(task, description=f"[cyan]📄 Ingesting {file_path.name}...[/cyan]")
                chunks, metadata = processor.process_file(str(file_path))

                # Step 2: Extract entities
                progress.update(task, description=f"[magenta]🤖 Extracting entities from {file_path.name}...[/magenta]")
                entities, relationships = extractor.extract_from_document(chunks, metadata.to_dict())

                # Step 3: Build graph
                progress.update(task, description=f"[yellow]📊 Building graph from {file_path.name}...[/yellow]")

                # Add entities
                for entity in entities:
                    graph_builder.add_entity(entity.to_dict())

                # Add relationships
                for relationship in relationships:
                    graph_builder.add_relationship(relationship.to_dict())

                total_entities += len(entities)
                total_relationships += len(relationships)

                progress.update(task, description=f"[green]✓ Completed {file_path.name}[/green]")

            except Exception as e:
                progress.update(task, description=f"[red]❌ Failed: {file_path.name} - {str(e)}[/red]")
                console.print(f"[red]Error processing {file_path.name}: {e}[/red]")

    # Display results
    console.print(f"\n[bold green]🎉 Analysis Complete![/bold green]\n")

    stats = graph_builder.get_statistics()

    table = Table(title="Knowledge Graph Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")

    table.add_row("Total Documents", str(len(files)))
    table.add_row("Total Entities", str(stats.total_nodes))
    table.add_row("Total Relationships", str(stats.total_edges))
    table.add_row("Connected Components", str(stats.connected_components))
    table.add_row("Graph Density", f"{stats.density:.4f}")
    table.add_row("Average Degree", f"{stats.avg_degree:.2f}")

    console.print(table)

    # Entity types breakdown
    console.print("\n[bold]Entity Types:[/bold]")
    for entity_type, count in sorted(stats.node_types.items(), key=lambda x: x[1], reverse=True):
        console.print(f"  [cyan]{entity_type}[/cyan]: {count}")

    # Relationship types breakdown
    console.print("\n[bold]Relationship Types:[/bold]")
    for rel_type, count in sorted(stats.relationship_types.items(), key=lambda x: x[1], reverse=True):
        console.print(f"  [magenta]{rel_type}[/magenta]: {count}")

    # Save graph
    output_name = output or f"analysis_{len(files)}_docs"
    output_path = Path(f"data/graphs/{output_name}.{format}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    graph_builder.save(str(output_path), format=format)
    console.print(f"\n[green]✓ Graph saved to:[/green] {output_path}")

    # Also save as PNG visualization
    viz_path = output_path.with_suffix('.png')
    console.print(f"[cyan]📊 Creating visualization...[/cyan]")
    try:
        graph_builder.visualize(output_path=str(viz_path), layout='spring')
        console.print(f"[green]✓ Visualization saved to:[/green] {viz_path}\n")
    except Exception as e:
        console.print(f"[yellow]⚠ Visualization failed: {e}[/yellow]\n")


@cli.command()
@click.argument('graph_path', type=click.Path(exists=True))
@click.option('--layout', type=click.Choice(['spring', 'circular', 'kamada_kawai']), default='spring')
@click.option('--output', '-o', type=str, help='Output image path')
def visualize(graph_path, layout, output):
    """
    Visualize an existing knowledge graph

    GRAPH_PATH: Path to graph file (.graphml, .gexf, or .json)
    """
    console.print(f"\n[cyan]📊 Loading graph from {graph_path}...[/cyan]")

    # Determine format from extension
    format_map = {'.graphml': 'graphml', '.gexf': 'gexf', '.json': 'json'}
    suffix = Path(graph_path).suffix
    format = format_map.get(suffix, 'graphml')

    # Load graph
    builder = GraphBuilder.load(graph_path, format=format)

    # Display stats
    stats = builder.get_statistics()
    console.print(f"[green]✓ Loaded graph with {stats.total_nodes} entities and {stats.total_edges} relationships[/green]\n")

    # Create visualization
    output_path = output or str(Path(graph_path).with_suffix('.png'))

    console.print(f"[cyan]Creating visualization with '{layout}' layout...[/cyan]")
    builder.visualize(output_path=output_path, layout=layout)
    console.print(f"[green]✓ Saved visualization to {output_path}[/green]\n")


@cli.command()
@click.argument('graph_path', type=click.Path(exists=True))
@click.argument('entity1', type=str)
@click.argument('entity2', type=str)
def query(graph_path, entity1, entity2):
    """
    Find shortest path between two entities (6 degrees of separation)

    Example:
      python cli.py query my_graph.graphml "John Smith" "ACME Corp"
    """
    console.print(f"\n[cyan]🔍 Loading graph...[/cyan]")

    # Determine format
    suffix = Path(graph_path).suffix
    format_map = {'.graphml': 'graphml', '.gexf': 'gexf', '.json': 'json'}
    format = format_map.get(suffix, 'graphml')

    builder = GraphBuilder.load(graph_path, format=format)
    console.print(f"[green]✓ Loaded graph[/green]\n")

    # Find path
    console.print(f"[cyan]Finding connection between:[/cyan]")
    console.print(f"  [bold]{entity1}[/bold] → [bold]{entity2}[/bold]\n")

    path = builder.shortest_path(entity1, entity2)

    if path:
        console.print(f"[green]✓ Found path with {len(path)-1} degrees of separation:[/green]\n")

        for i in range(len(path)):
            node_id = path[i]
            node_data = builder.graph.nodes[node_id]
            entity_text = node_data['text']
            entity_type = node_data['entity_type']

            console.print(f"  {i+1}. [{entity_type}] {entity_text}")

            # Show relationship to next entity
            if i < len(path) - 1:
                next_node = path[i+1]
                # Get edge data
                edges = builder.graph.get_edge_data(node_id, next_node)
                if edges:
                    # Get first relationship (could be multiple)
                    rel_data = list(edges.values())[0]
                    rel_type = rel_data.get('relationship_type', 'connected_to')
                    evidence = rel_data.get('evidence', '')
                    console.print(f"     ↓ [magenta]{rel_type}[/magenta]")
                    if evidence:
                        console.print(f"     [dim]\"{evidence[:80]}...\"[/dim]")

        console.print()
    else:
        console.print(f"[red]❌ No path found between these entities[/red]\n")


@cli.command()
@click.argument('graph_path', type=click.Path(exists=True))
@click.option('--algorithm', type=click.Choice(['degree', 'betweenness', 'closeness']), default='degree')
@click.option('--top', type=int, default=20, help='Number of top entities to show')
def centrality(graph_path, algorithm, top):
    """
    Calculate and display entity centrality scores

    Shows which entities are most "central" or important in the network.
    """
    console.print(f"\n[cyan]📊 Loading graph...[/cyan]")

    suffix = Path(graph_path).suffix
    format_map = {'.graphml': 'graphml', '.gexf': 'gexf', '.json': 'json'}
    format = format_map.get(suffix, 'graphml')

    builder = GraphBuilder.load(graph_path, format=format)
    console.print(f"[green]✓ Loaded graph[/green]\n")

    console.print(f"[cyan]Calculating {algorithm} centrality...[/cyan]")
    scores = builder.calculate_centrality(algorithm=algorithm)

    # Sort by score
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top]

    table = Table(title=f"Top {top} Entities by {algorithm.title()} Centrality")
    table.add_column("Rank", style="cyan", justify="right")
    table.add_column("Entity", style="bold")
    table.add_column("Type", style="green")
    table.add_column("Score", style="magenta", justify="right")

    for i, (node_id, score) in enumerate(sorted_scores, 1):
        node_data = builder.graph.nodes[node_id]
        entity_text = node_data['text']
        entity_type = node_data['entity_type']
        table.add_row(str(i), entity_text, entity_type, f"{score:.4f}")

    console.print(table)
    console.print()


@cli.command()
@click.argument('graph_path', type=click.Path(exists=True))
def communities(graph_path):
    """
    Detect and display communities/clusters in the network
    """
    console.print(f"\n[cyan]🔍 Loading graph...[/cyan]")

    suffix = Path(graph_path).suffix
    format_map = {'.graphml': 'graphml', '.gexf': 'gexf', '.json': 'json'}
    format = format_map.get(suffix, 'graphml')

    builder = GraphBuilder.load(graph_path, format=format)
    console.print(f"[green]✓ Loaded graph[/green]\n")

    console.print(f"[cyan]Detecting communities...[/cyan]")
    communities_list = builder.detect_communities()

    console.print(f"[green]✓ Found {len(communities_list)} communities[/green]\n")

    # Show top 10 largest communities
    sorted_communities = sorted(communities_list, key=len, reverse=True)[:10]

    for i, community in enumerate(sorted_communities, 1):
        console.print(f"[bold cyan]Community {i}[/bold cyan] ({len(community)} members):")

        # Show first 10 members
        members = list(community)[:10]
        for node_id in members:
            node_data = builder.graph.nodes[node_id]
            entity_text = node_data['text']
            entity_type = node_data['entity_type']
            console.print(f"  - [{entity_type}] {entity_text}")

        if len(community) > 10:
            console.print(f"  ... and {len(community) - 10} more")
        console.print()


if __name__ == "__main__":
    cli()
