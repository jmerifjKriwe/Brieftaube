# Architecture & Tech Stack: Notification Hub

This document describes how `data_model.md` and `api_spec.yaml` are implemented technically.
Guiding principle (see discussion): as lean as possible, no infrastructure that is not justified
by the actual load (single-digit user count, low notification frequency).

## 1. Tech Stack Overview

| Area | Choice | Rationale |
|---|---|---|
| Language/framework | Python 3.13, FastAPI | Natively async, automatically generates an `api_spec.yaml`-compatible OpenAPI spec from code, mature ecosystem for all required HTTP clients |
| Database | SQLite (WAL mode) | Trivially low write load, no separate DB container, no connection configuration |
| ORM | SQLAlchemy 2.0 (async) | Fits SQLite + a later migration option to Postgres, should the load ever grow |
| Migrations | Alembic | Standard companion to SQLAlchemy |
| Templating/frontend | Jinja2 + htmx | Server-rendered, no separate frontend build, no second container |
| Background processing | dedicated asyncio task in the same process | no broker needed at this load (see section 3) |
| MQTT client | `aiomqtt` | async, runs as another background task in the same process |
| Signal integration | `signal-cli-rest-api` (ready-made image) | language-agnostic sidecar container, no Python equivalent is sensibly usable |
| Password hashing | `argon2-cffi` | current standard |
| Sessions | signed cookies (`itsdangerous` or Starlette `SessionMiddleware`) | no server-side session store needed at this user count |

## 2. Process and Container Layout

Only two containers, deliberately minimal:

```
┌─────────────────────────────────────────────┐
│ Container: app                               │
│                                               │
│  FastAPI process (uvicorn, 1 worker)         │
│   ├─ HTTP routes (external + internal,       │
│   │   from api_spec.yaml)                    │
│   ├─ Jinja2/htmx views                       │
│   ├─ Background task: retry/escalation       │
│   │   loop (asyncio, see section 3)          │
│   └─ Background task: MQTT consumer          │
│       (aiomqtt, updates                      │
│       context_variable, see section 4)       │
│                                               │
│  SQLite file on mounted volume               │
└─────────────────────────────────────────────┘
                    │
                    │ HTTP
                    ▼
┌─────────────────────────────────────────────┐
│ Container: signal-cli-rest-api               │
│  (ready-made image, own Signal account)      │
└─────────────────────────────────────────────┘
```

A single uvicorn worker suffices: SQLite does not cope well with high parallel write load from
multiple processes, and the load does not justify multi-process scaling anyway. Retry loop and
MQTT consumer run as `asyncio.create_task(...)` on the FastAPI startup event, in the same event
loop as HTTP handling — no separate process, no broker.

## 3. Retry/Escalation Loop (replaces Redis/TaskIQ)

**Upstream, during recipient resolution of an incoming notification** (before any
`notification_recipient` rows are created at all): subscriptions with `snoozed_until > now()` are
skipped, like inactive ones. Recipient set steps with `target_type = device_channel` directly
return the referenced `channel_instance` as the target, without the detour via the default
channel set/`user_channel_rule` from section 5.2 — after all, a device recipient has no channel
preferences of its own, it *is* the channel.

Instead of a message broker: a simple asyncio task running periodically.

**Flow, every ~10 seconds:**

1. Query: all `delivery_attempt` rows with `next_attempt_at <= now()` and an associated
   `notification_recipient.status = pending`.
2. For each due entry: execute the delivery attempt via the associated `channel_instance`
   (see section 5 for channel adapters).
3. On success: `notification_recipient.status = delivered`, no further attempts.
4. On failure:
   - Within the retry budget for the same channel (count depends on priority, see below):
     create a new `delivery_attempt` entry with an increased `attempt_number` and
     `next_attempt_at` after the backoff interval.
   - Retry budget for this channel exhausted, and priority is `high`/`critical`: pick the next
     channel from `user_escalation_order` (one that has not been tried yet), create a new
     `delivery_attempt` entry for this channel.
   - No further channel left or priority `normal`/`low`: `notification_recipient.status =
     failed` — **except** when `notification.confirmation_type != none` and priority is
     `high`/`critical`: then `escalation_cycle_count += 1`, pause (e.g. 30 minutes,
     configurable) and afterwards run the complete escalation cycle again from channel 1,
     unlimited, until `read_at` or `completed_at` is set or the recipient switches to
     `cancelled` (see 3a).

