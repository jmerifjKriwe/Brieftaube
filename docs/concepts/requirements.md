# Requirements Specification: Notification Hub

## 1. Goal and Context

Replacement of the existing Home-Assistant-based `universal_notifier` script with a
standalone, Docker-hosted web application that serves as the central message distribution
point for the entire homelab.

Core idea compared to the status quo: sending systems (first and foremost Home Assistant) no
longer need to know *who* receives a notification and *via which channel* — they merely report
*that* something has happened (category/task, priority, content). Resolution to concrete
recipients and channels is handled by the new application, controlled by rules configured by
users and the administrator.

Operating environment: Unraid/Docker, hosted exclusively locally/VPN, no internet exposure
planned.

## 2. Glossary

| Term | Meaning |
|---|---|
| **Category** | Coarse, freely named topic bucket (e.g. "ToDos", "Sicherheit"). Created via upsert on the first arrival of a notification. |
| **Task** | Concrete notification type within a category (e.g. "Haustür-Klingel"). Also upsert. Semantics live in the free text, not in the name. |
| **Context variable** | Generic key/value state, fed from external sources (primarily MQTT/Home Assistant): presence, vacation mode, darkness, etc. |
| **Recipient set** | Base set of recipients: a single user or a group. |
| **Context filter** | Restriction of a recipient set via one or more context variables (e.g. "only those present"). |
| **Combinator** | Way of linking multiple filtered recipient sets: **Union** (all matches in parallel) or **Fallback** (first non-empty tier wins). |
| **Routing preset** | Named combination of recipient sets + filters + combinator, maintained by the administrator. Replaces the old fixed dropdown list, but is freely extensible. |
| **Subscription** | Linking of a category/task to a target — either direct (simple, self-service) or via a routing preset. Multiple active subscriptions per category/task are possible (see 4.4). |
| **Channel type** | Kind of delivery path: Pushover, Signal, Telegram, ntfy, ... |
| **Channel instance** | Concrete configuration of a channel type for a user (e.g. Telegram chat ID, Pushover user key). |
| **Priority** | Urgency level set by the sending application; controls retry/escalation behavior. |
| **Confirmation** | Optional requirement attached to a notification by the sending system: `read` (must be read) or `completion` (associated task must be completed). Tracked individually per recipient. |
| **Context re-routing** | Re-resolution of a routing preset, triggered by a change in a context variable used within it, while a `completion` notification is still open. |

## 3. a) User Management

- There is one **administrator** who creates/manages users.
- Every user has a login (username) + password and can change their own password.
- Users can be grouped into **groups** (n:m relationship), e.g. "Erwachsene",
  "Kinder", "Familie". Groups are the basis for recipient sets in b) and c).
- Role model: **administrator** and **regular user** as the basis. Optional (open, see
  chapter 8): an intermediate role with extended permissions (e.g. being allowed to manage
  routing presets/groups without being a full administrator).

## 4. b) Notification Management

### 4.1 Category/Task Creation

- Categories and tasks are **not registered explicitly**; they are created automatically
  (upsert) as soon as a notification with a previously unknown category/task combination
  arrives for the first time.
- Since no registration call exists, a newly created category/task initially has **no
  description text** — the administrator adds it later in the UI after noticing the new
  notification type (see 4.5 for the catch-all mechanism).

### 4.2 Context Variables

- Generic key/value mechanism, not limited to presence. Examples: person X at home,
  vacation mode active, dark outside.
- Source: primarily MQTT from Home Assistant, but fundamentally kept open to any source
  (later extension without code changes to the notification system — just a new mapping).
- **Staleness handling** required: for each context variable it must be definable from when
  a value counts as stale/unknown (e.g. MQTT connection dead, last state days old).
- Time windows (e.g. "at night") are **not** an external context value, but a built-in filter
  type computed by the system itself (see 4.3). Currently no concrete need, but to be
  provided for structurally.

### 4.3 Recipient Sets, Filters, Combinator, Routing Presets

Replaces the old, hard-coded target group list with a building block system:

