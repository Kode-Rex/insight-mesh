#!/usr/bin/env python3
"""
Query Neo4j to explore available data
"""

import os
from neo4j import GraphDatabase
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import json

console = Console()

def connect_neo4j():
    """Connect to Neo4j database"""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        # Test connection
        with driver.session() as session:
            session.run("RETURN 1")
        console.print(f"[green]✓ Connected to Neo4j at {uri}[/green]")
        return driver
    except Exception as e:
        console.print(f"[red]✗ Failed to connect to Neo4j: {e}[/red]")
        return None

def get_database_info(driver):
    """Get basic database information"""
    console.print("\n[bold blue]📊 Database Overview[/bold blue]")
    
    with driver.session() as session:
        # Get node counts by label
        result = session.run("""
            CALL db.labels() YIELD label
            CALL apoc.cypher.run('MATCH (n:' + label + ') RETURN count(n) as count', {}) YIELD value
            RETURN label, value.count as count
            ORDER BY count DESC
        """)
        
        table = Table(title="Node Counts by Label")
        table.add_column("Label", style="cyan")
        table.add_column("Count", style="magenta", justify="right")
        
        total_nodes = 0
        for record in result:
            label = record["label"]
            count = record["count"]
            total_nodes += count
            table.add_row(label, str(count))
        
        console.print(table)
        console.print(f"[bold]Total Nodes: {total_nodes}[/bold]")

def get_relationship_info(driver):
    """Get relationship information"""
    console.print("\n[bold blue]🔗 Relationship Overview[/bold blue]")
    
    with driver.session() as session:
        # Get relationship counts by type
        result = session.run("""
            CALL db.relationshipTypes() YIELD relationshipType
            CALL apoc.cypher.run('MATCH ()-[r:' + relationshipType + ']->() RETURN count(r) as count', {}) YIELD value
            RETURN relationshipType, value.count as count
            ORDER BY count DESC
        """)
        
        table = Table(title="Relationship Counts by Type")
        table.add_column("Relationship Type", style="cyan")
        table.add_column("Count", style="magenta", justify="right")
        
        total_relationships = 0
        for record in result:
            rel_type = record["relationshipType"]
            count = record["count"]
            total_relationships += count
            table.add_row(rel_type, str(count))
        
        console.print(table)
        console.print(f"[bold]Total Relationships: {total_relationships}[/bold]")

def sample_data_by_label(driver, label, limit=5):
    """Get sample data for a specific label"""
    console.print(f"\n[bold blue]📋 Sample {label} Nodes (limit {limit})[/bold blue]")
    
    with driver.session() as session:
        result = session.run(f"""
            MATCH (n:{label})
            RETURN n
            LIMIT {limit}
        """)
        
        for i, record in enumerate(result, 1):
            node = record["n"]
            console.print(f"\n[bold cyan]{label} #{i}:[/bold cyan]")
            
            # Convert node properties to JSON for pretty printing
            properties = dict(node)
            console.print(Panel(
                json.dumps(properties, indent=2, default=str),
                title=f"Properties",
                border_style="blue"
            ))

def explore_schema(driver):
    """Explore the database schema"""
    console.print("\n[bold blue]🏗️ Database Schema[/bold blue]")
    
    with driver.session() as session:
        # Get constraints
        console.print("\n[bold yellow]Constraints:[/bold yellow]")
        result = session.run("SHOW CONSTRAINTS")
        for record in result:
            console.print(f"  • {record['name']}: {record['description']}")
        
        # Get indexes
        console.print("\n[bold yellow]Indexes:[/bold yellow]")
        result = session.run("SHOW INDEXES")
        for record in result:
            console.print(f"  • {record['name']}: {record['labelsOrTypes']} on {record['properties']}")

def main():
    console.print("[bold green]🔍 Neo4j Data Explorer[/bold green]")
    
    # Connect to Neo4j
    driver = connect_neo4j()
    if not driver:
        return
    
    try:
        # Get database overview
        get_database_info(driver)
        
        # Get relationship overview
        get_relationship_info(driver)
        
        # Explore schema
        explore_schema(driver)
        
        # Sample data from each label
        with driver.session() as session:
            result = session.run("CALL db.labels() YIELD label RETURN label ORDER BY label")
            labels = [record["label"] for record in result]
        
        for label in labels:
            sample_data_by_label(driver, label, limit=3)
        
    except Exception as e:
        console.print(f"[red]Error exploring Neo4j: {e}[/red]")
    finally:
        driver.close()

if __name__ == "__main__":
    main() 