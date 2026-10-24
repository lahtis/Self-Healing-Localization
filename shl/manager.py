"""Generic preloader manager. No application dependencies."""
import importlib.metadata
import importlib.util
import os


class PreloaderEntry:
    """One preloader with its state."""

    def __init__(self, name, runner):
        self.name = name
        self.runner = runner
        self.status = "pending"
        self.error = None


class PreloaderManager:
    """Discovers and runs preloaders from files and entry points.

    Parameters
    ----------
    entry_point_group : str | None
        Entry point -ryhmän nimi, esim. ``"shl.preloaders"``.
        Jos ``None``, entry pointteja ei ladata.
    """

    def __init__(self, entry_point_group=None):
        self.entry_point_group = entry_point_group
        self.preloaders = []
        self.loaded = []
        self.errors = []
        self.registry = {}

    # ---------- Discovery ----------
    def discover_from_directory(self, directory):
        if not os.path.isdir(directory):
            return
        for filename in sorted(os.listdir(directory)):
            if filename.startswith("_") or not filename.endswith(".py"):
                continue
            name = filename[:-3]
            path = os.path.join(directory, filename)
            self.preloaders.append(
                PreloaderEntry(name, self._make_file_runner(name, path))
            )

    def discover_from_entry_points(self):
        if not self.entry_point_group:
            return
        try:
            eps = importlib.metadata.entry_points().select(
                group=self.entry_point_group
            )
        except AttributeError:
            eps = importlib.metadata.entry_points().get(
                self.entry_point_group, []
            )
        for ep in eps:
            self.preloaders.append(
                PreloaderEntry(ep.name, self._make_ep_runner(ep))
            )

    @staticmethod
    def _make_file_runner(name, path):
        def runner(manager):
            spec = importlib.util.spec_from_file_location(
                f"shl_preloaders.{name}", path    # ← korjattu
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot load {path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            hook = getattr(module, "preload", None)
            if not callable(hook):
                raise ImportError(f"{path} has no preload(manager) function")
            hook(manager)
        return runner

    @staticmethod
    def _make_ep_runner(ep):
        def runner(manager):
            fn = ep.load()
            fn(manager)
        return runner

    # ---------- Execution ----------
    def __len__(self):
        return len(self.preloaders)

    def __iter__(self):
        return iter(self.preloaders)

    def run_one(self, index):
        entry = self.preloaders[index]
        entry.status = "running"
        try:
            entry.runner(self)
            entry.status = "ok"
            self.loaded.append(entry.name)
        except Exception as exc:
            entry.status = "error"
            entry.error = exc
            self.errors.append((entry.name, exc))
        return entry

    def run_all(self):
        for i in range(len(self)):
            self.run_one(i)

    # ---------- Registry ----------
    def register(self, key, value):
        self.registry[key] = value

    def get(self, key, default=None):
        return self.registry.get(key, default)

    def summary(self):
        return {
            "loaded": list(self.loaded),
            "errors": [(n, str(e)) for n, e in self.errors],
            "registry_keys": list(self.registry),
        }
