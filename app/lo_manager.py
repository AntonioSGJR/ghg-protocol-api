import subprocess
import time
from pathlib import Path
from threading import Lock

import uno
from com.sun.star.beans import PropertyValue


class LibreOfficeManager:
    """Mantém uma instância do LibreOffice viva para evitar o custo de inicialização por requisição."""

    def __init__(self, port: int = 2002, profile_dir: str = "/tmp/libreoffice-profile"):
        self.port = port
        self.profile_dir = Path(profile_dir)
        self.process: subprocess.Popen | None = None
        self.lock = Lock()
        self.local_ctx = uno.getComponentContext()
        self.resolver = self.local_ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", self.local_ctx
        )
        self.ctx = None

    @staticmethod
    def _prop(name: str, value):
        prop = PropertyValue()
        prop.Name = name
        prop.Value = value
        return prop

    def start(self):
        if self.process and self.process.poll() is None and self.ctx:
            return

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        profile_url = self.profile_dir.resolve().as_uri()

        self.process = subprocess.Popen(
            [
                "libreoffice",
                "--headless",
                "--nologo",
                "--nodefault",
                "--nofirststartwizard",
                "--norestore",
                f"-env:UserInstallation={profile_url}",
                f"--accept=socket,host=127.0.0.1,port={self.port};urp;StarOffice.ComponentContext",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        last_error = None
        for _ in range(60):
            try:
                self.ctx = self.resolver.resolve(
                    f"uno:socket,host=127.0.0.1,port={self.port};urp;StarOffice.ComponentContext"
                )
                return
            except Exception as exc:
                last_error = exc
                time.sleep(0.25)

        raise RuntimeError(f"Não foi possível iniciar o LibreOffice: {last_error}")

    def recalculate(self, input_path: Path, output_path: Path):
        with self.lock:
            self.start()

            input_url = input_path.resolve().as_uri()
            output_url = output_path.resolve().as_uri()

            desktop = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", self.ctx
            )

            load_props = (
                self._prop("Hidden", True),
                self._prop("ReadOnly", False),
                self._prop("UpdateDocMode", 3),
            )

            document = desktop.loadComponentFromURL(input_url, "_blank", 0, load_props)
            if document is None:
                raise RuntimeError("LibreOffice não conseguiu abrir a planilha.")

            try:
                document.enableAutomaticCalculation(True)
                document.calculateAll()

                store_props = (
                    self._prop("FilterName", "Calc MS Excel 2007 XML"),
                    self._prop("Overwrite", True),
                )
                document.storeAsURL(output_url, store_props)
            finally:
                document.close(True)

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        self.ctx = None
