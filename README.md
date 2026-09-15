# CTI Chippy News

## Arquitectura

El proyecto consulta tres fuentes:

- GBHackers
- Cyber Security News
- The Hacker News

Para cada fuente consulta siempre ORIGINAL + FEEDBURNER.

Flujo:

```text
ORIGINAL + FEEDBURNER
        ↓
dedup dentro de la misma fuente
        ↓
comparar contra histórico mes actual
        ↓
comparar contra histórico mes anterior
        ↓
comparar contra daily actual
        ↓
solo noticias NUEVAS
        ↓
┌──────────────┬───────────────┬───────────────┐
↓              ↓               ↓
history        daily           allnews.json
mes actual     del día         corrida actual
```

## Estructura

```text
cti_chippy_news/
│
├── config.py
├── rss_common.py
├── dedup_store.py
├── collector_gbhackers.py
├── collector_cybersecuritynews.py
├── collector_thehackernews.py
├── run_all.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── .github/
│   └── workflows/
│       └── cti-rss.yml
│
└── data/
    ├── allnews.json
    ├── feeds/
    │   ├── gbhackers.json
    │   ├── cybersecuritynews.json
    │   └── thehackernews.json
    ├── history/
    │   └── YYYY-MM/
    │       ├── gbhackers.json
    │       ├── cybersecuritynews.json
    │       └── thehackernews.json
    └── daily/
        └── YYYY-MM-DD.json
```

## Archivos

### data/feeds/*.json

Snapshot actual de ORIGINAL y FEEDBURNER. Sirve para comparar ambos endpoints.

No lleva un timestamp cambiante, para evitar commits cuando el contenido no cambia.

### data/history/YYYY-MM/*.json

Histórico mensual por fuente.

La deduplicación consulta:

- mes actual;
- mes anterior.

Una noticia nueva se guarda únicamente en el mes actual.

### data/daily/YYYY-MM-DD.json

Conserva todas las noticias nuevas detectadas durante ese día, mezclando las tres fuentes.

No permite duplicados de la misma fuente.

Retención: 30 días.

### data/allnews.json

Contiene exclusivamente las noticias nuevas de la corrida actual.

Si no hay novedades:

```json
{
  "article_count": 0,
  "sources": {},
  "articles": []
}
```

Así XSOAR no vuelve a procesar artículos de una corrida anterior.

## Deduplicación

Clave principal:

```text
URL normalizada
```

Estos tres ejemplos son el mismo artículo:

```text
http://thehackernews.com/noticia
https://thehackernews.com/noticia/
https://thehackernews.com/noticia?utm_source=test
```

Se normalizan a:

```text
thehackernews.com/noticia
```

Si no existe URL, se usa SHA256 de título + fecha publicada.

## Retención

En config.py:

```python
DAILY_RETENTION_DAYS = 30
HISTORY_RETENTION_MONTHS = 12
```

Daily conserva hoy + los 29 días anteriores.

History conserva el mes actual + los 11 meses anteriores.

## Primera ejecución

Como todavía no hay histórico, todos los artículos actuales se consideran nuevos.

Después quedan guardados en history y daily.

La siguiente corrida solamente produce novedades.

## Cambio de mes

Ejemplo: una noticia capturada el 30 de septiembre todavía aparece el 1 de octubre.

El sistema compara:

```text
history/2026-10/<fuente>.json
+
history/2026-09/<fuente>.json
```

Por eso no vuelve a publicarla.

## Instalación

Desde la raíz del repositorio:

```bash
python -m pip install -r requirements.txt
python run_all.py
```

Luego revisar:

```text
data/allnews.json
data/daily/
data/history/
data/feeds/
```

## GitHub Actions

Workflow:

```text
.github/workflows/cti-rss.yml
```

Corre cada 30 minutos en America/Guayaquil:

```text
00:07
00:37
01:07
01:37
...
```

También puede ejecutarse manualmente desde Actions > CTI Chippy News RSS > Run workflow.

## XSOAR

Para producción, XSOAR debería consumir solamente:

```text
data/allnews.json
```

Lógica:

```text
article_count == 0
→ terminar

article_count > 0
→ procesar articles
```

Los archivos data/feeds son de diagnóstico, no para el flujo principal.

## Noticias similares entre medios

No se deduplican noticias de medios diferentes.

Si GBHackers, Cyber Security News y The Hacker News publican sobre el mismo CVE, se conservan las tres publicaciones.

Una capa posterior de XSOAR/OpenAI puede correlacionarlas semánticamente por CVE, campaña, malware, actor, producto o incidente.
