# Brieftaube – Combined Architecture and Concept Feedback

## Overall assessment

Overall, the concept is **ready for implementation**. The architecture is deliberately kept lean for a small, self-hosted homelab notification hub and avoids infrastructure that would not be justified by the expected load.

Particularly coherent are:

- Python/FastAPI + SQLite + SQLAlchemy/Alembic
- a single worker with `asyncio` background tasks
- no Redis, no task queue system and no message broker
- generic channel instance model
- separation of notification recipients and delivery channels
- dynamic routing via routing presets
- context-based recipient resolution
- retry and escalation
- read/completion confirmations
- context re-routing
- gradual cutover from the legacy system

The most important additions concern **group chats**, **context management**, **API-based context delivery**, **bulk heartbeats**, **presence/mode model**, **ntfy as a self-hostable channel** and some minor consistency/implementation details.

---

## 1. Context is its own data source

Presence should not necessarily be coupled to MQTT.

The notification hub should fundamentally treat context as **externally provided state**.

Examples:

```text
person.thorsten / presence = home
person.anna     / presence = away
house            / mode = holiday
house            / darkness = true
house            / occupancy = occupied
```

This allows the sender to deliver context via different transport paths:

1. REST API
2. MQTT
3. possibly further adapters later

The routing engine itself does not know any transport path.

### Recommended separation

```text
Home Assistant / Node-RED
        │
        ├── Notifications ────────┐
        │                          │
        └── Context Updates ──────┤
                                   ▼
                         ┌──────────────────┐
                         │  Brieftaube      │
                         │                  │
                         │ Context Store    │
                         │ Routing Engine   │
                         │ Delivery Engine  │
                         └──────────────────┘
```

This makes MQTT merely **one possible transport method** and not a domain-level requirement.

---

## 2. Context Subjects

Brieftaube should manage subjects as domain entities.

Examples:

```text
person.thorsten
person.anna
person.max
house
```

A subject can have multiple context variables:

```text
person.thorsten
 ├── presence = home
 ├── mode = normal
 └── location = home

house
 ├── occupancy = occupied
 ├── mode = holiday
 └── darkness = true
```

### Subject Discovery

Possible API:

```http
GET /context/subjects
POST /context/subjects
PATCH /context/subjects/{id}
```

Recommendation: **hybrid model**

- Subjects can be created explicitly.
- A context update may automatically create a subject that does not yet exist.
- Routing presets can explicitly select subjects in the UI.

This way, HA/Node-RED does not have to synchronize beforehand in order to transmit a context value.

---

## 3. Context REST API

### Single update

```http
POST /context
```

```json
{
  "subject": "person.thorsten",
  "key": "presence",
  "value": "home"
}
```

### Bulk update

A bulk endpoint should be provided for heartbeats:

```http
POST /context/bulk
```

```json
{
  "updates": [
    {
      "subject": "person.thorsten",
      "key": "presence",
      "value": "home"
    },
    {
      "subject": "person.anna",
      "key": "presence",
      "value": "away"
    },
    {
      "subject": "person.max",
      "key": "presence",
      "value": "home"
    },
    {
      "subject": "house",
      "key": "mode",
      "value": "normal"
    }
  ]
}
```

This is particularly useful for regular heartbeats.

Advantages:

- fewer automations
- fewer HTTP calls
- simple synchronization
- context can be rebuilt in full after a restart of the notification hub
- REST and MQTT can be used in parallel
- multiple context dimensions can be transmitted together

---

## 4. Context is not just `home/not_home`

The data model should **not** hard-wire presence **as a boolean**.

Better:

```text
key   = presence
value = home
```

or:

```text
key   = presence
value = away
```

This makes further states possible:

```text
presence = home
presence = away
presence = work
presence = school
presence = vacation
presence = unknown
```

Independently of this, further context keys can exist:

```text
mode = holiday
mode = vacation
mode = normal

darkness = true
occupancy = occupied
```

The important thing is the separation:

- **Subject** = what are we talking about?
- **Context Key** = which property?
- **Value** = which state?

Example:

```text
subject: person.thorsten
key:     presence
value:   home
```

and:

```text
subject: house
key:     mode
value:   holiday
```

---

## 5. Heartbeat and staleness

Home Assistant or Node-RED can, for example, transmit the current relevant context in a batch every 1–5 minutes.

Example:

```text
every 2 minutes:

POST /context/bulk

person.thorsten  → presence=home
person.anna      → presence=away
person.max       → presence=home
house            → mode=normal
house            → darkness=true
```

Every context value needs:

```text
updated_at
```

and optionally:

```text
stale_after_seconds
```

An outdated value should be treated as:

```text
unknown
```

and not automatically as `away`.

This prevents an outage of HA/Node-RED from inadvertently signaling absence.

