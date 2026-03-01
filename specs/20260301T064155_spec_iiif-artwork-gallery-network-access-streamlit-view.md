# Plan: IIIF Artwork Gallery — Network Access + Streamlit Viewer

## Context
Images were downloaded from Smithsonian and Getty IIIF APIs and saved to the local filesystem
(`/opt/tangerine/.data/etl/images/iiif/`). The user wants to (1) understand how to reach
those images from other machines on the local network, and (2) build a dedicated Streamlit
page in the admin app for browsing and viewing the artwork collection.

---

## Part 1: Network Access (no code changes needed)

### Accessing the Streamlit app from another machine
The admin service is already bound to `0.0.0.0:8501` — it accepts connections from any
interface. Any machine on the same LAN can open:
```
http://<server-ip>:8501
```
Find the server's LAN IP with: `ip route get 1 | awk '{print $7}'` or check your router.

### Accessing raw image files from another machine
Images live on the host at `/opt/tangerine/.data/etl/images/iiif/`. Three options:

| Option | How | Best for |
|---|---|---|
| **Streamlit viewer** (this plan) | Via the new gallery page | Browsing/viewing artworks |
| **Python static server** | `python3 -m http.server 8888 --directory /opt/tangerine/.data/etl/images/iiif/` on the server | Quick ad-hoc HTTP access to raw files |
| **Network share** | Expose via SMB/NFS | Direct filesystem access from another OS |

For the Streamlit viewer, no extra server is needed — `st.image()` reads the file directly
from the container's mounted volume.

---

## Part 2: Streamlit Artwork Gallery Page

### Files to create/modify

| File | Action |
|---|---|
| `admin/services/artwork_service.py` | **Create** — DB queries for artworks + provenance |
| `admin/pages/artwork_gallery.py` | **Create** — gallery page |
| `admin/app.py` | **Modify** — register page under "Collections" group |

---

### `admin/services/artwork_service.py`

Two functions:

```python
def get_artworks(source=None, rights=None, topic=None) -> list[dict]:
    """Return artwork records with optional filters."""
    # Query feeds.tiiif_artwork
    # source filter: datasource via JOIN to dba.tdataset / dba.tdatasource
    #   OR filter by manifest_id pattern (FS- = Freer, uuid = Getty)
    # rights filter: WHERE metadata_usage = %s
    # topic filter: WHERE %s = ANY(topics)
    # Returns: all columns needed for gallery + detail view

def get_provenance(artwork_id: int) -> list[dict]:
    """Return ordered provenance chain for one artwork."""
    # SELECT * FROM feeds.tiiif_provenance WHERE artwork_id = %s ORDER BY sequence_order
```

**DB access:** `fetch_dict` from `common.db_utils` — matches all existing service patterns.

---

### `admin/pages/artwork_gallery.py`

**Layout:**
```
[Page header: "Artwork Gallery"]

[Sidebar filters]
  - Source: All / Freer Gallery / Getty Museum
  - Rights: All / CC0 / Not determined
  - Topic: text input (ANY match)

[Main area]
  [N artworks found]

  [3-column grid]
    [col1]              [col2]              [col3]
    st.image(path)      st.image(path)      st.image(path)
    Title               Title               Title
    Accession #         Accession #         Accession #
    [View Details ▼]    [View Details ▼]    [View Details ▼]

    [expander]
      Medium, Date, Period, Origin, Artist
      Topics: badge list
      [Provenance table]
        seq | holder | dates | notes
```

**Image loading:**
```python
IMAGE_DIR = Path('/app/data/images/iiif')

img_path = IMAGE_DIR / record['local_filename']
if img_path.exists():
    st.image(str(img_path), use_container_width=True)
else:
    st.image(record['image_url'], use_container_width=True)  # fallback to original URL
```

**Identifying source** (no JOIN needed — pattern match on manifest_id):
- `manifest_id` starts with `FS-` → Freer Gallery of Art (Smithsonian)
- `manifest_id` is a UUID pattern → Getty Museum

---

### `admin/app.py` — register new page

Add a "Collections" group before "System":
```python
"Collections": [
    st.Page("pages/artwork_gallery.py", title="Artwork Gallery", icon="🖼️"),
],
```

---

## Verification

```bash
# Rebuild admin container (new page file)
docker compose build admin && docker compose up -d admin

# Open from local machine
open http://localhost:8501

# Open from another LAN machine
open http://<server-ip>:8501
# Navigate to "Artwork Gallery" in sidebar

# Confirm all 4 artworks display with images, filters work,
# provenance expander shows correct chain
```
