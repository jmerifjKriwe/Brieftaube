# Data Model: Notification Hub

This document derives a concrete relational data model from the requirements specification (`requirements.md`).
Wherever the requirements left something open, the modeling decision that was made is explicitly
marked as a comment.

## 1. Users & Groups

### `user`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| username | text, unique | |
| password_hash | text | |
| role | enum: `admin`, `user`, `power_user` | `power_user` as a placeholder for the still-open intermediate role (preset/group management) |
| created_at | timestamp | |

### `group`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| name | text, unique | e.g. "Adults", "Children", "Family" |

### `group_member` (m:n)
| Field | Type |
|---|---|
| group_id | FK → group |
| user_id | FK → user |

## 2. Category & Task

### `category`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| name | text, unique | upsert target when a notification arrives |
| description | text, nullable | maintained by the administrator after the fact |
| created_at | timestamp | |

### `task`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| category_id | FK → category | |
| name | text | |
| description | text, nullable | |
| created_at | timestamp | |

`UNIQUE(category_id, name)`

## 3. Context Variables

### `context_variable`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| key | text, unique | e.g. `person.thorsten.home`, `mode.vacation`, `sun.dark` |
| scope | enum: `global`, `per_user` | **Modeling decision**: distinguishes global values (vacation mode, darkness) from values that exist per person (presence). With `per_user`, `user_ref_id` references the affected person. |
| user_ref_id | FK → user, nullable | only set when `scope = per_user` |
| value | text | current value (bool as "true"/"false" or a free-form string) |
| updated_at | timestamp | |
| stale_after_seconds | int, nullable | from when the value is considered stale/unknown |
| source | text | e.g. `mqtt:home_assistant`, for later troubleshooting |

## 4. Recipient Sets, Filters, Routing Presets

**Modeling decision**: recipient sets and filters are not modeled as standalone, reusable
entities, but directly as a row within a routing preset (`routing_preset_step`) — a recipient
set makes no independent sense outside a preset and does not need to be globally reusable.

### `routing_preset`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| name | text, unique | e.g. "Family at home, otherwise Adults" |
| combinator | enum: `union`, `fallback` | see requirements document 4.3 |
| created_by | FK → user | administrator/power_user |

### `routing_preset_step`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| preset_id | FK → routing_preset | |
| step_order | int | ordering; decisive when `combinator = fallback`, only for UI display when `union` |
| target_type | enum: `user`, `group`, `device_channel` | with `device_channel`, `target_id` points directly to `channel_instance.id` (typically a device recipient without `user_id`); filter/aggregation then effectively do not apply, since there is no per-person context reference |
| target_id | int | depending on `target_type`, points to `user.id`, `group.id`, or `channel_instance.id` |
| filter_context_key | text, nullable | e.g. `home`, `vacation`, `dark` — logical key, not the full `context_variable.key` (see below) |
| filter_expected_value | text, nullable | e.g. `true` |
| group_aggregation | enum: `any`, `all`, `none`, nullable | only relevant when `target_type = group` and a filter is set; controls how aggregation is performed over the per-person context variables of the group members |

**Note on resolving `filter_context_key`**: with `target_type = user`, the `per_user`
context variable of that person is checked directly (e.g. `person.<user>.home`). With
`target_type = group`, the variable is resolved per member and merged via
`group_aggregation`. Global variables (e.g. `mode.vacation`) ignore the person reference and
are checked directly, regardless of `target_type`.

## 5. Subscriptions

### `subscription`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| category_id | FK → category, nullable | |
| task_id | FK → task, nullable | exactly one of `category_id`/`task_id` set (constraint at the application level), or both `NULL` for the default catch-all (see below) |
| is_default_fallback | boolean | **Modeling decision**: instead of a "magic" pseudo-category, the default catch-all from 4.5 is kept as a dedicated flag on a normal subscription row (category_id/task_id remain NULL) |
| subscription_type | enum: `simple`, `preset` | |
| target_type | enum: `user`, `group`, `device_channel`, nullable | only with `subscription_type = simple`; `device_channel` allows directly addressing a device recipient without going through a preset |
| target_id | int, nullable | only with `subscription_type = simple` |
| preset_id | FK → routing_preset, nullable | only with `subscription_type = preset` |
| active | boolean, default true | activate/deactivate without deleting |
| snoozed_until | timestamp, nullable | temporary muting (concept adopted from Ticker); as long as `now() < snoozed_until`, the subscription is skipped during recipient resolution without changing `active` |
| created_by | FK → user | |
| created_at | timestamp | |

Multiple active subscriptions per `(category_id, task_id)` are permitted (no unique constraint
on it) — at runtime they are treated as a union.

## 6. Channels

### `channel_type`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| name | text, unique | `pushover`, `telegram`, `signal`, `ntfy` |

### `channel_instance`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| user_id | FK → user, nullable | `NULL` for a **device recipient** (concept adopted from Ticker) — a channel that is not assigned to any person, e.g. a hallway speaker or a wall-mounted tablet |
| channel_type_id | FK → channel_type | |
| label | text | freely chosen display name, e.g. "Pushover phone", "Pushover tablet", "Telegram private", or for device recipients e.g. "hallway speaker" — needed as soon as multiple instances of the same type exist, and always for device recipients for identification |
| config | JSON | type-specific: `{"chat_id": ...}` (Telegram), `{"user_key": ..., "device": ...}` (Pushover), `{"topic": ...}` (ntfy) |

