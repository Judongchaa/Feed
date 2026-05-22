# Idea: YouTube Suggestions Addon

This document explores a conceptual addon for the Feed application that retrieves personalized YouTube suggestions and displays them in a dedicated article list.

## 1. The Challenge: Getting Personal Suggestions
The biggest hurdle is that YouTube does not provide a simple RSS feed for your *personal homepage recommendations*. 

To solve this, the addon could use one of the following approaches:
- **Cookie Export & yt-dlp**: You export your YouTube cookies from your browser to a `cookies.txt` file. The addon uses the `yt-dlp` Python library to fetch your homepage feed using those cookies.
- **YouTube Data API v3**: Requires setting up an OAuth 2.0 flow, which is heavy for a simple TUI application, and still may not perfectly replicate the home page algorithm.
- **Browser Automation**: Use Playwright/Selenium in the background to scrape the homepage, though this is resource-intensive.

*Recommendation*: The **yt-dlp + cookies.txt** approach is the most reliable and lightweight for terminal applications.

## 2. Addon Architecture (`addons/yt_suggest.py`)

The addon will plug into the existing architecture using the `addon_manager`.

### Configuration (`addon_config.yml`)
You would map the addon to a specific tag, for example, `Youtube/Suggestions`:
```yaml
addons:
  yt_suggest:
    enabled: true
    tags:
      - "Youtube/Suggestions"
```

### Fetching & Updating
Because recommendations aren't an RSS feed, we would need to slightly adjust `core/logic.py` to allow addons to run custom update routines.
- When "Update Feeds" is pressed, the `yt_suggest` addon reads `cookies.txt` and queries `yt-dlp` for the homepage videos.
- It saves these videos into a local SQLite database (e.g., `yt_suggestions.db`) to keep track of read/unread states and avoid re-populating the same suggestions constantly.

### UI & Display
The addon will implement the `load_articles(current_dir, tag, subtag, limit)` method.
- It will query `yt_suggestions.db` for the latest videos.
- It will return a list of `SuggestionItem` widgets (a subclass of `ListItem`).
- The `SuggestionItem` will display the channel name, video title, and duration/date.
- When you press `Enter` on an item, it marks it as read in the database and uses Python's `webbrowser` module to launch the video in your default browser.

## 3. Step-by-Step Execution Flow
1. **Trigger**: You press `u` to update feeds.
2. **Fetch**: `yt_suggest.py` silently runs a background scrape using `yt-dlp` to grab your top 20 recommended videos.
3. **Database**: It inserts any new videos into `yt_suggestions.db`.
4. **Render**: You navigate to the `Youtube -> Suggestions` folder in the sidebar.
5. **Load**: The app calls `yt_suggest.load_articles()`. The addon fetches the recommendations from the database and yields them to the `ListView`.
6. **Action**: You select an interesting video, it opens in your browser, and the indicator dot turns from Unread to Read.
