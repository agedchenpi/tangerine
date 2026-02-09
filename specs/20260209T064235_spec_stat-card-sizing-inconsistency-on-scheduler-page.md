# Fix: Stat card sizing inconsistency on scheduler page

## Context
The 6 stat cards on `/scheduler` have uneven heights because label text varies in length ("Total Schedules" wraps, "Active" doesn't). The card container has no `min-height`, so shorter labels produce shorter cards.

## Change

### `admin/utils/ui_helpers.py` — `render_stat_card()` (~line 716)

Add `min-height: 120px` to the outer card `<div>` style to ensure uniform card sizing across all pages that use this component.

```python
# In the outer div style block, add:
min-height: 120px;
```

This is a single-line CSS addition in the existing inline style block.

## Verification
1. `docker compose up -d --build admin`
2. Visit `/scheduler` — all 6 stat cards should be the same height
