"""CLI: serve-mock | sync | status."""

import argparse

from .read import Reader
from .sync import run_sync


def main():
    parser = argparse.ArgumentParser(prog="snapshot_sync")
    sub = parser.add_subparsers(dest="cmd", required=True)

    serve = sub.add_parser("serve-mock", help="run the flaky demo source")
    serve.add_argument("--port", type=int, default=8811)
    serve.add_argument("--rate-limit-every", type=int, default=7)
    serve.add_argument("--fail-first", type=int, default=1)

    sync = sub.add_parser("sync", help="pull one snapshot")
    sync.add_argument("--source", required=True)
    sync.add_argument("--data", required=True)
    sync.add_argument("--page-size", type=int, default=50)

    status = sub.add_parser("status", help="what the read surface would serve")
    status.add_argument("--data", required=True)

    args = parser.parse_args()
    if args.cmd == "serve-mock":
        from .mock_source import MockSource
        server = MockSource(("127.0.0.1", args.port),
                            fail_first=args.fail_first,
                            rate_limit_every=args.rate_limit_every)
        print(f"mock source at {server.url} (fail_first={args.fail_first}, "
              f"rate_limit_every={args.rate_limit_every}); Ctrl-C to stop")
        server.serve_forever()
    elif args.cmd == "sync":
        marker = run_sync(args.source, args.data, page_size=args.page_size)
        print(f"run {marker['run_id']}: {marker['items']} items -> {marker['snapshot']}")
    elif args.cmd == "status":
        reader = Reader(args.data)
        row = reader.latest()
        if row is None:
            print("no complete snapshot")
        else:
            print(f"run {row['run_id']}: {row['items']} items, "
                  f"age {reader.data_age_seconds():.0f}s")


if __name__ == "__main__":
    main()
