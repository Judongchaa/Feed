# Feed: Textual RSS TUI

A terminal-based RSS reader built with Python and the Textual framework. This application allows you to subscribe to RSS and YouTube feeds, organizes content into a hierarchical folder structure, and stores every article as a local Markdown file.

## Purpose
The goal of this application is to provide a clean, distraction-free environment for reading RSS feeds while maintaining a local, searchable archive of articles in a standard format (Markdown).

## Installation & Usage

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the App**:
   - Locally: `python app.py`
   - Anywhere (Global Command): Type `feed` from any directory in your terminal.

## Global Command Setup
The `feed` command is a wrapper script located in `~/.local/bin/feed`. It automatically handles changing directories to ensure your configuration and RSS data remain centralized in the project folder.

## File Structure

```text
Feed/
├── app.py           # Main Entry Point & TUI Implementation
├── logic.py         # Business Logic (Fetching, Parsing, Saving)
├── models.py        # Data Models & Configuration Management
├── config.yml       # Subscription & Settings Configuration
├── requirements.txt # Project Dependencies
└── rss_data/        # Local Database (Auto-generated)
    └── [Tag]/
        └── [Subtag]/
            └── [YYYY-MM-DD]_[Feed]_[Title].md
```

### Components

- **`app.py`**: 
    - Implements the `FeedApp` class using Textual.
    - Manages the layout (Header, Sidebar, Content, Footer).
    - Handles UI events like file selection, button clicks, and keyboard shortcuts (`u` for update, `a` for add).
    - Uses a `DirectoryTree` for navigation and a `Markdown` widget for reading.

- **`logic.py`**:
    - **Fetch Worker**: Asynchronously retrieves XML data from feed URLs.
    - **Parser**: Extracts titles, authors, and content using `feedparser`.
    - **Sanitization**: Uses `python-slugify` to create safe, cross-platform filenames.
    - **Converter**: Transforms HTML content into clean Markdown using `markdownify`.
    - **Storage**: Writes files with YAML frontmatter for metadata compatibility with other tools (like Obsidian).

- **`models.py`**:
    - Defines `FeedConfig` and `AppConfig` dataclasses.
    - Handles serialization/deserialization to `config.yml` using `PyYAML`.

- **`config.yml`**:
    - The source of truth for the application.
    - Stores the `data_dir` location and the list of subscribed feeds with their respective tags and subtags.

## Application Logic

### 1. Boot Sequence
- The app loads `config.yml` to initialize internal state.
- It ensures the `data_dir` (default: `./rss_data`) exists.
- The `DirectoryTree` is mounted to point at the data directory, instantly reflecting your local archive.

### 2. The Fetch Worker
- Triggered by the "Update Feeds" button or the `u` key.
- Spawns an asynchronous task (`@work`) to fetch all feeds in parallel.
- For every entry in a feed:
    - It generates a unique filename based on the date, feed name, and title.
    - It checks if the file already exists on disk (idempotency).
    - If new, it creates the `Tag/Subtag` folder hierarchy and saves the article.
- Once complete, it sends a notification and reloads the Sidebar to show new content.

### 3. Adding Feeds
- Clicking "Add Feed" (or pressing `a`) pushes a `ModalScreen`.
- Upon saving, the new feed is appended to `config.yml` and the internal config list.
- A fetch is automatically triggered for the newly added feed to populate the archive immediately.

## Data Format
Each article is saved as a Markdown file with the following structure:

```markdown
---
author: Author Name
date: '2026-05-21'
feed: Feed Name
title: Article Title
url: https://example.com/article
---

# Article Title
Converted markdown content here...
```