**3a. Confirmation handling** (in addition to pure delivery success, see requirements document
section 4.7):
- `GET /confirm/{token}` handler: finds the `notification_recipient` via `confirmation_token`,
  sets `read_at` or `completed_at` depending on `notification.confirmation_type`.
- On `completion`: additionally set all other `notification_recipient` rows of the same
  `notification_id` with status `pending` to `cancelled` (no further retry/escalation needed —
  the task is done), plus the associated `notification_watch.active = false`.
- As long as `read_at`/`completed_at` is not set, a notification counts as "open" regardless of
  its technical delivery status — that is the condition driving the retry cycle in step 4 as
  well as the context re-routing (3b).

**3b. Context re-routing** (separate trigger path, triggered by the MQTT consumer, not by the
retry loop): when the MQTT consumer (see section 4) updates a `context_variable`, a check is
made whether a `routing_preset_step` references this key and whether an active
`notification_watch` row exists for it. If so: re-resolve the affected preset; new recipients
(who were not addressed before) get a fresh `notification_recipient` entry including their own
`confirmation_token` and are fed into the retry loop (steps 1–4) as usual.

**Concrete values (proposal, marked as open in `data_model.md` section 8 — provided with a
sensible default here, easily changeable in a configuration constant):**

| Priority | Retries per channel | Backoff | Escalation to next channel |
|---|---|---|---|
| `low` | 1 (no retry) | – | no |
| `normal` | 3 | 30s / 2min / 5min | no |
| `high` | 3 | 30s / 2min / 5min | yes |
| `critical` | 5 | 15s / 30s / 1min / 2min / 5min | yes |

This table lives as a simple Python constant in the code (`RETRY_POLICY`); no separate DB table
is needed, since it does not differ per user/category.

## 4. MQTT Consumer → Context Variables

- An `aiomqtt.Client` subscribes at startup to the configured topics (the mapping topic →
  `context_variable.key` lives in a simple configuration file/table, e.g.
  `homeassistant/person/thorsten/home` → `person.thorsten.home`).
- On an incoming message: update `context_variable.value` and `updated_at` (upsert).
- Staleness is not actively checked in the consumer, but only when a context variable is
  **read** by the routing logic: if `now() - updated_at > stale_after_seconds`, the value
  counts as "unknown" (treated as "condition not met", conservative default).
- Connection drops: `aiomqtt` handles reconnecting; until reconnection, the staleness rule
  applies automatically.
- After every successful update of a `context_variable`, the context re-routing check is
  triggered as well (see section 3, step 3b) — it runs synchronously in the MQTT consumer
  task, because the set to be checked (active `notification_watch` rows with a matching
  `filter_context_key`) is small at this scale and the check is cheap.

## 5. Channel Adapters (Delivery)

One shared interface, one implementation per channel type:

```python
class ChannelAdapter(Protocol):
    async def send(
        self,
        config: dict,
        notification: Notification,
        thread_key_state: str | None,
    ) -> DeliveryResult: ...
```

- **Telegram**: `httpx` against the Bot API (`sendMessage`/`sendPhoto`), `chat_id` from `config`.
- **Signal**: `httpx` against the `signal-cli-rest-api` sidecar container.
- **Pushover**: `httpx` against the Pushover API, `user key` + optional `device` directly from
  the `config` of the respective `channel_instance` (one device = one instance with its own
  `label`, no separate sub-model anymore, see data model revision). Priority is mapped 1:1 onto
  Pushover's own priority system
  (`critical` → Pushover priority `2`/emergency with `retry`/`expire` parameters —
  this is in addition to our own retry logic, not a replacement for it).
- **ntfy**: `httpx` against the ntfy server, `topic` from `config`, priority via the
  `X-Priority` header.
