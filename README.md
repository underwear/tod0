# todo

Fast, minimal command-line client for Microsoft To-Do

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

```
$ todo tasks
[0]  Buy groceries
[1]  Call mom                     ! (due: tomorrow)
[2]  Review PR #42
     [x] Check tests
     [ ] Add documentation

$ todo new "Deploy v2.0" -d friday -r 9am -I
Created task 'Deploy v2.0' in 'Tasks'

$ todo complete 0
Completed task 'Buy groceries' in 'Tasks'
```

## Why todo?

| | |
|---|---|
| **Natural dates** | `tomorrow`, `1h30m`, `9:30am`, `friday`, `weekly:mon,wed,fri` |
| **Scriptable** | JSON output, stable task IDs, proper exit codes |
| **Fast** | No interactive UI, minimal dependencies, instant results |
| **Complete** | Tasks, lists, subtasks, recurrence, reminders, filters |

## Install

**Requirements:** Python 3.8+

```bash
pip install microsoft-todo-cli
```

Or install from source:

```bash
git clone https://github.com/underwear/microsoft-todo-cli.git
cd microsoft-todo-cli
pip install -e .
```

Then configure Microsoft API access: **[Setup Guide](docs/setup-api.md)** (5 min)

## Quick Start

```bash
todo lists                        # Show all lists
todo tasks                        # Show tasks (default list)
todo new "Buy milk"               # Create task
todo complete "Buy milk"          # Mark done
todo rm "Old task"                # Delete
```

## Usage

### Tasks

```bash
# View
todo tasks                        # Default list
todo tasks Work                   # Specific list
todo tasks --due-today            # Due today
todo tasks --overdue              # Past due
todo tasks --important            # High priority
todo tasks --completed            # Done tasks
todo tasks --all                  # Everything

# Create
todo new "Task name"              # Basic
todo new "Task" -l Work           # In specific list
todo new "Task" -d tomorrow       # With due date
todo new "Task" -r 2h             # With reminder (in 2 hours)
todo new "Task" -d mon -r 9am     # Due Monday, remind at 9am
todo new "Task" -I                # Important
todo new "Task" -R daily          # Recurring
todo new "Task" -R weekly:mon,fri # Recurring on specific days
todo new "Task" -S "Step 1" -S "Step 2"  # With subtasks

# Manage
todo complete "Task"              # Mark complete
todo complete 0 1 2               # Complete by index (batch)
todo uncomplete "Task"            # Reopen task
todo update "Task" --title "New"  # Rename
todo update "Task" -d friday -I   # Change due date, make important
todo rm "Task"                    # Delete (asks confirmation)
todo rm "Task" -y                 # Delete (no confirmation)
```

### Subtasks (Steps)

```bash
todo new-step "Task" "Step text"      # Add step
todo list-steps "Task"                # List steps
todo complete-step "Task" "Step"      # Check off
todo uncomplete-step "Task" "Step"    # Uncheck
todo rm-step "Task" 0                 # Remove by index
```

### Lists

```bash
todo lists                        # Show all lists
todo new-list "Project X"         # Create list
```

### Date & Time Formats

| Type | Examples |
|------|----------|
| Relative | `1h`, `30m`, `2d`, `1h30m` |
| Time | `9:30`, `9am`, `17:00`, `5:30pm` |
| Days | `tomorrow`, `monday`, `fri` |
| Date | `2026-12-31`, `31.12.2026`, `12/31/2026` |
| Keywords | `morning` (7:00), `evening` (18:00) |

### Recurrence Patterns

| Pattern | Description |
|---------|-------------|
| `daily` | Every day |
| `weekly` | Every week |
| `monthly` | Every month |
| `yearly` | Every year |
| `weekdays` | Monday to Friday |
| `weekly:mon,wed,fri` | Specific days |
| `every 2 days` | Custom interval |
| `every 3 weeks` | Custom interval |

## Scripting & Automation

### JSON Output

Add `--json` to any command for machine-readable output:

```bash
# Read commands
todo tasks --json
todo lists --json
todo show "Task" --json

# Write commands return IDs
todo new "Task" --json            # {"action": "created", "id": "AAMk...", ...}
todo complete "Task" --json       # {"action": "completed", "id": "AAMk...", ...}
todo rm "Task" -y --json          # {"action": "removed", "id": "AAMk...", ...}
```

### Task IDs

For reliable scripting, use stable task IDs instead of names or indices:

```bash
# Get task ID from JSON
todo tasks --json | jq '.[0].id'

# Show IDs inline (without full JSON)
todo tasks --show-id

# Use ID in commands
todo complete --id "AAMkADU3..." -l Tasks
todo update --id "AAMkADU3..." --title "New title"
todo rm --id "AAMkADU3..." -l Tasks -y
```

### Aliases

| Alias | Command |
|-------|---------|
| `t` | `tasks` |
| `n` | `new` |
| `c` | `complete` |
| `d` | `rm` |
| `newl` | `new-list` |

```bash
todo t          # = todo tasks
todo n "Task"   # = todo new "Task"
todo c 0        # = todo complete 0
```

## Credits

Forked from [kiblee/tod0](https://github.com/kiblee/tod0) with a redesigned CLI.

## License

MIT