---

## 6. Distinguish logical groups and provider group chats

There are two different kinds of groups.

### Logical Group

A group of Brieftaube users:

```text
Family
 ├── Thorsten
 ├── Anna
 └── Max
```

It serves recipient resolution and context filtering.

### Provider Group Chat

An actual group chat:

```text
Signal → group "Family"
Telegram → group "Family"
```

A routing preset should be able to address both.

---

## 7. Provider group chats

The existing `channel_instance` model can be extended for this.

Signal example:

```json
{
  "type": "group",
  "group_id": "..."
}
```

Telegram example:

```json
{
  "type": "group",
  "chat_id": "-1001234567890"
}
```

A group chat thus becomes an independent delivery target.

Example:

```text
Notification
    ├── Thorsten → Signal private
    ├── Anna     → Signal private
    └── Family   → Signal group chat
```

This makes additive deliveries possible.

---

## 8. Signal and Telegram

Both adapters should support at least the following target types:

```text
direct
group
```

Telegram:

- private chat
- group
- supergroup

Signal:

- individual contact
- group

The provider-specific IDs remain hidden inside the respective adapter.

---

## 9. ntfy as an additional channel

ntfy is treated as a full-fledged channel adapter.

Important: Brieftaube must **not** assume exclusively `ntfy.sh`.

An ntfy instance needs at least:

```json
{
  "base_url": "https://ntfy.example.org",
  "topic": "family"
}
```

or:

```json
{
  "base_url": "http://192.168.1.50:8080",
  "topic": "family"
}
```

This supports:

- public ntfy
- self-hosted ntfy
- internal HTTP endpoint
- reverse proxy
- multiple ntfy servers

Optional:

```json
{
  "base_url": "https://ntfy.example.org",
  "topic": "family",
  "username": "...",
  "password": "..."
}
```

Secrets must never appear in UI logs or regular delivery logs.

### ntfy is not a real group chat

Technically, an ntfy topic is not a group chat like Signal or Telegram.

Functionally, however, it can represent a shared target:

```text
ntfy topic: family
```

Therefore the semantics should stay clean:

```text
Signal group   = real group chat
Telegram group = real group chat
ntfy topic     = shared push channel
```

---

## 10. Recommended channel instance model

`channel_instance`:

```text
id
user_id nullable
channel_type_id
label
instance_type
config
```

`instance_type`:

```text
user
device
group
```

Examples:

```text
Telegram / user
Telegram / group
Signal / user
Signal / group
ntfy / device
ntfy / group
Pushover / user
Pushover / device
```

Alternatively, `instance_type` could be derived from `config`. However, an explicit field is clearer for UI and validation.

---

## 11. Recipient resolution

Recommended order:

```text
Notification
    │
    ▼
Determine subscriptions
    │
    ├── Simple User
    ├── Simple Group
    ├── Channel Instance
    └── Routing Preset
    │
    ▼
Check snooze / active
    │
    ▼
Apply context filters
    │
    ▼
Expand logical groups
    │
    ▼
Remove duplicate targets
    │
    ▼
User → Channel Routing
    │
    ▼
Channel Instances
    │
    ▼
notification_recipient
    │
    ▼
delivery_attempt
```

A directly addressed group chat is already a concrete delivery target and does not need to go through personal user-channel routing.

---

## 12. Deduplication

Example:

```text
Family group
+
Thorsten
```

and Thorsten is a member of the logical group.

In the case of a group chat, the following is explicitly possible:

```text
Signal Family       ✓
Thorsten private    ✓
```

If, on the other hand, the same person ends up on the same channel through multiple logical groups, they should not be notified multiple times via the same channel instance.

Deduplication therefore by:

```text
(user_id, channel_instance_id)
```

or, for direct channel targets:

```text
channel_instance_id
```

---

## 13. Permission matrix

A clear permission matrix should be documented before implementation.

| Function | user | power_user | admin |
|---|---:|---:|---:|
| own channel instances | ✓ | ✓ | ✓ |
| own subscriptions | ✓ | ✓ | ✓ |
| group membership | ✓ | ✓ | ✓ |
| manage groups | – | optional | ✓ |
| create provider groups | – | optional | ✓ |
| routing presets | – | ✓ | ✓ |
| API Sources | – | – | ✓ |
| read context subjects | ✓ | ✓ | ✓ |
| context configuration | – | optional | ✓ |

The exact role of `power_user` can remain open for now.

---

## 14. Behavior on an empty recipient set

After context filtering, a recipient set can be empty.

Example:

```text
all adults
Filter: presence = home
```

and nobody is at home.

The notification should still be stored.

Important:

**Having no recipients is not a technical error.**

The history should show:

```text
No recipients after routing
```

---

## 15. Retry and escalation

