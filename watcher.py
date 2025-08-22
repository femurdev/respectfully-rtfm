import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Watcher:
    def __init__(self, path, callback):
        self.observer = Observer()
        self.path = path
        self.callback = callback

    def run(self):
        event_handler = Handler(self.callback)
        self.observer.schedule(event_handler, self.path, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

class Handler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            self.callback(event.src_path)

if __name__ == "__main__":
    def regenerate(file_path):
        print(f"File changed: {file_path}. Regenerating documentation...")
        # Placeholder for integration with docgen.py

    path_to_watch = os.getcwd()
    watcher = Watcher(path_to_watch, regenerate)
    watcher.run()