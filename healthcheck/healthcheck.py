#!/usr/bin/env python3
"""Healthcheck: odpytuje listę adresów HTTP z pliku YAML i sprawdza kody statusu.

Użycie:
    python3 healthcheck.py cele.yaml [--timeout SEKUNDY] [--raport raport.json]

Format pliku:
    cele:
      - url: http://localhost/
        oczekiwany_status: 200

Kody wyjścia: 0 — wszystkie cele OK, 1 — co najmniej jeden BŁĄD,
2 — brak albo niepoprawny plik konfiguracji (lub nie da się zapisać raportu).
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests
import yaml

DOMYSLNY_TIMEOUT = 3.0


def wczytaj_cele(sciezka):
    """Zwraca listę celów [{url, oczekiwany_status}]. Rzuca ValueError (plik) albo TypeError (zły kształt danych)."""
    try:
        tresc = Path(sciezka).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ValueError(f"plik {sciezka} nie istnieje")
    except OSError as blad:
        raise ValueError(f"nie mogę odczytać pliku {sciezka}: {blad.strerror}")

    try:
        dane = yaml.safe_load(tresc)
    except yaml.YAMLError as blad:
        raise ValueError(f"plik {sciezka} nie jest poprawnym YAML-em: {blad}")

    if not isinstance(dane, dict) or not isinstance(dane.get("cele"), list):
        raise TypeError(f"w pliku {sciezka} brakuje listy pod kluczem 'cele'")

    cele = []
    for cel in dane["cele"]:
        if (
            not isinstance(cel, dict)
            or not isinstance(cel.get("url"), str)
            or not isinstance(cel.get("oczekiwany_status"), int)
        ):
            raise TypeError(
                f"niepoprawny cel w pliku {sciezka} (potrzebne: url i oczekiwany_status): {cel!r}"
            )
        cele.append({"url": cel["url"], "oczekiwany_status": cel["oczekiwany_status"]})
    return cele


def sprawdz_cel(url, oczekiwany_status, timeout):
    """Odpytuje jeden adres. Zwraca {url, status, czas_ms, ok}; status to None, gdy nie było odpowiedzi."""
    start = time.perf_counter()
    try:
        odpowiedz = requests.get(url, timeout=timeout)
        status = odpowiedz.status_code
    except requests.RequestException:
        # timeout, odmowa połączenia, błąd DNS, błędny adres — wszystko to jest BŁĄD celu, nie skryptu
        status = None
    czas_ms = round((time.perf_counter() - start) * 1000)
    return {
        "url": url,
        "status": status,
        "czas_ms": czas_ms,
        "ok": status == oczekiwany_status,
    }


def podsumowanie(wyniki):
    """Jedna linia z liczbą celów OK i łącznym czasem, np. 'Podsumowanie: 2/3 celów OK, łącznie 12 ms'."""
    ok = sum(1 for w in wyniki if w["ok"])
    razem_ms = sum(w.get("czas_ms", 0) for w in wyniki)
    return f"Podsumowanie: {ok}/{len(wyniki)} celów OK, łącznie {razem_ms} ms"


def najwolniejszy(wyniki):
    """Linia o celu, który odpowiadał najdłużej, np. 'Najwolniejszy cel: http://… (412 ms)'; None bez celów."""
    if not wyniki:
        return None
    w = max(wyniki, key=lambda x: x.get("czas_ms", 0))
    return f"Najwolniejszy cel: {w['url']} ({w.get('czas_ms', 0)} ms)"


def main():
    parser = argparse.ArgumentParser(
        description="Sprawdza dostępność adresów HTTP z pliku YAML."
    )
    parser.add_argument("konfiguracja", help="plik YAML z listą celów (klucz 'cele')")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DOMYSLNY_TIMEOUT,
        metavar="SEKUNDY",
        help=f"limit czasu na jedno zapytanie w sekundach (domyślnie {DOMYSLNY_TIMEOUT:g})",
    )
    parser.add_argument(
        "--raport", metavar="PLIK.json", help="zapisz wyniki do pliku JSON"
    )
    args = parser.parse_args()

    try:
        cele = wczytaj_cele(args.konfiguracja)
    except (ValueError, TypeError) as blad:
        print(f"Błąd: {blad}", file=sys.stderr)
        return 2

    wyniki = []
    print(f"{'URL':<45} {'STATUS':>6} {'CZAS_MS':>8}  WYNIK")
    for cel in cele:
        wynik = sprawdz_cel(cel["url"], cel["oczekiwany_status"], args.timeout)
        wyniki.append(wynik)
        status = "-" if wynik["status"] is None else wynik["status"]
        ocena = "OK" if wynik["ok"] else "BŁĄD"
        print(f"{wynik['url']:<45} {status:>6} {wynik['czas_ms']:>8}  {ocena}")
    print(podsumowanie(wyniki))
    linia = najwolniejszy(wyniki)
    if linia:
        print(linia)

    if args.raport:
        try:
            Path(args.raport).write_text(
                json.dumps(wyniki, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as blad:
            print(
                f"Błąd: nie mogę zapisać raportu {args.raport}: {blad.strerror}",
                file=sys.stderr,
            )
            return 2

    return 0 if all(w["ok"] for w in wyniki) else 1


def opisz_wynik(wynik):
    """Jedna linia o wyniku celu do raportu dziennego (raport dopiszę w kolejnym Pull Requeście)."""
    status = wynik.get("status")
    if status is None:
        return f"{wynik['url']}: brak odpowiedzi"
    return f"{wynik['url']}: {status} w {wynik['czas_ms']} ms"


if __name__ == "__main__":
    sys.exit(main())
