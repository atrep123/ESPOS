# Web UI Designer & Backend – Setup & Examples

Tento dokument popisuje, jak spustit prototyp webového UI Designeru postavený nad FastAPI backendem a jak jej integrovat do existujícího workflow (JSON → C → firmware).

## 1. Závislosti

Backend používá volitelné závislosti:

```bash
pip install fastapi uvicorn
```

Pro build/flash přes `ui_pipeline.py` je potřeba mít:

- PlatformIO CLI (`pio` nebo `platformio` v PATH),
- Python závislosti projektu (viz `requirements.txt`, `pyproject.toml`).

## 2. Start backendu

Backend je definován v `web_designer_backend.py` a poskytuje:

- REST API: `/api/projects`, `/api/projects/{id}`, `/api/projects/{id}/design`, `/api/projects/{id}/build`
- WebSocket: `/ws/projects/{id}` (broadcast kanál pro collaborative editing)

Základní spuštění:

```bash
python web_designer_backend.py
```

Implicitně se spustí na `http://127.0.0.1:8000`.

### 2.1 Povolení buildů (export → build → flash)

Endpoint `POST /api/projects/{id}/build` je z bezpečnostních důvodů vypnutý. Pro lokální vývoj jej povolíš:

```bash
export ESP32OS_WEB_BUILD_ENABLED=1
python web_designer_backend.py
```

Bez tohoto nastavení vrací backend `503 Service Unavailable` pro build endpoint.

### 2.2 Volitelný API key (production guard)

Pro nasazení do sdíleného prostředí můžeš build endpoint chránit jednoduchým API klíčem:

```bash
export ESP32OS_WEB_BUILD_ENABLED=1
export ESP32OS_WEB_API_KEY="secret-token-123"
python web_designer_backend.py
```

- Backend pak vyžaduje pro `POST /api/projects/{id}/build`:
  - HTTP header: `X-ESP32OS-Key: secret-token-123`, nebo
  - query parametr: `?api_key=secret-token-123`.

Bez správného klíče vrací `401 Invalid API key`.

> Poznámka: Ostatní REST/Ws endpointy (list/get/put designu, WebSocket kolaborace) jsou v prototypu veřejné – pro production nasazení zvaž:
> - TLS terminaci (HTTPS),
> - autentizaci před reverzním proxy (OAuth2/OpenID, reverse-proxy auth),
> - omezení přístupu na interní sítě / VPN.

## 3. Webový klient – `web/designer.html`

Frontend je čistý HTML/JS soubor, který mluví s backendem:

- REST: `http://127.0.0.1:8000/api/...`
- WebSocket: `ws://127.0.0.1:8000/ws/projects/{id}`

### 3.1 Spuštění klienta

Nejjednodušší je otevřít soubor přímo v prohlížeči:

- `web/designer.html` (např. `Ctrl+O` → soubor).

Nebo spustit jednoduchý HTTP server v kořeni repa:

```bash
python -m http.server 8080
```

a pak otevřít:

- `http://127.0.0.1:8080/web/designer.html`

### 3.2 Základní workflow

1. Ujisti se, že běží backend na `http://127.0.0.1:8000`.
2. Otevři `web/designer.html`.
3. V levém panelu:
   - nech `Backend URL` jako `http://127.0.0.1:8000`,
   - klikni **Refresh projects** (měla by se zobrazit prázdná nebo existující lista).
4. V sekci **New project**:
   - vyplň `ID` (např. `dashboard_main`),
   - `Width`/`Height` (např. `128 x 64`),
   - klikni **Create project**.
5. V seznamu projektů klikni na nový projekt:
   - střední panel načte `design.json` (JSON struktura scén + widgetů kompatibilní s `UIDesigner`).
6. Uprav JSON podle potřeby (zatím ručně):
   - použij **Format JSON** pro přehlednost,
   - **Save + Broadcast**:
     - provede `PUT /api/projects/{id}/design`,
     - pokud je připojen WebSocket, odešle `design_update` ostatním klientům.

### 3.3 Collaborative editing (více klientů)

