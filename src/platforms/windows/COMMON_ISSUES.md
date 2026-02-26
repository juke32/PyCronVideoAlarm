# Common Coding Issues - Windows Platform

A running list of bugs encountered and lessons learned during development.

---

## 1. Treeview Tuple Unpacking Crash (Silent Death)

**Date:** 2026-02-15  
**Severity:** Critical (function silently does nothing)  
**File:** `src/ui/main_window.py` → `delete_selected_alarm()`

### What Happened
The delete button appeared to do nothing when an alarm was selected. No error, no log, no popup. The "select an alarm" warning worked (when nothing was selected), so the button *was* wired correctly — but any actual delete attempt silently crashed.

### Root Cause
The alarm list Treeview has **4 columns** (`time`, `sequence`, `days`, `enabled`), but the code tried to unpack the row values into **3 variables**:

```python
# BROKEN — 4 values into 3 variables = ValueError!
time_str, sequence, _ = values
```

Python raises `ValueError: too many values to unpack` and since there was no `try/except`, the function just died.

### The Fix
Use **index access** instead of tuple unpacking, and always wrap in `try/except`:

```python
# CORRECT — safe index access
time_str = values[0]
sequence = values[1]
```

### Prevention Rules
1. **Never use tuple unpacking on Treeview values.** If a column is added or removed later, unpacking breaks silently.
2. **Always wrap Treeview value access in `try/except`** with `logging.exception()` so crashes are never silent.
3. **When a button "does nothing", check for silent exceptions** — add logging around the function to find where it dies.

---

## 2. Spaces in Task Scheduler Filenames

**Date:** 2026-02-14  
**Severity:** High (alarms can't be deleted)  
**File:** `src/platforms/windows/scheduler.py`

### What Happened
Creating an alarm for a sequence named "New Sequence" would create a Task Scheduler entry with spaces in the task name. Deleting it would fail because the filename matching logic couldn't handle spaces.

### Root Cause
The task name was constructed directly from the sequence name without sanitization:
```python
task_name = f"{sequence_name}_{alarm_time.strftime('%H_%M')}"
# Result: "New Sequence_06_43" — spaces in filename!
```

### The Fix
- **Sanitize filenames**: Replace spaces with underscores for the task filename
- **Store metadata**: Put the real sequence name in the Task Description field as `PyCron|Sequence Name|06:43`
- **Match on metadata first**, fall back to filename parsing for legacy tasks

### Prevention Rules
1. **Never use user input directly in filenames** — always sanitize (replace spaces, special chars).
2. **Store identification metadata separately** from the filename so matching is reliable.
3. **Always include fallback matching** for backward compatibility with old entries.

---

## 3. Double-Escaped Newlines in f-strings

**Date:** 2026-02-15  
**Severity:** Low (cosmetic)  
**File:** `src/ui/main_window.py`

### What Happened
Error popups showed literal `\n` text instead of actual newlines.

### Root Cause
Using `\\n` inside an f-string when `\n` was intended:
```python
# BROKEN — shows literal \n in the popup
messagebox.showerror("Error", f"Failed:\n{msg}")  # ← if this was \\n

# CORRECT
messagebox.showerror("Error", f"Failed:\n{msg}")
```

### Prevention Rules
1. In f-strings, `\n` = newline, `\\n` = literal backslash-n.
2. Always test error dialogs visually to catch formatting issues.

---

## General Windows Platform Tips

- **Task Scheduler API** uses 1-based indexing (`tasks.Item(1)` not `tasks.Item(0)`)
- **COM objects** (`win32com.client`) can throw cryptic errors — always wrap in try/except
- **`ctypes` power flags** need to be combined with bitwise OR, and `ES_CONTINUOUS` must always be included
- **Silent failures are the worst bugs** — always add `logging.exception()` in except blocks, never use bare `except: pass` in user-facing code
