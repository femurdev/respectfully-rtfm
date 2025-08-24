import argparse
import json
import os
import sys
from .crawler import DocCrawler
from .utils import ensure_on_sys_path, is_python_file


def main():
    parser = argparse.ArgumentParser(description="Deep Python documentation crawler")
    parser.add_argument("path", help="Path to a project directory or .py file")
    parser.add_argument("--max-modules", type=int, default=5000)
    parser.add_argument("--max-file-size", type=int, default=2_000_000)
    parser.add_argument("--no-follow", action="store_true")
    args = parser.parse_args()

    crawler = DocCrawler(
        max_modules=args.max_modules,
        max_file_size_bytes=args.max_file_size,
        follow_dependency_tree=not args.no_follow,
    )

    target = os.path.abspath(args.path)
    if os.path.isdir(target):
        results = crawler.crawl_directory(target)
    elif os.path.isfile(target) and is_python_file(target):
        results = crawler.crawl_directory(os.path.dirname(target))
    else:
        print("Invalid path")
        sys.exit(1)

    def coerce(obj):
        if isinstance(obj, set):
            return list(obj)
        return obj

    print(json.dumps(results, default=coerce, indent=2))


if __name__ == "__main__":
    main()
