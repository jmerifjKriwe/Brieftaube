# Implementation Roadmap: Notification Hub

Breakdown into phases following the principle "have something working early, then add
complexity step by step" instead of building everything at once. Each phase is
usable/testable on its own. Cutover from the old `universal_notifier` system can happen
category by category instead of in one big cut — old HA automations therefore keep
running in parallel until their respective category is represented in the new
application.

## Phase 0 — Foundation

No functional benefit to the outside, but the prerequisite for everything that follows.

- Project setup: `pyproject.toml`, project structure from `architecture.md` chapter 6
- SQLAlchemy models 1:1 from `data_model.md`, first Alembic migration
- Auth: login/logout/change password, session cookie
- User management: admin can create users (only `user`/`admin` roles, `power_user` can
  wait)
- Docker Compose scaffold with SQLite volume
- **Definition of Done**: you can log in, the admin can create a second user

## Phase 1 — Walking Skeleton: a notification arrives, a human receives it

Goal: the complete path from HA to the phone works end to end once, with the simplest
possible form of each building block.

- `POST /notifications` incl. API key auth and category/task upsert (no description
  text maintenance, no default fallback mechanism — that comes in phase 2)
- **One** channel type first (suggestion: Telegram — central bot, no per-user setup
  beyond the chat ID, lowest implementation effort)
- Simple subscriptions: a user can register directly (only for themselves, no groups)
  for a category/task
- Exactly one delivery attempt, no retry, no escalation — failure is only logged
- Minimal UI: login, category/task list with own subscriptions on/off, store one's own
  Telegram chat ID
- **Definition of Done**: a real HA automation successfully sends a notification that
  arrives on at least one person's phone

## Phase 2 — Reliability

- Retry loop as described in `architecture.md` chapter 3 (backoff table by priority),
  initially retry on the same channel only (escalation follows in phase 3, since only
  then do multiple channels per user exist in the first place)
- `notification_recipient` status + `delivery_attempt` log
- Default fallback subscription (4.5): unregistered new categories/tasks go to everyone
  who has registered for the default
- UI: view notification history/log (`/notifications-log`)
- **Definition of Done**: a simulated Telegram outage leads to visible retry attempts
  in the log, no more silent data loss

## Phase 3 — Full Channel Flexibility

- Additional channel adapters: Pushover, ntfy, Signal (via `signal-cli-rest-api`
  sidecar)
- Multiple channel instances per user (the generalized label model from the data model
  revision), incl. UI for creating/naming them
- Default channel set (several at once) + additive/replacing `user_channel_rule`s by
  category/task/priority
- Escalation to a different channel from priority `high`/`critical` upward, incl. UI
  for the escalation order (`user_escalation_order`)
- **Definition of Done**: a user can use Pushover+Telegram simultaneously as default,
  a critical notification demonstrably escalates to the next channel when the first
  one is unreachable

## Phase 4 — Groups, Context & Routing Presets

The most functionally demanding part, deliberately postponed, because it builds on an
already running system instead of rebuilding everything at the same time.

- Groups + group membership, simple subscriptions extended to groups as targets
- MQTT consumer + `context_variable` table (initially only presence per person)
- Context filters on recipient sets (only present/absent people), group aggregation
  (any/all/none)
- Routing presets (combinator Union/Fallback) + preset-based subscriptions, restricted
  to admins (or the new role `power_user`, if desired by then)
- Further context variables as needed: vacation mode, darkness
- **Confirmations (read/completion)**: `confirmation_type` at the notification level,
  `confirmation_token`/`read_at`/`completed_at` on `notification_recipient`,
  `/confirm/{token}` endpoint, link attachment in all four adapters (native buttons
  optional at first, may not come until phase 5)
- **Context re-routing**: `notification_watch` table, trigger logic in the MQTT
  consumer, repetition cycle in the retry loop for unconfirmed `high`/`critical`
  notifications — builds directly on the two items above and the routing presets that
  already exist
- **Definition of Done**: the old cases from your original preset list ("Dynamic:
  adults at home, otherwise children at home", etc.) are reproduced 1:1 as routing
  presets and work with real MQTT data; in addition, a real "take out the trash"
  notification is, as a test, correctly confirmed for all addressed persons as soon as
  one of them confirms, and, as a test, escalates again to the parents when they come
  home and the task is still open

## Phase 5 — Polish & Additional Features

Nice-to-have, no blocking need for production use:

- `thread_key`/update-in-place for channels that support it
- Native confirmation buttons instead of a plain text link wherever the channel offers
  it (Telegram inline keyboard, ntfy action button) — functionally covered from
  phase 4 via the link, here only the cosmetic improvement
- Image attachments (`image_url`) in all adapters
- Time window filters (if a need does arise after all, see the open points in the
  requirements document)
- Channel health checks (proactively detect invalid tokens/keys)
- Optional real delivery confirmation (Pushover emergency ack) as additional
  information, without replacing the existing "technical success is enough" model
- **Migration tool** (concept by Ticker): CLI script that searches existing HA YAML
  automations for `universal_notifier` calls and generates
  category/task/subscription suggestions — purely to ease the switch, see
  `architecture.md` chapter 7a
- **Subscription snooze** (concept by Ticker): time-limited muting of individual
  subscriptions via `snoozed_until`, without permanently disabling them
- **Device recipients** (concept by Ticker): `channel_instance` without an associated
  user for permanently installed devices (hallway speaker, tablet), directly
  addressable as a target in simple subscriptions or routing presets
- **Searchable history**: full-text search (`q` parameter) over `/notifications-log`

## The Prioritization Logic Behind This

- Phases 1–2 quickly deliver something useful and already cover part of the old
  categories (those that get by without presence logic — e.g. "always to me").
- Phase 3 makes the system fit for everyday use at all priority levels before the most
  complex functional logic (phase 4) is tackled.
- Phase 4 is the project's actual reason for existing compared to the status quo
  (dynamic presence logic), but deliberately comes only once the scaffold and delivery
  have already been proven and are stable — this way, errors in the routing logic are
  easier to tell apart from delivery failures.
- Phase 5 can be shifted as needed and blocks nothing.

## Migration from the Old System

Recommendation: switch over one category at a time. An HA automation that currently
calls `script.universal_notifier` with `target`/`channel` is switched over to the new
`POST /notifications` call as soon as the corresponding category/task has a working
subscription in the new application that maps the previous target behavior (initially
possibly simplified as a simple subscription, later reproduced as a routing preset in
phase 4). In the meantime, the old script can keep running in parallel for categories
that have not yet been migrated.
