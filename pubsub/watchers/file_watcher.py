"""
File system watcher using watchdog library.

Watches specified directories for new files and creates events in the pub-sub queue.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

logger = logging.getLogger(__name__)


class FileEventHandler(FileSystemEventHandler):
    """
    Handler for file system events.

    Creates pub-sub events when files are created or moved into watched directories.
    """

    def __init__(
        self,
        event_callback,
        file_patterns: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None
    ):
        """
        Initialize file event handler.

        Args:
            event_callback: Function to call when event occurs (receives event_data dict)
            file_patterns: Optional list of glob patterns to match (e.g., ['*.csv', '*.xlsx'])
            ignore_patterns: Optional list of patterns to ignore (e.g., ['*.tmp', '.*'])
        """
        super().__init__()
        self.event_callback = event_callback
        self.file_patterns = file_patterns or ['*']
        self.ignore_patterns = ignore_patterns or ['*.tmp', '*.swp', '.*', '*~']

    def _should_process(self, path: str) -> bool:
        """Check if file should be processed based on patterns."""
        import fnmatch
        filename = os.path.basename(path)

        # Check ignore patterns
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return False

        # Check file patterns
        for pattern in self.file_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True

        return False

    def _create_event_data(self, file_path: str, event_type: str) -> Dict[str, Any]:
        """Create event data dictionary for a file event."""
        path = Path(file_path)
        stat = path.stat() if path.exists() else None

        return {
            'file_path': str(path.absolute()),
            'filename': path.name,
            'directory': str(path.parent),
            'extension': path.suffix,
            'size_bytes': stat.st_size if stat else 0,
            'created_at': datetime.now().isoformat(),
            'fs_event_type': event_type
        }

    def on_created(self, event):
        """Handle file creation event."""
        if event.is_directory:
            return

        if not self._should_process(event.src_path):
            logger.debug(f"Ignoring file: {event.src_path}")
            return

        logger.info(f"File created: {event.src_path}")
        event_data = self._create_event_data(event.src_path, 'created')
        self.event_callback(event_data)

    def on_moved(self, event):
        """Handle file move event (file moved into watched directory)."""
        if event.is_directory:
            return

        if not self._should_process(event.dest_path):
            logger.debug(f"Ignoring moved file: {event.dest_path}")
            return

        logger.info(f"File moved: {event.dest_path}")
        event_data = self._create_event_data(event.dest_path, 'moved')
        event_data['source_path'] = event.src_path
        self.event_callback(event_data)


class FileWatcher:
    """
    Watches directories for file events.

    Uses watchdog Observer to monitor file system changes.
    """

    def __init__(
        self,
        directories: List[str],
        event_callback,
        file_patterns: Optional[List[str]] = None,
        recursive: bool = False
    ):
        """
        Initialize file watcher.

        Args:
            directories: List of directories to watch
            event_callback: Function to call when file event occurs
            file_patterns: Optional list of glob patterns to match
            recursive: Whether to watch subdirectories
        """
        self.directories = directories
        self.event_callback = event_callback
        self.file_patterns = file_patterns
        self.recursive = recursive
        self.observer = Observer()
        self._running = False

    def start(self):
        """Start watching directories."""
        handler = FileEventHandler(
            event_callback=self.event_callback,
            file_patterns=self.file_patterns
        )

        for directory in self.directories:
            if os.path.isdir(directory):
                logger.info(f"Watching directory: {directory}")
                self.observer.schedule(handler, directory, recursive=self.recursive)
            else:
                logger.warning(f"Directory not found: {directory}")

        self.observer.start()
        self._running = True
        logger.info("File watcher started")

    def stop(self):
        """Stop watching directories."""
        if self._running:
            self.observer.stop()
            self.observer.join()
            self._running = False
            logger.info("File watcher stopped")

    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running


if __name__ == '__main__':
    # Test the file watcher
    import time
    logging.basicConfig(level=logging.INFO)

    def test_callback(event_data):
        print(f"Event received: {json.dumps(event_data, indent=2)}")

    watcher = FileWatcher(
        directories=['/app/data/source'],
        event_callback=test_callback,
        file_patterns=['*.csv', '*.xlsx']
    )

    try:
        watcher.start()
        print("Watching for file events. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
        print("Watcher stopped.")
