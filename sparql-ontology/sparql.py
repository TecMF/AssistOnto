#!/usr/bin/env python3

# could also use oxigraph or sophia (rust), or maybe redland rdf (librdf, C)

import argparse
from rdflib import Graph

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Run a SPARQL query on an RDF ontology.")
    parser.add_argument("ontology", help="Path to the ontology file (e.g., ontology.ttl).")
    parser.add_argument("query", help="Path to the SPARQL query file (e.g., query.sparql).")
    parser.add_argument("--format", default="turtle", help="Ontology file format (default: turtle).")

    # Parse arguments
    args = parser.parse_args()

    # Load ontology
    g = Graph()
    try:
        g.parse(args.ontology, format=args.format)
        print(f"Ontology loaded successfully from {args.ontology}")
    except Exception as e:
        print(f"Error loading ontology: {e}")
        return

    # Load SPARQL query
    try:
        with open(args.query, "r") as query_file:
            query = query_file.read()
    except Exception as e:
        print(f"Error reading query file: {e}")
        return

    # Run query
    try:
        results = g.query(query)
        print("Query executed successfully. Results:")
        for row in results:
            print("\t".join(map(str, row)))
    except Exception as e:
        print(f"Error executing query: {e}")

if __name__ == "__main__":
    main()