1. Spusť backend (`web_designer_backend.py`).
2. Otevři `web/designer.html` ve dvou oknech/prohlížečích.
3. V obou:
   - nastav stejný `Backend URL`,
   - vyber stejný projekt.
4. Vpravo v sekci **Collaboration**:
   - klikni **Connect live** v obou klientech.
5. V jednom okně proveď změny v JSONU a klikni **Save + Broadcast**:
   - druhé okno:
     - obdrží zprávu `design_update` přes WebSocket,
     - přepíše svůj JSON na novou verzi,
     - zobrazí info o tom, který `Client ID` změnu poslal.

> Zjednodušení: Aktuální implementace jede v režimu *last-writer-wins* bez CRDT/OT. Frontend přepisuje celý JSON design – to je v pohodě pro menší projekty a první iteraci.

## 4. Napojení na C/ESP32 firmware (build trigger)

Webový designer je napojený na `ui_pipeline.py` přes backend endpoint:

- `POST /api/projects/{id}/build?env=...&port=...`

### 4.1 Lokální použití

1. Povolit buildy:

```bash
export ESP32OS_WEB_BUILD_ENABLED=1
python web_designer_backend.py
```

2. V prohlížeči:
   - otevři `web/designer.html`,
   - vyber projekt,
   - v pravém panelu **Firmware build** nastav:
     - `Env` – např. `esp32-s3-devkitm-1` (viz `platformio.ini`),
     - `Port` – např. `COM3` nebo `/dev/ttyUSB0` (pokud chceš flash).
   - klikni **Build + optional flash**.

3. Backend provede:
   - `ui_pipeline.py run-all --design ui_projects/<id>/design.json --env <env> [--port <port>]`
   - tj.:
     - export C layoutu (přes `UIDesigner` + `ui_export_c.py`),
     - PlatformIO `pio run -e <env>`,
     - volitelně upload/flash.

4. Výsledek:
   - návratový kód build pipeline (`returncode`) je vrácen v JSONu,
   - frontend ho loguje v panelu **Collaboration** (`Build finished (code X)`).

### 4.2 Bezpečnostní doporučení

Pro real-world nasazení:

- **Nikdy** nepublikuj build endpoint do internetu bez ochrany.
- Vždy nastav:
  - `ESP32OS_WEB_BUILD_ENABLED=0` (default) na prostředích, kde se buildy nemají spouštět,
  - `ESP32OS_WEB_API_KEY` pro prostředí, kde buildy potřeba jsou (CI runner, interní lab).
- Zvaž, aby webový backend běžel za reverzním proxy (nginx, Traefik) s:
  - TLS (HTTPS),
  - autentizací (Basic auth, OAuth2, enterprise SSO),
  - rate-limit / IP allowlist.

## 5. Testování & Integration Testy

V repu jsou základní testy pro backend:

- `test_web_designer_backend.py` – ověřuje helpery `_list_projects` a `_summarize_design`.
- `test_web_designer_collab.py` – integration testy WebSocket broadcastu/zpráv:
  - používá `pytest.importorskip("fastapi")` a `fastapi.testclient.TestClient`,
  - ověřuje, že zpráva poslaná přes `/ws/projects/{id}` se doručí dalším klientům (collaboration workflow).

Spuštění testů:

```bash
python -m pytest -q
```

> Pokud FastAPI/TestClient nejsou v prostředí dostupné, WebSocket testy se automaticky přeskočí (budou označené jako `skipped`), aby neblokovaly běžný CI.

## 6. Další směry rozšíření

- Přidat vizuální canvas (ASCII preview) nad JSON modelem:
  - reuse logiky z `ui_designer_preview.py` nebo `ui_components_library_ascii.py`,
  - případně se napojit na běžící simulátor (`sim_run.py` + `esp32_sim_client.py`) a zobrazit „živý“ ASCII framebuffer v prohlížeči.
- Přidat správu šablon a komponent:
  - REST API pro listování/uložení šablon,
  - UI pro vkládání komponent (paleta v levém panelu).
- Zpřísnit auth:
  - per-user session (JWT, cookies),
  - mapování uživatel ↔ projekty,
  - audit log změn designů.

