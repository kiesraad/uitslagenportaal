from pathlib import Path


class FolderPDFFileHanlder:
    def __init__(self, folder: Path):
        super().__init__()
        self.folder = folder

    def _import_pv(self, file):
        int

    def run(self):
        files = sorted(self.folder.rglob("*.pdf"))
        for file in files:
            self._import_pv(file)
