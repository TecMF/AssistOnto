from app import start_webapp
import argparse
import sys

if __name__ == "__main__":
  # define parser for command line arguments
  parser = argparse.ArgumentParser(description="AssistOnto")
  subparsers = parser.add_subparsers()
  parser_server = subparsers.add_parser('server', help="Start up AssistOnto web interface")
  parser_server.add_argument("--db-path", metavar="DBPATH", help="Path to SQLite database file storing application data", type=str)
  parser_server.add_argument("--host", metavar="HOST", help="Host address", type=str)
  parser_server.add_argument("--port", metavar="PORT", help="Port to listen to", type=int)
  parser_server.add_argument("--debug", metavar="DEBUG", action=argparse.BooleanOptionalAction, help="Whether to run app in debug mode")
  parser_server.set_defaults(func=lambda args: start_webapp(host=args.host, port=args.port, debug_mode=args.debug, db_path=args.db_path))

  # parse
  if len(sys.argv) <= 1:
    parser.print_help(sys.stderr)
    sys.exit(1)
  args = parser.parse_args()
  # run
  args.func(args)