- `thread_key` update-in-place: for channels with support (e.g. Telegram via
  `editMessageText`, if the previously sent `message_id` is known — for this,
  `delivery_attempt` must optionally store the returned provider message ID) an edit is
  executed instead of a new message. Channels without support simply ignore
  `thread_key`.
- **Confirmation link/button** (only when `notification.confirmation_type != none`): every
  adapter appends the `/confirm/{token}` link. Telegram and ntfy support native interaction
  elements (Telegram inline keyboard with a callback to the link, ntfy action button with
  `http` action) and trigger the call directly; Pushover and Signal receive the same link as
  clickable text at the end of the message — functionally identical, just without the button
  look. This way confirmation works uniformly across all channels from the start; native
  buttons are a purely cosmetic refinement per adapter (see roadmap phase 5).

## 6. Project Structure (Proposal)

```
notification-hub/
├── app/
│   ├── main.py                # FastAPI app, startup events for background tasks
│   ├── models.py              # SQLAlchemy models (1:1 from data_model.md)
│   ├── schemas.py             # Pydantic schemas (1:1 from api_spec.yaml)
│   ├── routers/
│   │   ├── notifications.py   # POST /notifications (external)
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── groups.py
│   │   ├── categories.py
│   │   ├── subscriptions.py
│   │   ├── routing_presets.py
│   │   ├── channels.py
│   │   └── notifications_log.py
│   ├── services/
│   │   ├── routing.py         # Recipient set/filter/combinator resolution, incl. snooze check
│   │   │                       # and direct device_channel targets (see data model revision)
│   │   ├── channel_routing.py # Default+rule combination (5.2 from the requirements document)
│   │   ├── delivery.py        # Retry loop logic (see section 3)
│   │   └── context.py         # Staleness resolution, aggregation any/all/none
│   ├── adapters/
│   │   ├── telegram.py
│   │   ├── signal.py
│   │   ├── pushover.py
│   │   └── ntfy.py
│   ├── mqtt_consumer.py
│   └── templates/              # Jinja2, htmx fragments
├── alembic/
├── tests/
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## 7. Docker Compose (Skeleton)

```yaml
services:
  app:
    build: .
    volumes:
      - ./data:/data          # SQLite file lives here
    environment:
      - DATABASE_PATH=/data/notifications.db
      - MQTT_HOST=...
    ports:
      - "8080:8080"
    restart: unless-stopped

  signal-cli-rest-api:
    image: bbernhard/signal-cli-rest-api
    volumes:
      - ./signal-data:/home/.local/share/signal-cli
    environment:
      - MODE=json-rpc
    restart: unless-stopped
```

## 7a. Optional Migration Tool (concept adopted from Ticker)

A one-off CLI script (not part of the running system) that searches existing HA YAML files for
`script.universal_notifier` calls, extracts the `target`/`data.group` values from them, and
outputs them as a suggestion list for initial `category`/`task`/`subscription` entries (e.g.
as JSON, which can then be applied to the API via a one-off import script). Purely a
convenience for the transition, not a core part of the application — see roadmap phase 5.

## 8. Deliberately not included (delimitation against the first proposal)

- No Redis, no message broker.
- No Postgres — migration to it is possible later via SQLAlchemy without model changes if
  needed, should the load ever grow significantly.
- No separate frontend framework/build process.
- No multi-process/multi-worker setup.

## 9. Open Points for the Implementation

- Concrete MQTT topic to context key mapping (configuration format: file vs. DB table).
- `confirmation_token` generation: a random, sufficiently long string (e.g. `secrets.token_urlsafe(32)`)
  suffices given this threat model — no additional HMAC signature needed, since the token is
  one-time anyway and stored uniquely in the DB per `notification_recipient`.
- Pause interval between repeated escalation cycles for unconfirmed `high`/`critical`
  notifications (proposal: 30 minutes, see section 3) — should be configurable, not
  hardcoded.
- Deployment order: `signal-cli-rest-api` requires a one-time manual device linking
  (QR code scan) before production operation — not part of the application itself, but a
  setup step.
