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

## CD

```
scalenie do main ─▶ CD: obraz ghcr.io/msj-devops/healthcheck:<SHA> (amd64, arm64)
                 ─▶ próba w klastrze kind (runner GitHuba) ─▶ dev: runner w VM, helm upgrade do f2-dev
tag vX.Y.Z       ─▶ Wydanie: obraz <SHA> dostaje tag X.Y.Z ─▶ zatwierdzenie (środowisko prod)
                 ─▶ Pull Request „Prod: healthcheck X.Y.Z” ─▶ scalenie ─▶ Argo CD wdraża f2-prod
```

- **Dev** wdraża się sam po każdym scaleniu do `main` (workflow `CD`, job na runnerze w VM z etykietą `minikube`). Runner działa jako użytkownik bez `sudo`, a jego konto w klastrze ma uprawnienia tylko w `f2-dev` (`wdrozenia/dev/dostep-runnera.yaml`).
- **Wydanie:** `git tag -a v1.2.0 -m "…"` na commicie z `main`, dla którego `CD` jest zielony, i `git push origin v1.2.0`. Po zatwierdzeniu w środowisku `prod` workflow `Wydanie` otwiera Pull Request ze zmianą wersji w `wdrozenia/prod/values.yaml`. Scalasz go jak każdy inny, przy zielonych testach.
- **Wycofanie na prod:** `git revert` commitu „Prod: healthcheck X.Y.Z” w Pull Requeście i scalenie. Argo CD wróci do poprzedniej wersji.
- **Wycofanie na dev:** ponowne uruchomienie joba `Wdrożenie na dev` z przebiegu `CD` dla poprzedniego commita (`gh run rerun <ID> --job <ID joba>`).

## Sekrety i konfiguracja środowisk

W repozytorium nie ma żadnych haseł ani skrótów haseł. Konfiguracja aplikacji jest w `wdrozenia/<środowisko>/values.yaml`, a to, czego potrzebuje pipeline, w ustawieniach środowisk GitHuba (*Settings → Environments*):

| Co | dev | prod |
|---|---|---|
| adres strony w historii wdrożeń | zmienna `ADRES_STRONY` środowiska `dev` | zmienna `ADRES_STRONY` środowiska `prod` |
| login do panelu `/admin/` | zmienna `PANEL_LOGIN` środowiska `dev` | w Secrecie w klastrze (niżej) |
| hasło do panelu | sekret `PANEL_HASLO` środowiska `dev`; job „Wdrożenie na dev” zamienia je na skrót i zapisuje w Secrecie `strona-htpasswd` w `f2-dev` | **poza GitHubem**: Secret `strona-htpasswd` w `f2-prod` tworzy ręcznie administrator klastra (przepis: README chartu, „Secret z hasłami panelu”). Pipeline i Argo CD go nie dotykają |

**Zmiana hasła na dev:** `gh secret set PANEL_HASLO --env dev` (pyta o hasło), potem ponowne uruchomienie joba „Wdrożenie na dev” z ostatniego przebiegu `CD` (`gh run rerun <ID> --job <ID joba>`). Bez tego dev ma stare hasło: job czyta sekret, gdy rusza.

**Zmiana hasła na prod:** z konta administratora klastra, z hasłem podanym na wejście (bez zapisywania go w pliku i w historii powłoki):

```bash
read -rsp 'Nowe hasło: ' HASLO; echo
printf '%s:%s\n' <LOGIN> "$(printf '%s' "$HASLO" | openssl passwd -apr1 -stdin)" \
  | kubectl -n f2-prod create secret generic strona-htpasswd --from-file=htpasswd=/dev/stdin --dry-run=client -o yaml \
  | kubectl -n f2-prod apply -f -
unset HASLO
```

Hasło zapisz w menedżerze haseł zespołu. Argo CD nie usunie tego Secretu: nie jest w manifestach w repozytorium.
