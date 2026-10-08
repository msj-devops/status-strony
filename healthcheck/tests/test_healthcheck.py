"""Testy healthchecka: plik celów, sprawdzanie jednego celu i program jako całość."""

import json
import sys

import pytest

import healthcheck

# ---------------------------------------------------------------- plik celów


def test_wczytaj_cele_z_poprawnego_pliku(plik_celow):
    sciezka = plik_celow(
        [("http://example.test/", 200), ("http://example.test/brak", 404)]
    )

    cele = healthcheck.wczytaj_cele(sciezka)

    assert cele == [
        {"url": "http://example.test/", "oczekiwany_status": 200},
        {"url": "http://example.test/brak", "oczekiwany_status": 404},
    ]


def test_brak_pliku_celow_to_czytelny_blad(tmp_path):
    with pytest.raises(ValueError, match="nie istnieje"):
        healthcheck.wczytaj_cele(tmp_path / "nie-ma.yaml")


@pytest.mark.parametrize(
    "tresc",
    [
        "cele: to nie lista\n",
        "inne: []\n",
        "cele:\n  - url: http://example.test/\n",
        "cele:\n  - url: http://example.test/\n    oczekiwany_status: dwieście\n",
    ],
    ids=["cele-nie-lista", "brak-klucza-cele", "brak-statusu", "status-nie-liczba"],
)
def test_zly_ksztalt_pliku_celow(tmp_path, tresc):
    sciezka = tmp_path / "cele.yaml"
    sciezka.write_text(tresc, encoding="utf-8")

    with pytest.raises(TypeError):
        healthcheck.wczytaj_cele(sciezka)


def test_plik_celow_bez_poprawnego_yamla(tmp_path):
    sciezka = tmp_path / "cele.yaml"
    sciezka.write_text("cele: [\n", encoding="utf-8")

    with pytest.raises(ValueError, match="YAML"):
        healthcheck.wczytaj_cele(sciezka)


# ---------------------------------------------------------------- jeden cel


@pytest.mark.parametrize(
    "sciezka, oczekiwany, status, ok",
    [
        ("/ok", 200, 200, True),
        ("/awaria", 200, 503, False),
        ("/nie-ma", 404, 404, True),
        ("/ok", 404, 200, False),
    ],
)
def test_sprawdz_cel_porownuje_status(serwer, sciezka, oczekiwany, status, ok):
    wynik = healthcheck.sprawdz_cel(serwer + sciezka, oczekiwany, timeout=2)

    assert wynik["url"] == serwer + sciezka
    assert wynik["status"] == status
    assert wynik["ok"] is ok
    assert wynik["czas_ms"] >= 0


def test_cel_bez_odpowiedzi_to_blad_celu(zamkniety_port):
    wynik = healthcheck.sprawdz_cel(
        f"http://127.0.0.1:{zamkniety_port}/", 200, timeout=1
    )

    assert wynik["status"] is None
    assert wynik["ok"] is False


def test_przekroczony_timeout_to_blad_celu(serwer):
    wynik = healthcheck.sprawdz_cel(serwer + "/wolny", 200, timeout=0.5)

    assert wynik["status"] is None
    assert wynik["ok"] is False
    assert wynik["czas_ms"] < 2000


# ---------------------------------------------------------------- program


def uruchom(monkeypatch, *argumenty):
    """main() z podanymi argumentami wiersza poleceń; zwraca kod wyjścia."""
    monkeypatch.setattr(sys, "argv", ["healthcheck.py", *map(str, argumenty)])
    return healthcheck.main()


def test_kod_0_i_raport_gdy_wszystkie_cele_ok(
    monkeypatch, serwer, plik_celow, tmp_path, capsys
):
    raport = tmp_path / "raport.json"

    kod = uruchom(monkeypatch, plik_celow([(serwer + "/ok", 200)]), "--raport", raport)

    assert kod == 0
    assert json.loads(raport.read_text(encoding="utf-8"))[0]["ok"] is True
    assert "OK" in capsys.readouterr().out


def test_kod_1_gdy_ktorys_cel_zawiodl(monkeypatch, serwer, plik_celow):
    kod = uruchom(
        monkeypatch, plik_celow([(serwer + "/ok", 200), (serwer + "/awaria", 200)])
    )

    assert kod == 1


def test_kod_2_i_komunikat_gdy_brak_pliku(monkeypatch, tmp_path, capsys):
    kod = uruchom(monkeypatch, tmp_path / "nie-ma.yaml")

    assert kod == 2
    assert "nie istnieje" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("oki", "oczekiwane"),
    [
        ([True, True], "Podsumowanie: 2/2 celów OK, łącznie 20 ms"),
        ([True, False, False], "Podsumowanie: 1/3 celów OK, łącznie 30 ms"),
        ([], "Podsumowanie: 0/0 celów OK, łącznie 0 ms"),
    ],
)
def test_podsumowanie_liczy_cele_ok_i_czas(oki, oczekiwane):
    assert healthcheck.podsumowanie([{"ok": ok, "czas_ms": 10} for ok in oki]) == oczekiwane


def test_najwolniejszy_wskazuje_cel_z_najdluzszym_czasem():
    wyniki = [
        {"url": "http://a.test/", "czas_ms": 12},
        {"url": "http://b.test/", "czas_ms": 412},
        {"url": "http://c.test/", "czas_ms": 30},
    ]

    assert (
        healthcheck.najwolniejszy(wyniki)
        == "Najwolniejszy cel: http://b.test/ (412 ms)"
    )


def test_najwolniejszy_bez_celow_to_none():
    assert healthcheck.najwolniejszy([]) is None


def test_program_wypisuje_najwolniejszy_cel(monkeypatch, serwer, plik_celow, capsys):
    uruchom(
        monkeypatch, plik_celow([(serwer + "/ok", 200), (serwer + "/wolny", 200)])
    )

    assert f"Najwolniejszy cel: {serwer}/wolny (" in capsys.readouterr().out
