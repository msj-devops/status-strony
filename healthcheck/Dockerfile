# Obraz programu healthcheck (Faza 1, Moduł 06).
# Budowanie (w katalogu healthcheck/):  docker build -t <login>/healthcheck:1.0 .
# Uruchomienie:  docker run --rm -v "$PWD/cele.yaml:/dane/cele.yaml:ro" <login>/healthcheck:1.0 /dane/cele.yaml

# Lekki obraz bazowy z przypiętą wersją (Debian slim: glibc, gotowe koła dla requests/pyyaml).
FROM python:3.12-slim-trixe

# Bez plików .pyc w obrazie, logi od razu na stdout (docker logs).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Użytkownik systemowy bez uprawnień roota; wysoko, bo zmienia się rzadko (cache).
RUN useradd --system --uid 10001 --no-create-home healthcheck

WORKDIR /app

# Najpierw zależności (rzadko się zmieniają) — ta warstwa zostaje w cache przy zmianach kodu.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Potem kod aplikacji.
COPY healthcheck.py .

# Od tej chwili (i w kontenerze) nie-root. UID liczbą: Kubernetes (runAsNonRoot) sprawdzi go bez /etc/passwd obrazu.
USER 10001

# Obraz działa jak polecenie: argumenty z `docker run <obraz> …` trafiają do healthcheck.py.
# Forma exec (JSON) — inaczej argumenty są ignorowane, a sygnały nie docierają do Pythona.
ENTRYPOINT ["python", "/app/healthcheck.py"]

# Domyślny argument: konwencja „lista celów montowana w /dane/cele.yaml”.
CMD ["/dane/cele.yaml"]
