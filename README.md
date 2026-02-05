# microsoft-todo-cli

Fast, minimal Microsoft To-Do CLI built for LLM agents, automation, and human use.

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

## Install

**Requirements:** Python 3.10+

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
todo tasks                        # Show tasks from default list
todo tasks Work                   # Show tasks from "Work" list
todo new "Buy milk"               # Create task
todo complete "Buy milk"          # Mark done (or: todo c "Buy milk")
todo rm "Old task"                # Delete
```

**Default list**: The first list returned by Microsoft To-Do API (usually "Tasks"). Specify a list explicitly with `-l ListName` or as a positional argument.

**Short aliases**: `t` (tasks), `n` (new), `c` (complete), `d` (rm) — see [Aliases](#aliases).

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
todo new "Task" -N "Note content"     # With note

# View single task
todo show "Task"                  # Show task details
todo show 0                       # Show by index

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

### Notes

```bash
todo note "Task" "Note content"       # Add/update note
todo show-note "Task"                 # Display note (alias: sn)
todo clear-note "Task"                # Remove note (alias: cn)
```

Notes are text content attached to a task. Use `todo show "Task"` to see the note along with other task details.

### Lists

```bash
todo lists                        # Show all lists
todo new-list "Project X"         # Create list
todo rename-list "Old" "New"      # Rename list
todo rm-list "Project X"          # Delete list (asks confirmation)
todo rm-list "Project X" -y       # Delete list (no confirmation)
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
todo tasks --json
todo lists --json
todo show "Task" --json
```

**Example: `todo tasks --json`**
```json
{
  "list": "Tasks",
  "tasks": [
    {
      "id": "AAMkADU3...",
      "title": "Buy groceries",
      "status": "notStarted",
      "importance": "normal",
      "due_date": null,
      "reminder": null,
      "recurrence": null,
      "steps": []
    },
    {
      "id": "AAMkADU4...",
      "title": "Call mom",
      "status": "notStarted",
      "importance": "high",
      "due_date": "2026-02-06",
      "reminder": "2026-02-06T09:00:00",
      "recurrence": null,
      "steps": [
        {"id": "step1", "name": "Check tests", "completed": true},
        {"id": "step2", "name": "Add documentation", "completed": false}
      ]
    }
  ]
}
```

**Write commands return action confirmation:**
```bash
todo new "Task" --json            # {"action": "created", "id": "AAMk...", "title": "Task", "list": "Tasks"}
todo complete "Task" --json       # {"action": "completed", "id": "AAMk...", "title": "Task", "list": "Tasks"}
todo rm "Task" -y --json          # {"action": "removed", "id": "AAMk...", "title": "Task", "list": "Tasks"}
```

### Task Identification

Tasks can be identified by **name**, **index**, or **ID**. Priority for reliable automation:

| Method | Stability | Use case |
|--------|-----------|----------|
| `--id "AAMk..."` | Stable | Scripts, automation, agents |
| Index (`0`, `1`) | Unstable | Interactive use only |
| Name (`"Task"`) | Unstable | Interactive use, unique names |

```bash
# Get task ID from JSON output
todo tasks --json | jq -r '.tasks[0].id'

# Show IDs inline (human-readable + IDs)
todo tasks --show-id

# Use ID in commands (requires -l for list context)
todo complete --id "AAMkADU3..." -l Tasks
todo update --id "AAMkADU3..." --title "New title"
todo rm --id "AAMkADU3..." -l Tasks -y
```

**Example: Create and complete a task by ID**
```bash
ID=$(todo new "Deploy v2.0" -l Work --json | jq -r '.id')
# ... later ...
todo complete --id "$ID" -l Work
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error (invalid arguments, task not found, API error) |

With `--json`: stdout contains only valid JSON on success. Errors go to stderr.

### Tips for Scripts and Agents

- **Prefer `--id` over names/indexes**: Names can have duplicates (first match wins). Indexes change as tasks are added/completed/reordered.
- **Always use `-l ListName`** with `--id` to specify list context.
- **Capture IDs on creation**: Store the ID from `todo new --json` for later operations.
- **Use `--json` for parsing**: Human-readable output format may change between versions.
- **Use `-y` flag** with `rm` commands to skip confirmation prompts.

## Aliases

| Alias | Command | Alias | Command |
|-------|---------|-------|---------|
| `t` | `tasks` | `d` | `rm` |
| `n` | `new` | `newl` | `new-list` |
| `c` | `complete` | `reopen` | `uncomplete` |
| `sn` | `show-note` | `cn` | `clear-note` |

```bash
todo t                  # = todo tasks
todo n "Task" -d fri    # = todo new "Task" -d fri
todo c 0 1 2            # = todo complete 0 1 2
todo d "Old" -y         # = todo rm "Old" -y
```

## Claude Code

A skill for [Claude Code](https://claude.ai/download) is available:

**[todo skill](https://github.com/underwear/claude-code-underwear-skills/blob/main/skills/todo/SKILL.md)** — enables Claude to manage your Microsoft To-Do tasks directly.

## Credits

Forked from [kiblee/tod0](https://github.com/kiblee/tod0) with a redesigned CLI.

## License

MIT