The existing retry approach remains sensible.

Recommended indexing:

```text
delivery_attempt(next_attempt_at, status)
notification_recipient(status)
```

Escalation cycles for unacknowledged `high`/`critical` notifications remain sensible.

The pause interval should be configurable.

---

## 16. Tech stack

The existing stack should largely be retained.

### Backend

```text
Python 3.13
FastAPI
Pydantic 2
SQLAlchemy 2.0
Alembic
SQLite WAL
```

### HTTP

```text
httpx
```

for Telegram, Signal, Pushover and ntfy.

### Async

```text
asyncio
```

for the retry loop, MQTT and provider calls.

### MQTT

```text
aiomqtt
```

MQTT is an **optional context transport**, not a domain-level requirement.

### Frontend

```text
Jinja2
htmx
```

No separate frontend framework required.

### Security

```text
argon2-cffi
itsdangerous / Starlette SessionMiddleware
secrets
```

### Tests

```text
pytest
pytest-asyncio
httpx
```

Particularly important are tests for:

- recipient resolution
- context filters
- group aggregation
- fallback
- escalation
- deduplication
- context re-routing
- provider errors

### Deployment

```text
Docker
Docker Compose
```

SQLite remains the right choice for the expected load.

---

## 17. Adapter structure

```text
ChannelAdapter
├── TelegramAdapter
├── SignalAdapter
├── PushoverAdapter
└── NtfyAdapter
```

Interface:

```python
class ChannelAdapter(Protocol):
    async def send(
        self,
        config: dict,
        notification: Notification,
        thread_key_state: str | None,
    ) -> DeliveryResult:
        ...
```

The routing engine does not know any provider details.

---

## 18. Roadmap adjustment

### Phase 0 – Foundation

- project setup
- data model
- Alembic
- auth
- user management
- Docker
- SQLite

### Phase 1 – Walking Skeleton

- Notification API
- Telegram
- personal Telegram chat
- Simple Subscription
- basic UI

### Phase 2 – Reliability

- Retry
- Delivery Logs
- Default Fallback
- Notification History

### Phase 3 – Channels & Direct Targets

- Signal
- Pushover
- ntfy
- multiple channel instances
- self-hosted ntfy with configurable `base_url`
- Telegram Groups
- Signal Groups
- direct device/topic targets
- Default Channel Sets
- Channel Rules
- Escalation

### Phase 4 – Dynamic Routing & Context

- Logical Groups
- Context Subjects
- Context Variables
- REST Context API
- Bulk Context API
- MQTT Context Adapter
- Heartbeat
- Presence
- Vacation/Holiday/Mode
- Staleness
- any/all/none
- Routing Presets
- Context Re-Routing
- Read/Completion
- Confirmation
- Escalation cycles

### Phase 5 – Polish

- `thread_key`
- native buttons
- images
- Channel Health
- Migration Tool
- Snooze
- searchable history
- further context adapters

---

## 19. GitHub description

The previous description has become somewhat too narrow because it presents MQTT as the central context source.

### Recommended repository description

> **A lightweight, self-hosted notification hub for homelabs. Decouples senders like Home Assistant and Node-RED from Telegram, Signal, Pushover and self-hosted ntfy, with context-aware routing, groups, group chats, retries, escalation, read receipts and task completion tracking. Docker-ready.**

### Longer README description

> **Brieftaube is a lightweight, self-hosted notification hub for homelabs. It decouples senders like Home Assistant and Node-RED from delivery channels such as Telegram, Signal, Pushover, and self-hosted ntfy. It supports dynamic context-aware routing, groups and group chats, retries, multi-stage escalation, read receipts, and task completion tracking. Context can be supplied through REST or MQTT, making presence, vacation, and other household states available for flexible routing. Docker-ready and designed for small, reliable deployments.**

The short variant is better suited for the GitHub repository description.

---

## 20. Overall conclusion

The original architecture does not need to be fundamentally changed.

The most important evolution is the **separation between domain context and its transport**:

```text
                    ┌───────────────┐
                    │ Home Assistant│
                    └───────┬───────┘
                            │
                    REST / MQTT
                            │
                    ┌───────▼───────┐
                    │ Context Store │
                    └───────┬───────┘
                            │
                    ┌───────▼───────┐
                    │ Routing Engine│
                    └───────┬───────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
       Users           Logical Groups    Direct Targets
          │                 │                 │
          ▼                 ▼                 ▼
      Telegram          Signal Group       ntfy Topic
      Signal            Telegram Group     Device
      Pushover
      ntfy
```

This way, Brieftaube does not become a "Home-Assistant-MQTT-Notifier", but an independent notification and routing platform in which Home Assistant is merely one possible source of notifications and context.

That is the more sensible long-term architecture.
