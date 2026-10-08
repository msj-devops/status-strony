"""Healthcheck uruchomiony jak przez człowieka: cel odpowiada 503."""

import json
import subprocess
import sys
from pathlib import Path

HEALTHCHECK = next(
    p / "healthcheck.py"
    for p in Path(__file__).resolve().parents
    if (p / "healthcheck.py").is_file()
)


def test_cel_503_daje_kod_1_i_raport(httpserver, tmp_path):
    httpserver.expect_request("/zdrowie").respond_with_data("awaria", status=503)
    cele = tmp_path / "cele.yaml"
    cele.write_text(
        f"cele:\n  - url: {httpserver.url_for('/zdrowie')}\n    oczekiwany_status: 200\n",
        encoding="utf-8",
    )
    raport = tmp_path / "raport.json"

    wynik = subprocess.run(
        [sys.executable, str(HEALTHCHECK), str(cele), "--raport", str(raport)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert wynik.returncode == 1
    dane = json.loads(raport.read_text(encoding="utf-8"))
    assert dane[0]["status"] == 503
    assert dane[0]["ok"] is False
