# Feed Monitor MCP Agent

This MCP agent provides HTTP tools to monitor and manage RSS feeds, designed for integration in multi-agent systems and easy deployment on Railway or any cloud platform compatible with Python and FastAPI.

## What does it do?
- Validates RSS feeds.
- Adds feeds to users.
- Removes feeds from users.
- Gets user and global feeds.
- Marks episodes as processed.
- Returns new unprocessed episodes.

## Main Endpoints
The main endpoints are:

- `GET /list_tools`: Returns the list of available tools and their input schemas.
- `POST /call_tool`: Invokes an MCP tool. The body must include the tool name and its arguments.

Available tools via `/call_tool`:

1. **validateRssFeed**
   - Validates if a URL is a correct RSS feed.
   - Arguments: `{ "feed_url": "<url>" }`
2. **get_user_feeds**
   - Gets the feeds of a user.
   - Arguments: `{ "user_id": "<uid>" }`
3. **get_all_feeds**
   - Gets all global feeds.
   - Arguments: `{}`
4. **get_new_episodes**
   - Gets new unprocessed episodes from all feeds.
   - Arguments: `{}`
5. **add_feed_to_user**
   - Adds an RSS feed to a user's list.
   - Arguments: `{ "user_id": "<uid>", "email": "<email>", "feed_url": "<url>", "custom_name": "<name>", "active": true }`
6. **delete_feed_from_user**
   - Removes an RSS feed from a user's list.
   - Arguments: `{ "user_id": "<uid>", "feed_url": "<url>" }`
7. **mark_episode_processed**
   - Marks an episode as processed in the processed_episodes subcollection of a feed.
   - Arguments: `{ "feed_id": "<id>", "guid": "<guid>", "metadata": { ... } }`

## Example usage with curl

### Validate an RSS feed
```bash
curl -X POST https://<your-app>.up.railway.app/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name": "validateRssFeed", "arguments": {"feed_url": "https://feeds.megaphone.fm/sciencevs"}}'
```

### List available tools
```bash
curl https://<your-app>.up.railway.app/list_tools
```

### Get feeds of a user
```bash
curl -X POST https://<your-app>.up.railway.app/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name": "get_user_feeds", "arguments": {"user_id": "<uid>"}}'
```

### Get all global feeds
```bash
curl -X POST https://<your-app>.up.railway.app/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name": "get_all_feeds", "arguments": {}}'
```

### Get new unprocessed episodes
```bash
curl -X POST https://<your-app>.up.railway.app/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name": "get_new_episodes", "arguments": {}}'
```

### Add a feed to a user
```bash
curl -X POST https://<your-app>.up.railway.app/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name": "add_feed_to_user", "arguments": {"user_id": "<uid>", "email": "<email>", "feed_url": "<url>", "custom_name": "<name>", "active": true}}'
```

### Remove a feed from a user
```bash
curl -X POST https://<your-app>.up.railway.app/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name": "delete_feed_from_user", "arguments": {"user_id": "<uid>", "feed_url": "<url>"}}'
```

### Mark episode as processed
```bash
curl -X POST https://<your-app>.up.railway.app/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name": "mark_episode_processed", "arguments": {"feed_id": "<id>", "guid": "<guid>", "metadata": {}}}'
```

## Security notes
- Do not expose your Firebase private key in public repositories.
- Configure CORS in production to restrict allowed origins.

## Author
- Project: GlobalPodcaster
- MCP Agent: feed-monitor-agent