1. **Recipient set**: a single user, a group — or a **device-independent channel**
   (example: a hallway speaker that, when the doorbell rings, announces who is currently at
   home regardless of anything else). Adopted as a concept from Ticker ("Device
   Recipients"): technically a `channel_instance` without an associated person, directly
   referenceable as a target.
2. **Context filter** on a recipient set: e.g. "only those present", "only those absent",
   freely extensible with additional context variables (vacation, darkness, ...).
3. **Combinator** across multiple filtered recipient sets:
   - **Union**: all matches from all sets simultaneously.
   - **Fallback**: try the sets in order; the first tier with a non-empty result wins.
4. **Routing preset**: named combination of 1–3, maintained by the administrator (or a user
   with extended permissions). It covers all cases of the old system (individuals, groups,
   presence logic, multi-level fallback chains, hybrid forms of Union+Fallback), but unlike
   the old system it is **freely extensible without code changes**.

There is **no** global condition filter at the subscription level ("suppress notifications
in general") — all control runs exclusively via the recipient set filtering within a preset.

### 4.4 Subscriptions

- A subscription links a category **or** a task to a target:
  - **Simple**: direct target (a user or a group); can be created self-service by any user
    for themselves or for groups in which they are a member.
  - **Preset-based**: selection of a predefined routing preset from a list (analogous to the
    old dropdown selection). Creating/maintaining the presets themselves is an administrator
    function (or a user with extended permissions).
- A category/task can have **multiple active subscriptions at the same time**. These are
  treated as a union (each active rule independently triggers a recipient circle).
- Subscriptions can be **enabled/disabled** in the UI without being deleted or overwritten
  (status flag, no hard delete on deactivation).
- In addition to the permanent active/inactive toggle: **snooze** — a subscription can be
  muted for a limited time (e.g. "no notifications from this category for 2 hours") without
  having to manually re-enable it afterwards. When the period expires, the subscription
  automatically takes effect again. Concept adopted from Ticker.
- Registration is fundamentally possible **at the category level or at the task level**
  (inheritance: a task-level rule can override/complement a category-level rule more
  specifically).

### 4.5 Catch-all Mechanism for Unregistered / New Categories

- A virtual default target group exists for notifications whose concrete category/task does
  not (yet) have an active subscription.
- Every user (not just the administrator) can register for this default.
- As soon as a dedicated subscription exists for a concrete category/task, only the specific
  rule applies to future notifications of this kind, no longer the default pool.

### 4.6 Priority

- Set by the **sending application** when the notification is created.
- Default value: `normal`.
- Concrete value set (proposal, open — see chapter 8): `low`, `normal`, `high`, `critical`.
- Primarily controls the retry/escalation behavior (see 5.3), optionally also
  channel-specific signaling behavior (e.g. Pushover priority, mobile app importance).

### 4.7 Confirmations (Read/Completion) and Context Re-Routing

In addition to pure delivery, there are two optional types of confirmation that a
notification can require. The sending system determines this via `confirmation_type`
(`none` as the default, otherwise `read` or `completion`):

- **`read`**: the notification must be acknowledged as read individually by each addressed
  recipient. Purely individual tracking; a confirmation by person A has no effect on
  person B.
- **`completion`**: the underlying task (e.g. "take out the trash") must be completed.
  Tracking is granular per recipient (everyone has their own status), but confirmation by
  **any one** currently addressed person completes the task for **everyone** at once — after
  all, it is actually done, regardless of who did it.

**Confirmation happens directly in the channel.** Every delivery contains a signed, one-time
confirmation link that works without login (the token itself is the authentication). Channels
with native interaction elements (Telegram inline buttons, ntfy action buttons) invoke the
link in the background; channels without native support (Signal, Pushover) get the same link
appended as clickable text.

**Context re-routing (only with `completion` + preset-based subscription):** While a
`completion` notification is still open, the system watches whether a context variable used
in the associated routing preset changes. On a relevant change, the preset is **resolved
again**. If this yields new recipients (example: "whoever is at home, otherwise the parents" —
the parents come home, the task is still open → the preset now resolves to "the parents",
even though someone else was addressed before), the notification is additionally delivered to
them. This runs in parallel to the existing time-triggered retry mechanism (5.3) — re-routing
reacts to context events, retry/escalation to time.

**Interaction with priority:**
- `normal`/`low` + confirmation required: one-time delivery, no active follow-up. The open
  status is visible in the UI, but there is no repeated delivery or escalation.
- `high`/`critical` + confirmation required: the existing retry/escalation chain (5.3) keeps
  running until either a confirmation arrives or all channels are exhausted. Unlike
  notifications that do not require confirmation, this then does **not** end in a definitive
  "failed" — the full escalation cycle is **repeated** after a pause, indefinitely, until a
  confirmation arrives.

## 5. c) Device/Channel Management

### 5.1 Channel Types & Instances

- **Centrally operated channels** (one bot/server for all users, the user only provides
  their ID): Signal, Telegram, ntfy.
- **Per-user configured channels**: Pushover (own user key per user).
- In principle, a user can create **any number of instances of the same channel type**
  (distinguished by a freely choosable label, e.g. "Pushover Handy", "Pushover Tablet") —
  no more special case for Pushover devices; uniform for all channel types.
- A `channel_instance` can optionally exist **without an associated user** (device
  recipient, see 4.3) — e.g. a hallway speaker or a wall-mounted tablet that is addressed
  independently of a specific person.

### 5.2 Routing: From (User, Category/Task, Priority) to the Channel Set

- Every user defines a **default channel set** (channels used at all times, as a rule).
- Additional rules per user: `condition (category/task and/or priority) → channel set`.
- Rule mode per rule:
  - **additive** (normal case): the channel set is added to the default.
  - **replacing** (special case): the channel set replaces the default set for this match.
- Combination logic when multiple rules apply simultaneously: all applicable additive rules
  plus the default are united (union, no duplicates). If at least one replacing rule
  applies, the default is dropped; additive matches still apply in addition. No ranking
  between rules is needed; everything works via set union.

### 5.3 Delivery: Retry & Escalation

- "Delivered" means: **some channel has technically accepted the message successfully**
  (API success). A real read receipt by the human is not required as a condition (even
  though individual channels such as Pushover could do that natively — that is not a core
  part of the system, but an optional later extension).
- **Retry on the same channel**: applies to **all** priority levels incl. `normal`. Multiple
  attempts with backoff (concrete intervals/count — see chapter 8, open).
- **Escalation to a different channel** after retries are exhausted: only from priority
  `high` and `critical` upward. With `normal`, the status remains "failed" after the
  retries (logging only, no channel switch).
- **Escalation order**: freely configurable per user (sortable list of their own channel
  instances), independent of the channel set determined from category/priority.
- If all of a user's channels exhaust their attempts unsuccessfully → status "failed",
  visible in the UI/log. **Exception**: for notifications requiring confirmation (4.7) with
  priority `high`/`critical`, the escalation cycle is instead restarted after a pause until
  a confirmation arrives.

### 5.4 Delivery Status & Logging

- A separate status per notification **and per recipient**: `pending` / `delivered` /
  `failed` (not just one global status for the entire notification).
- **Delivery attempt log**: one entry per notification × recipient × channel × attempt
  (timestamp, success/error, error message) — the basis for traceability in the UI.
- Requires a background job/queue mechanism (retries are time-deferred, not pure
  request-response). TaskIQ as the obvious candidate, since it is already in use in the
  ecosystem (Narrare).

## 6. d) Security

- Login: username/password with a session cookie; no OAuth/2FA required.
- Password hashing to standard (bcrypt/argon2) — implementation detail.
- **One API key per sending system** (not one global key for everyone), so that sources can
  be attributed in the log/UI and can be rotated/revoked individually.
- Purely local operation/VPN assumed, no internet exposure planned — therefore no
  brute-force protection, rate limiting on login or the like is required.
- Role model as described in 3. (administrator / user, intermediate role optional/open).

## 7. e) Interface / API

### 7.1 Inbound API (from sending systems such as Home Assistant)

`POST /notifications`, authentication via a source-specific API key.

Payload fields (proposal):

| Field | Required | Description |
|---|---|---|
| `category` | yes | Category name; upsert if new |
| `task` | yes | Task name within the category; upsert if new |
| `priority` | no (default `normal`) | Urgency level |
| `confirmation_type` | no (default `none`) | `none` / `read` / `completion` — see 4.7 |
| `title` | no | Title of the notification |
| `message` | yes | Message text |
| `image_url` | no | Image attachment, passed on to channels with image support |
| `thread_key` | no | Update-in-place: identical later notifications with the same key replace/update the previous one, provided the target channel supports that; otherwise a new message is sent unconditionally |
| `data` | no | Free-form JSON for future, channel-specific additional data |

- `category`/`task` are **explicit** top-level fields (not derived from a generic `data`
  structure) so that the upsert behavior works cleanly.
- **Response behavior**: asynchronous. The endpoint acknowledges receipt (e.g. HTTP 202)
  and provides no information about the actual delivery result — processing/retries run in
  the background.
- Optional later extension: `GET /notifications/{id}/status` for querying the delivery
  status by the sending system (currently not prioritized; status inspection happens
  primarily in the application's web UI).

### 7.2 Administrative Functions

- Management of users, groups, categories/description texts, routing presets, and channel
  instances exclusively via the **web UI**; no separate admin API is planned.

## 8. Open Points (deliberately marked as placeholders)

- Concrete retry intervals/backoff values and maximum number of attempts per channel.
- Final priority enum: four levels (`low/normal/high/critical`) vs. a reduced set —
  currently assumed as a proposal with four levels.
- Extended user role between "administrator" and "regular user" (managing routing
  presets/groups without full admin access) — need indicated, but not finally decided.
- `thread_key`/update-in-place: the extent of channel support per adapter (which channels
  can do it natively, which only via "new message") is an implementation detail, to be
  provided for in the first build-out stage.
- Channel health checks (e.g. detecting an invalid bot token before a delivery attempt
  fails) — considered, not elaborated.
- Time window filter (built-in filter type, see 4.2) — mechanics not specified in detail,
  as there is currently no concrete use case.

## 9. Explicitly Not Planned (Non-Goals)

- No subscription-wide condition check independent of recipients (see 4.3).
- No rate limiting for notification dispatch.
- No user-defined quiet hours in the system — this is deliberately left to the respective
  end device/channel.
- No requirement of a real read receipt for the "delivered" status (see 5.3) — real
  confirmations (`read`/`completion`) are a separate, optional property of individual
  notifications (see 4.7), not a general requirement for all.
