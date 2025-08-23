# server.py

DocCache: thread-safe documentation cache with mtime fingerprinting and inverted index.

This module provides DocCache, a reusable component suitable for embedding into
web servers or other tools that need to keep an up-to-date view of parsed
Python documentation for a path.

It intentionally does not depend on Flask or any web framework; it simply
maintains parsed docs, an inverted index, and exposes a snapshot and search
API that are safe to call from multiple threads.