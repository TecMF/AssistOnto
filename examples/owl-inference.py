#!/usr/bin/env python3

# owl-rl-inferencing.py: read RDF files provided as command line
# arguments, do OWL RL inferencing, and output any new triples
# resulting from that.

import sys
import rdflib
import owlrl

if len(sys.argv) <  2:  # print directions
    print("Read RDF files, perform inferencing, and output the new triples.")
    print ("Enter one or more .ttl, .nt, and .rdf filenames as arguments.")
    sys.exit()

inputGraph = rdflib.Graph()
graphToExpand = rdflib.Graph()

# Read the files. arg 0 is the script name, so don't parse that as RDF.
for filename in sys.argv[1:]:
    if filename.endswith(".ttl"):
       inputGraph.parse(filename, format="turtle")
    elif filename.endswith(".nt"):
       inputGraph.parse(filename, format="nt")
    elif filename.endswith(".rdf"):
       inputGraph.parse(filename, format="xml")
    else:
        print("# Filename " + filename + " doesn't end with .ttl, .nt, or .rdf.")

owlrl.interpret_owl_imports('auto', inputGraph)

# Copy the input graph so that we can diff to identify new triples later.
for s, p, o in inputGraph:
    graphToExpand.add((s,p,o))

# Do the inferencing. See
# https://owl-rl.readthedocs.io/en/latest/stubs/owlrl.DeductiveClosure.html#owlrl.DeductiveClosure
# for other owlrl.* choices.
owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(graphToExpand)


query = """
prefix ns1: <http://www.daml.org/2002/03/agents/agent-ont#>

SELECT ?error ?errorMessage
WHERE {
    ?error a ns1:ErrorMessage .
    ?error ns1:error ?errorMessage .
}
"""

results = graphToExpand.query(query)

# Display the error messages found
for row in results:
    print(f"Error Message: {row.errorMessage}, Error: {row.error}")

newTriples = graphToExpand - inputGraph  # How cool is that?

# Output Turtle comments reporting on graph sizes
print(f"# inputGraph: {len(inputGraph)} triples")
print(f"# graphToExpand: {len(graphToExpand)} triples")
print(f"# newTriples: {len(newTriples)} triples")

# Output the new triples
# print(newTriples.serialize(format='turtle'))
