# status-strony

Strona zespołu z panelem `/admin/`, program `healthcheck`, który sprawdza, czy strona odpowiada, i chart Helm, który wdraża całość na Kubernetes. Projekt z kursu „From Zero to DevOps”, rozwijany od Fazy 3 razem z pipeline'em CI/CD.

Utrzymuje: **msj-devops**

## Co jest w repozytorium

| Katalog | Zawartość |
|---|---|
| `healthcheck/` | program w Pythonie: sprawdza listę adresów HTTP i zapisuje raport JSON; `Dockerfile` jego obrazu |
| `strona/html/` | treść strony: strona główna i panel `/admin/` |
| `strona/nginx/` | konfiguracja nginx: panel za hasłem HTTP Basic |
| `chart/status-strony/` | chart Helm: strona, healthcheck co 5 minut i strona statusu |
| `wdrozenia/dev/`, `wdrozenia/prod/` | wartości chartu dla środowisk |
| `.github/workflows/` | workflow GitHub Actions |

## Jak uruchomić lokalnie

Strona z nginx w kontenerze (bez panelu: plik z hasłami nie jest w repozytorium):

```bash
docker run --rm -p 8080:80 \
  -v "$PWD/strona/html:/usr/share/nginx/html:ro" \
  -v "$PWD/strona/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:1.30-alpine
```

healthcheck:

```bash
cd healthcheck
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 healthcheck.py PLIK_Z_CELAMI.yaml --raport raport.json
```
