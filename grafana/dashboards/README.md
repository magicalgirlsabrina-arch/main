# Grafana Dashboards

Drop dashboard JSON files here and Grafana auto-imports them on startup.

## Recommended pre-built dashboards to import

After Grafana is running, go to **Dashboards → New → Import** and paste these IDs:

- **22650** — NVIDIA Jetson Orin Nano Super Monitoring (works with the
  jetson-stats exporter on each ClawBox)

You can also import them by downloading the JSON from grafana.com/dashboards
and saving it in this folder — they'll show up automatically.

## Custom OpenClaw dashboard

Build your own using these PromQL queries against the OpenClaw metrics:

- `rate(openclaw_gateway_requests_total[5m])` — requests per second
- `openclaw_gateway_active_sessions` — currently open chat sessions
- `rate(openclaw_tokens_generated_total[1m])` — token throughput
- `histogram_quantile(0.95, rate(openclaw_request_duration_seconds_bucket[5m]))`
  — p95 latency

(Exact metric names may vary — check `http://CLAWBOX:18789/api/diagnostics/prometheus`
to see what's actually exposed.)
