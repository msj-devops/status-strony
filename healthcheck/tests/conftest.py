"""Wspólne fixture testów healthchecka: lokalny serwer HTTP i plik celów w katalogu tymczasowym."""

import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class _Obsluga(BaseHTTPRequestHandler):
    """/ok → 200, /awaria → 503, /wolny → 200 po 2 s, inne ścieżki → 404."""

    def do_GET(self):
        if self.path == "/ok":
            self._odpowiedz(200)
        elif self.path == "/awaria":
            self._odpowiedz(503)
        elif self.path == "/wolny":
            time.sleep(2)
            self._odpowiedz(200)
        else:
            self._odpowiedz(404)

    def _odpowiedz(self, kod):
        try:
            self.send_response(kod)
            self.send_header("Content-Length", "0")
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
            pass  # klient przestał czekać (test z krótkim timeoutem)

    def log_message(self, *args):
        pass  # bez logu każdego zapytania w wynikach testów


@pytest.fixture(scope="session")
def serwer():
    """Adres bazowy serwera testowego na wolnym porcie, np. http://127.0.0.1:43127"""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Obsluga)
    httpd.daemon_threads = True
    watek = threading.Thread(target=httpd.serve_forever, daemon=True)
    watek.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def zamkniety_port():
    """Port, na którym nikt nie nasłuchuje: połączenie zostanie odrzucone."""
    with socket.socket() as gniazdo:
        gniazdo.bind(("127.0.0.1", 0))
        return gniazdo.getsockname()[1]


@pytest.fixture
def plik_celow(tmp_path):
    """Funkcja, która zapisuje listę (url, oczekiwany_status) jako plik celów i zwraca jego ścieżkę."""

    def zapisz(cele):
        tresc = "cele:\n" + "".join(
            f"  - url: {url}\n    oczekiwany_status: {kod}\n" for url, kod in cele
        )
        sciezka = tmp_path / "cele.yaml"
        sciezka.write_text(tresc, encoding="utf-8")
        return sciezka

    return zapisz
