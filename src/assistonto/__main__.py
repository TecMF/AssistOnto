from .app import start_webapp, markdown_to_html
from .docdb import go_doc_db
import argparse
import sys

def cli_start_webapp(args):
  start_webapp(
    host=args.host,
    port=args.port,
    debug_mode=args.debug,
    db_path=args.db_path,
    docdb_path=args.docdb_path,
  )

def markdown_file_to_html(fp):
  with open(fp) as f:
    input_text = f.read()
  return markdown_to_html(input_text)

def main():
  # define parser for command line arguments
  parser = argparse.ArgumentParser(description="AssistOnto")
  subparsers = parser.add_subparsers()
  # assistant server
  parser_server = subparsers.add_parser('server', help="Start up AssistOnto web interface")
  parser_server.add_argument("--db-path", metavar="DBPATH", help="Path to SQLite database file storing application data", type=str)
  parser_server.add_argument("--docdb-path", metavar="DOCDBPATH", help="Path to database of document embeddings used for RAG", type=str)
  parser_server.add_argument("--host", metavar="HOST", help="Host address", type=str)
  parser_server.add_argument("--port", metavar="PORT", help="Port to listen to", type=int)
  parser_server.add_argument("--debug", metavar="DEBUG", action=argparse.BooleanOptionalAction, help="Whether to run app in debug mode")
  parser_server.set_defaults(func=cli_start_webapp)
  # RAG docs DB
  parser_docs = subparsers.add_parser('docs', help="Initialize document database for RAG")
  parser_docs.add_argument("--docdb-path", metavar="DOCDBPATH", help="Path to database file storing documents", type=str, required=True)
  parser_docs.add_argument("--add", metavar="DIR", help="Path to directory containing documents to add to database", type=str)
  parser_docs.add_argument("--query", metavar="TEXT", help="Text to query", action='append')
  parser_docs.add_argument("--reset-db", help="Reset database", action='store_true')
  parser_docs.set_defaults(func=lambda args: go_doc_db(docdb_path=args.docdb_path, doc_dir=args.add, queries=args.query, reset_db=args.reset_db))
  # render markdown
  parser_md = subparsers.add_parser('markdown', help="Render markdown document as HTML")
  parser_md.add_argument("filepath", metavar="PATH", help="Path to markdown file", type=str)
  parser_md.set_defaults(func=lambda args: markdown_file_to_html(args.filepath))

  # parse
  if len(sys.argv) <= 1:
    parser.print_help(sys.stderr)
    sys.exit(1)
  args = parser.parse_args()
  # run
  sys.exit(args.func(args))


if __name__ == "__main__":
  main()