**Modeling decision (revision)**: originally, "one instance per channel type per user" was
planned, with a separate `pushover_device` entity as a special case for multiple Pushover
devices. That was discarded in favor of a uniform principle: **a user can create any number
of instances of the same channel type** (no more unique constraint on
`(user_id, channel_type_id)`). Each device/chat is thus simply another `channel_instance` row
with its own `label` and its own `config` — referenceable like any other instance in
`user_default_channel`, `user_channel_rule_target`, and `user_escalation_order`. This solves
the Pushover device granularity without a special entity and works identically for all
channel types (e.g. two Telegram chats are also possible, if desired).

## 7. Channel Routing per User (which channels for which notification)

### `user_default_channel`
| Field | Type | Description |
|---|---|---|
| user_id | FK → user | |
| channel_instance_id | FK → channel_instance | |

Composite PK `(user_id, channel_instance_id)` — multiple rows = the default set.

### `user_channel_rule`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| user_id | FK → user | |
| category_id | FK → category, nullable | condition: category |
| task_id | FK → task, nullable | condition: task (more specific than category) |
| min_priority | enum, nullable | condition: priority ≥ threshold |
| mode | enum: `additive`, `replace` | see requirements document 5.2 |

### `user_channel_rule_target`
| Field | Type |
|---|---|
| rule_id | FK → user_channel_rule |
| channel_instance_id | FK → channel_instance |

(n:m, since a rule can address multiple channels at once)

### `user_escalation_order`
| Field | Type | Description |
|---|---|---|
| user_id | FK → user | |
| channel_instance_id | FK → channel_instance | |
| order_index | int | personal escalation order, independent of the rule logic |

## 8. Notifications & Delivery

### `api_source`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| name | text | e.g. "Home Assistant" |
| api_key_hash | text | |
| created_at | timestamp | |

### `notification`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| source_id | FK → api_source | |
| category_id | FK → category | |
| task_id | FK → task | |
| priority | enum: `low`, `normal`, `high`, `critical` | default `normal` |
| confirmation_type | enum: `none`, `read`, `completion` | default `none`, see requirements document 4.7 |
| title | text, nullable | |
| message | text | |
| image_url | text, nullable | |
| thread_key | text, nullable | |
| data | JSON, nullable | |
| created_at | timestamp | |

For history search (concept adopted from Ticker: searchable history), a simple `LIKE` filter
over `title`/`message` in SQLite is sufficient at this data volume, without a dedicated
full-text index table (SQLite FTS5 could be retrofitted later if needed, but is not necessary
for the expected data volume).

### `notification_recipient`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| notification_id | FK → notification | |
| user_id | FK → user | resolved individual recipient (groups are expanded into individuals during processing) |
| status | enum: `pending`, `delivered`, `failed`, `cancelled` | `cancelled` = the task was completed by someone else, no longer relevant for this recipient |
| confirmation_token | text, unique, nullable | only set when `notification.confirmation_type != none`; basis for the confirmation link |
| read_at | timestamp, nullable | set with `confirmation_type = read` |
| completed_at | timestamp, nullable | set with `confirmation_type = completion`; as soon as it is set for **any** recipient of this notification, the notification is considered completed (see `notification_watch`) |
| escalation_cycle_count | int, default 0 | counts full escalation cycles for confirmation-required `high`/`critical` notifications that are repeated (see requirements document 5.3) |

### `delivery_attempt`
| Field | Type | Description |
|---|---|---|
| id | PK | |
| notification_recipient_id | FK → notification_recipient | |
| channel_instance_id | FK → channel_instance | |
| attempt_number | int | |
| status | enum: `success`, `failure` | |
| error_message | text, nullable | |
| attempted_at | timestamp | |
| next_attempt_at | timestamp, nullable | for controlling the retry loop (see architecture document) |

### `notification_watch`

**New, for context re-routing (requirements document 4.7).** Links an open `completion`
notification with the routing preset that originally resolved it, so that on relevant
context changes it can be checked specifically whether re-addressing is needed — without
recomputing all open notifications in full on every MQTT change.

| Field | Type | Description |
|---|---|---|
| id | PK | |
| notification_id | FK → notification | |
| preset_id | FK → routing_preset | only relevant if the triggering subscription was `subscription_type = preset` |
| active | boolean | set to `false` as soon as any `notification_recipient.completed_at` is set for this notification — ends the watch |

**Procedure on context change**: when a `context_variable` changes, all `routing_preset_step`
rows whose `filter_context_key` is affected are looked up, then via those all associated
`routing_preset`, and via those all `notification_watch` rows with `active = true`. For each
hit, the preset is resolved again; for recipients that newly come in, a new
`notification_recipient` entry (plus a first `delivery_attempt`) is created.

## 9. Open Modeling Questions (to be reviewed)

- `is_default_fallback` as a flag on `subscription` vs. a dedicated, fixed system row —
  functionally equivalent; the flag is easier to handle and was therefore chosen.
- `config` as a JSON blob in `channel_instance` is deliberately kept schemaless so that new
  channel types can be added without a migration — validation is done on the application
  side per `channel_type.name`.
- The earlier question "how granularly can a single Pushover device be addressed" is obsolete
  due to the generalized multiple-instances principle (see above) — every device is now an
  independently addressable instance.
- Device recipients (`channel_instance.user_id = NULL`) are treated during recipient set
  resolution as a fixed, always "reachable" recipient — context filters (4.3, e.g. "only
  people present") make no sense for them and are ignored in the routing logic when
  `target_type = device_channel`, instead of raising an error.
- Group expansion (`notification_recipient` per individual instead of per group) means: if
  someone is removed from a group later, this changes nothing about already resolved,
  ongoing notifications — only future ones. This seemed like the most sensible default to me,
  but please double-check whether it matches your expectation.
