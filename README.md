# status-strony

Strona zespołu z panelem `/admin/`, program `healthcheck`, który sprawdza, czy strona odpowiada, i chart Helm, który wdraża całość na Kubernetes. Projekt z kursu „From Zero to DevOps”, rozwijany od Fazy 3 razem z pipeline'em CI/CD.

Utrzymuje: **msj-devops**

## Co jest w repozytorium

| Katalog | Zawartość |
|---|---|
| `healthcheck/` | program w Pythonie: sprawdza listę adresów HTTP i zapisuje raport JSON; `Dockerfile` jego obrazu |
| `chart/status-strony/` | chart Helm: strona, healthcheck co 5 minut i strona statusu |
| `chart/status-strony/files/` | treść strony (strona główna, panel `/admin/`) i konfiguracja nginx: jedyne źródło, z którego korzysta chart i test strony |
| `wdrozenia/dev/`, `wdrozenia/prod/` | wartości chartu dla środowisk |
| `.github/workflows/` | workflow GitHub Actions |

## Jak uruchomić lokalnie

Strona z nginx w kontenerze (bez panelu: plik z hasłami nie jest w repozytorium). Treść ma wyrażenia Helma, więc najpierw renderujesz chart z wartościami `dev`:

```bash
mkdir -p /tmp/strona/html/admin /tmp/strona/nginx
helm template strona-dev chart/status-strony -n f2-dev -f wdrozenia/dev/values.yaml \
  --show-only templates/configmap-strona.yaml > /tmp/strona/configmap.yaml
yq '.data["index.html"]' /tmp/strona/configmap.yaml > /tmp/strona/html/index.html
yq '.data["admin.html"]' /tmp/strona/configmap.yaml > /tmp/strona/html/admin/index.html
yq '.data["default.conf"]' /tmp/strona/configmap.yaml > /tmp/strona/nginx/default.conf
docker run --rm -p 8080:80 \
  -v /tmp/strona/html:/usr/share/nginx/html:ro \
  -v /tmp/strona/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro \
  nginx:1.30-alpine
```

## CI

Każdy Pull Request sprawdza workflow `CI` (`.github/workflows/ci.yml`): lintery (ruff, yamllint, hadolint, actionlint), testy healthchecka na trzech wersjach Pythona, chart (`helm lint`, `helm template | kubeconform` dla `dev` i `prod`) i budowanie obrazu bez publikacji. Joby ruszają tylko dla zmienionych części, a job `CI OK` zbiera ich wyniki. Test strony (`test-strony.yml`) uruchamia stronę z chartu na amd64 i arm64. Gałąź `main` chroni reguła: scalenie wymaga zielonych `CI OK` i obu wariantów testu strony.

Testy i lintery lokalnie (w `healthcheck/`, w tych samych wersjach co w CI — `requirements-dev.txt`):

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest
ruff check .
```

healthcheck:

```bash
cd healthcheck
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 healthcheck.py PLIK_Z_CELAMI.yaml --raport raport.json
```
