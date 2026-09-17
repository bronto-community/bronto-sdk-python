# Examples

Runnable versions of the call sites in the [README](../README.md). Each script
is standalone and reads its credentials from the environment:

```bash
export BRONTO_API_KEY=...
export BRONTO_REGION=eu        # or BRONTO_BASE_URL for a custom deployment

uv run python examples/search_logs.py
```

| Script | Shows |
| --- | --- |
| [`search_logs.py`](search_logs.py) | A typed `POST /search`, a natural-language window, and **explicit escaping** of an untrusted value into the where clause |
| [`get_monitor.py`](get_monitor.py) | `GET /monitors/{id}`, and catching one status-specific error out of the hierarchy |
| [`async_search.py`](async_search.py) | `AsyncBrontoClient`, concurrent searches through one client, and the `max_concurrency` cap |
| [`mcp_endpoint.py`](mcp_endpoint.py) | The MCP registry: regional and staging endpoints, and the auth header |

Only `mcp_endpoint.py` runs without a live API key.
