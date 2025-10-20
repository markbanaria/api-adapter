import asyncio
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable, Dict, Any
import time

logger = logging.getLogger(__name__)


class ConfigFileHandler(FileSystemEventHandler):
    """Handler for config file changes"""

    def __init__(self, config_dir: Path, reload_callback: Callable):
        self.config_dir = config_dir
        self.reload_callback = reload_callback
        self.last_reload = 0
        self.debounce_delay = 1.0  # 1 second debounce

    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only react to .yaml files in our config directory
        if (file_path.suffix.lower() in ['.yaml', '.yml'] and
            file_path.parent == self.config_dir):
            self._debounced_reload(f"File modified: {file_path.name}")

    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only react to .yaml files in our config directory
        if (file_path.suffix.lower() in ['.yaml', '.yml'] and
            file_path.parent == self.config_dir):
            self._debounced_reload(f"File created: {file_path.name}")

    def on_deleted(self, event):
        """Handle file deletion events"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only react to .yaml files in our config directory
        if (file_path.suffix.lower() in ['.yaml', '.yml'] and
            file_path.parent == self.config_dir):
            self._debounced_reload(f"File deleted: {file_path.name}")

    def _debounced_reload(self, reason: str):
        """Debounced reload to prevent multiple rapid reloads"""
        current_time = time.time()

        if current_time - self.last_reload > self.debounce_delay:
            self.last_reload = current_time
            logger.info(f"Config change detected: {reason}")

            # Schedule reload in main event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(self._async_reload())
                    )
                else:
                    logger.warning("Event loop not running, cannot reload configs")
            except RuntimeError:
                logger.warning("No event loop available, cannot reload configs")

    async def _async_reload(self):
        """Async wrapper for reload callback"""
        try:
            await self.reload_callback()
        except Exception as e:
            logger.error(f"Failed to reload configs: {e}", exc_info=True)


class ConfigFileWatcher:
    """Watches config directory for changes and triggers reloads"""

    def __init__(self, config_dir: Path, reload_callback: Callable):
        self.config_dir = config_dir
        self.reload_callback = reload_callback
        self.observer = None
        self.handler = None

    def start(self):
        """Start watching for file changes"""
        if self.observer is not None:
            logger.warning("File watcher is already running")
            return

        self.handler = ConfigFileHandler(self.config_dir, self.reload_callback)
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.config_dir), recursive=False)
        self.observer.start()

        logger.info(f"Started watching config directory: {self.config_dir}")

    def stop(self):
        """Stop watching for file changes"""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.handler = None
            logger.info("Stopped config file watcher")

    def is_running(self) -> bool:
        """Check if watcher is running"""
        return self.observer is not None and self.observer.is_alive()