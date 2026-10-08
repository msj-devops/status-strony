# status-strony

Chart Helm strony zespołu. Jeden release to cała aplikacja w jednej przestrzeni nazw:

- **strona** (nginx) z treścią z ConfigMap i panelem `/admin/` za hasłem (HTTP Basic). Treść i konfiguracja nginx są w `files/` (wyrażenia Helma w tych plikach wypełnia `tpl`),
- **healthcheck**: CronJob, który co 5 minut sprawdza stronę i panel (i cele z `healthcheck.cele`) i zapisuje raport `raport.json` na PVC,
- **strona statusu** (nginx): podaje ostatni raport z tego samego PVC, tylko do odczytu,
- **Ingress** dla dwóch hostów: strony i strony statusu.

Wersja chartu: `Chart.yaml` → `version`. Wersja treści strony: `appVersion`.

## Zanim zainstalujesz

1. Klaster z kontrolerem Ingress klasy `traefik` (minikube: dodatek `traefik`) i domyślną StorageClass.
2. **Secret z hasłami panelu** w przestrzeni nazw release'u. Chart go nie tworzy, bo hasła nie trafiają do repozytorium. Domyślna nazwa: `strona-htpasswd`, klucz `htpasswd`, zawartość: plik htpasswd (`login:skrót`, skrót z `openssl passwd -apr1`):

   ```bash
   # plik z hasłami trzymaj poza repozytorium albo w katalogu wykluczonym w .gitignore
   printf '<LOGIN>:%s\n' "$(openssl passwd -apr1)" > ~/sekrety/strona.htpasswd
   kubectl create namespace <PRZESTRZEŃ>
   kubectl create secret generic strona-htpasswd --from-file=htpasswd=$HOME/sekrety/strona.htpasswd -n <PRZESTRZEŃ>
   ```

3. Plik wartości środowiska z co najmniej `login` i hostami (przykłady: `values-dev.yaml`, `values-prod.yaml` obok katalogu `charts/`).

## Instalacja i aktualizacja

```bash
helm upgrade --install strona-dev charts/status-strony -n f2-dev -f values-dev.yaml \
  --rollback-on-failure --timeout 3m
```

Najpierw `f2-dev`, potem tym samym poleceniem z `values-prod.yaml` release `strona-prod` w `f2-prod`. `--rollback-on-failure` czeka, aż wszystko będzie gotowe, a jeśli w ciągu `--timeout` się nie uda, sam wycofuje release do poprzedniej działającej rewizji.

Wycofanie ręczne: `helm history strona-prod -n f2-prod`, potem `helm rollback strona-prod <REWIZJA> -n f2-prod --wait --timeout 3m`. Po wycofaniu przywróć w repozytorium pliki z tej rewizji (`git revert`), żeby repozytorium znów opisywało klaster.

## Wartości

| Klucz | Domyślnie | Opis |
|---|---|---|
| `login` | brak (wymagany) | login GitHub właściciela strony; widoczny na stronie i w panelu |
| `ingress.className` | `traefik` | klasa Ingress dla obu hostów |
| `strona.replicas` | `3` | liczba replik strony |
| `strona.image.repository` | `nginx` | obraz strony (oficjalny nginx) |
| `strona.image.tag` | `1.30-alpine` | tag obrazu strony; zawsze przypięta wersja |
| `strona.host` | `strona.lab.local` | host strony i panelu `/admin/` w Ingressie |
| `strona.resources` | 20m / 32Mi, limit 64Mi | `requests` i `limits` kontenera strony |
| `admin.existingSecret` | `strona-htpasswd` | nazwa istniejącego Secretu z plikiem htpasswd (klucz `htpasswd`); chart go nie tworzy |
| `admin.realm` | `Panel strony` | tekst w okienku logowania przeglądarki |
| `status.host` | `status.lab.local` | host strony statusu w Ingressie |
| `status.image.repository`, `status.image.tag` | `nginx`, `1.30-alpine` | obraz strony statusu |
| `status.resources` | 10m / 16Mi, limit 32Mi | `requests` i `limits` strony statusu |
| `healthcheck.image.repository` | `msjtest/healthcheck` | obraz healthchecka (Twój z Fazy 1, Moduł 06) |
| `healthcheck.image.tag` | `1.0` | tag obrazu healthchecka |
| `healthcheck.schedule` | `*/5 * * * *` | harmonogram CronJoba |
| `healthcheck.cele` | `[]` | dodatkowe cele (`url`, `oczekiwany_status`); stronę główną (200) i panel (401) tego release'u chart sprawdza zawsze |
| `healthcheck.resources` | 20m / 32Mi, limit 128Mi | `requests` i `limits` healthchecka |
| `persistence.existingClaim` | `""` | nazwa istniejącego PVC na raporty; pusta: chart tworzy własny PVC `<release>-raporty` |
| `persistence.size` | `20Mi` | rozmiar PVC tworzonego przez chart |

## Co warto wiedzieć

- **Raporty przeżywają `helm uninstall`.** PVC tworzony przez chart ma adnotację `helm.sh/resource-policy: keep`: Helm go nie usuwa. Ponowna instalacja pod tą samą nazwą release'u znowu go używa. PVC usuwasz ręcznie (`kubectl delete pvc <release>-raporty -n …`), świadomie: z nim znikają raporty.
- **Strona statusu jest gotowa od razu,** choć raportu jeszcze nie ma: sonda gotowości sprawdza tylko, czy nginx przyjmuje połączenia. Pierwszy raport pojawia się po najbliższym uruchomieniu healthchecka; do tego czasu `/raport.json` zwraca 404.
- **Nie zmieniaj obiektów release'u ręcznie** (`kubectl scale`, `kubectl edit`): następny `helm upgrade` zgłosi konflikt. Każda zmiana idzie przez pliki wartości albo chart i `helm upgrade`.
- Nazwy obiektów zaczynają się od nazwy release'u, więc dwa release'y mogą działać w jednej przestrzeni nazw (każdy z innymi hostami).
