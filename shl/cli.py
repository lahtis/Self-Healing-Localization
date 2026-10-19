"""Command line entry point for shl."""
import sys
from shl._version import __version__

def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print("Usage: shl <command>")
        print("Commands:")
        print("  extract   Extract translation keys (alias: shl-extract)")
        print("  version   Print version")
        return 0
    if argv[0] in ("-v", "--version", "version"):
        print(f"shl {__version__}")
        return 0
    print(f"error: unknown command {argv[0]!r}", file=sys.stderr)
    return 2

if __name__ == "__main__":
    sys.exit(main())
