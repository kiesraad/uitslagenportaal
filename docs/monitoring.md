# Monitoring

> [!NOTE]
> Status: **built, not yet installed**, 17 September 2026. The stack, the proxy, the Django
> instrumentation and the three exporters are in the repository and wait only for an administrator to
> run the commands in [deployments.md](deployments.md). Two things remain proposals and are marked as
> such below: **alerting has no receiver**, so alerts reach nobody, and **error tracking** is not
> built at all.

The portal has no metrics, no alerting and no log aggregation. This file proposes a Prometheus-based stack, installed as
cluster infrastructure rather than as part of the application chart, and names what has to be instrumented, in the order
worth doing it.

## What we can see today

Everything below is reachable only through `kubectl`, on a cluster nobody watches between deploys.

| Source   | State                                                                                                    |
|----------|----------------------------------------------------------------------------------------------------------|
| Traefik  | JSON access logs at INFO. Request-level detail exists, but nothing aggregates it.                        |
| Django   | Plain-text logs to stdout via the `simple` formatter, root logger at INFO.                               |
| Health   | Backend probes are `tcpSocket` only. Granian accepting connections says nothing about the database.      |
| Metrics  | No endpoint on any workload. Traefik and cert-manager can both export; neither is switched on.           |
| Celery   | Queue depth, task duration and failure counts are invisible. A stalled import looks like an idle worker. |
| Alerting | None. A failed renewal or a crash-looping worker surfaces when somebody opens the site.                  |

There is no Sentry, no Prometheus client and no OpenTelemetry anywhere in the repository.

## The stack

Installed into a `monitoring` namespace as a one-time infra release, alongside Traefik and cert-manager. One chart per
cluster. Pin the chart versions the way those two already are.

| Component             | Chart                                        | Role                                                                                                                                           |
|-----------------------|----------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| kube-prometheus-stack | `prometheus-community/kube-prometheus-stack` | Prometheus, Alertmanager, Grafana, node-exporter, kube-state-metrics, and the `ServiceMonitor`/`PrometheusRule` CRDs everything else hangs off |
| Loki                  | `grafana/loki`, SingleBinary mode            | Logs, backed by Scaleway object storage — reusing the bucket and credential convention the application already follows                         |
| Grafana Alloy         | `grafana/alloy`                              | Scrapes pod logs into Loki; the promtail successor, and the route to OpenTelemetry if traces ever earn their place                             |

Single-binary Loki is deliberate: a microservice deployment is not worth running for four workloads.

## Why not Scaleway Cockpit

Cockpit is managed Grafana, Mimir and Loki with nothing to operate, and it already carries metrics for the managed
Postgres, Redis and object storage that sit outside the cluster. For a team this size that is genuinely attractive.

It loses on portability. The chart has consistently picked provider-independent building blocks — the Gateway API is
installed for provider-independent routing, and certificates come from cert-manager rather than from Scaleway.
Monitoring is the layer you would most want intact during a migration, so tying it to one hosting provider cuts against
the grain of everything around it.

Reach for Cockpit as a `remote_write` destination once retention becomes a question: long-term storage becomes somebody
else's problem while the alerting rules stay on the cluster.

## Where it lives

Values files in `k8s-config/infra/`, installed by an administrator, documented as further steps under "One-time infra
setup" in [deployments.md](deployments.md).

It has to sit outside the application chart for the same reason `service-accounts` does: it needs ClusterRoles and CRDs,
and the deploy token deliberately cannot touch RBAC.

The application chart does ship its own `ServiceMonitor`s and `PrometheusRule`, which had one consequence for CD and,
contrary to an earlier reading of this file, none for CI:

- **The deploy Role was widened.** `deploy-service-account.yaml` now carries `monitoring.coreos.com`
  in its `apiGroups`, so CD can write the scrape configuration and alert rules that ship with the release they describe.
  The Role is still namespace-scoped and still excludes RBAC, so the token cannot widen its own grant. Because it lives
  in the `service-accounts` chart, it has to be applied with `helm upgrade` per environment; an application deploy does
  not pick it up.
- **`helm-ci` needed no change.** The workflow already passes `kubeconform` a generic
  `-schema-location` pointing at the datree CRDs-catalog, which carries the prometheus-operator schemas, and
  `helm template` there runs with `values.yaml` defaults — where `monitoring.enabled` is true. The new manifests are
  therefore rendered and validated on every pull request already. The one thing to watch is that the catalogue can lag
  the CRDs actually installed, and `-strict` would then reject a field it does not recognise.

The exporters need no new rights at all: a `Deployment` and a `Service` each, both already covered.

## Instrumentation, in priority order

Each step is useful on its own. The order is deliberate: the first two cover the whole site without touching application
code.

1. **Traefik metrics.** Enable `metrics.prometheus.serviceMonitor` in `infra/traefik-values.yaml`. Request rate, error
   rate and latency per HTTPRoute, covering frontend and backend at once. The most value for the least work.
2. **cert-manager metrics.** A silently failed ACME renewal takes the whole portal down on a Saturday.
   `certmanager_certificate_expiration_timestamp_seconds` turns that into a one-line alert with weeks of warning.
3. **A real health endpoint on Django.** `/healthz/` checks the database and backs both probes, so readiness now means
   the pod can serve rather than that granian accepted a connection.
   `django-prometheus` serves `/metrics` on the **same** port: the Gateway routes only `/api` to the backend and
   everything else to the frontend, so neither path is reachable from the internet, and in-cluster scrapes address the
   pod directly. A separate port would buy nothing.
4. **Celery task metrics.** `celery-exporter` reads task events off the Redis broker, which is why
   `CELERY_WORKER_SEND_TASK_EVENTS` and `CELERY_TASK_SEND_SENT_EVENT` are set in `settings.py`:
   without both, the exporter runs and reports nothing. Queue depth is the number that matters most — a backlog of EML
   imports is the failure that surfaces as stale results on a live site.
5. **Managed Postgres and Redis.** Both live outside the cluster. `postgres_exporter` and
   `redis_exporter` run in the **application** namespace rather than the monitoring one: that is where the credentials
   already are and they differ per environment, so keeping them here avoids maintaining a second copy of each secret.
   They reuse the CA mounts the application pods already use.
6. **JSON logging for Django.** The `simple` formatter is fine for `kubectl logs` and close to useless in Loki. A JSON
   formatter behind the existing `LOG_LEVEL` convention is a small change with a large payoff once logs are searchable.

## Alerts worth having

| Area         | Condition                                            | Signal             | Response |
|--------------|------------------------------------------------------|--------------------|----------|
| Gateway      | 5xx above 1% of requests for 5 minutes               | Traefik            | Page     |
| Gateway      | p95 route latency above 2s for 10 minutes            | Traefik            | Warn     |
| Gateway      | An HTTPRoute has no ready backends                   | kube-state-metrics | Page     |
| Certificates | Certificate expires within 14 days                   | cert-manager       | Page     |
| Certificates | ACME order failing for over an hour                  | cert-manager       | Warn     |
| Imports      | Queue depth rising 15 minutes with no completions    | celery-exporter    | Page     |
| Imports      | Task failure rate above 5% over 10 minutes           | celery-exporter    | Warn     |
| Imports      | Beat has not enqueued for two schedule intervals     | celery-exporter    | Page     |
| Imports      | Worker OOMKilled against its 2Gi limit               | kube-state-metrics | Page     |
| Backend      | Pod restart loop, or OOMKill against the 512Mi limit | kube-state-metrics | Page     |
| Backend      | Postgres connections above 80% of the instance cap   | postgres_exporter  | Warn     |
| Backend      | Health endpoint failing for 2 minutes                | Blackbox           | Page     |
| Platform     | Node memory pressure, or disk above 85%              | node-exporter      | Warn     |
| Platform     | Migration job failed during a deploy                 | kube-state-metrics | Page     |

The two columns are not prose. `Response` becomes a `severity` label on each `PrometheusRule` —
`Page` is `critical`, `Warn` is `warning` — and `Area` becomes an `area` label. The routing below reads directly off
those two, so the table and the rules can be checked against one another. The rules kube-prometheus-stack ships carry
`severity` but no `area`; grouping tolerates the missing label rather than forking the built-ins to add it.

Three of these are specific to how the application is configured rather than generic Kubernetes hygiene:

- **The celery memory ceiling.** Imports are sized by hand against peak memory, so an OOM against the 2Gi limit is a
  realistic failure rather than a theoretical one.
- **The database connection arithmetic.** `DB_CONN_MAX_AGE=60` with `blockingThreads: 16` across two replicas means
  every serving thread holds a persistent connection. That sum is currently maintained by hand in the ConfigMap
  comments; an alert says when it stops holding.
- **The single beat replica.** One replica under a `Recreate` strategy — if it dies quietly, periodic imports simply
  stop and nothing else notices.

## Alerting

Prometheus evaluates the rules and hands firing alerts to Alertmanager, which groups, deduplicates, applies silences and
delivers to a receiver. Delivery is outbound only, so the port-forward decision governs who can inspect and silence
alerts, not whether they are sent.

Installed as it comes, kube-prometheus-stack routes `Watchdog` to a null receiver and everything else to a receiver that
does nothing. Every alert in the table above fires into a void until the configuration below exists.

### Where alerts go

Email to a role mailbox, `uitslagenportaal-alerts@kiesraad.nl`, with the urgency in the subject line rather than in the
channel.

It is the only channel certain to exist. There is no chat webhook anywhere in this repository, no SMTP settings in
Django, and the two addresses that do exist are single-purpose: the ACME contact in
`values.yaml` and the disclosure inbox in `SECURITY.md`. Neither is an alerting mailbox.

> [!NOTE]
> This rests on an assumption: that the mailbox can be created and an SMTP submission endpoint on
> port 587 is reachable from the cluster. If it is wrong, only the `receivers:` block and the key
> names in one secret change. The label contract, route tree, grouping, timings, inhibitions and
> every `PrometheusRule` stay as they are.

| If the channel turns out to be       | Receiver                           | Secret key              |
|--------------------------------------|------------------------------------|-------------------------|
| Microsoft 365 or Teams               | `msteamsv2_configs`                | `msteams-webhook-url`   |
| Slack or Mattermost                  | `slack_configs`                    | `slack-webhook-url`     |
| A paging product, once a rota exists | `pagerduty_configs` on `page` only | `pagerduty-routing-key` |

A GitHub-issue receiver would reuse the pattern `deploy-token-check.yml` established, but Alertmanager has no native
one, so it means writing and running a bridge. It stays the escape hatch for the case where both mail and chat are
refused.

### Routing

The whole configuration lives in `k8s-config/infra/kube-prometheus-stack-values.yaml`. No credential is in it —
Alertmanager performs no environment-variable substitution, and secrets enter only through fields with a `_file`
variant — so the routing policy stays reviewable in git.

| Route     | Matches                            | `group_wait` | `repeat_interval` |
|-----------|------------------------------------|--------------|-------------------|
| heartbeat | `alertname="Watchdog"`             | 0s           | 5m                |
| blackhole | `severity="info"`, `InfoInhibitor` | —            | —                 |
| dev       | `namespace="uitslagenportaal-dev"` | 5m           | 24h               |
| page      | `severity="critical"`              | 30s          | 4h                |
| warn      | `severity="warning"`               | 5m           | 24h               |

Order matters: Alertmanager takes the first matching child, so the heartbeat and the blackholes come first, and `dev`
before the severity routes so dev never pages whatever its severity.

One policy, all the time. There are no time-based routes: the same alert reaches the same receiver at 03:00 on a Sunday
as at 11:00 on a Tuesday. `time_intervals` are the mechanism if that is ever worth varying, and a rota is the thing that
would make it worth varying.

Group by `namespace` and `area`. With fourteen rules across two namespaces that is deliberately aggressive: a node
failure then produces two or three messages that each list everything firing, rather than a dozen separate ones. The
cost is that an alert joining an existing group waits up to
`group_interval`, which is why the page route's is shorter than the warn route's.

Point `alertmanagerSpec.externalUrl` at `http://localhost:9090/alertmanager` to match the proxy path under Access, and
set `routePrefix` to `/alertmanager` to go with it. Prometheus takes the same pair. The Source and Silence links inside
every notification would otherwise reference an in-cluster service name that resolves nowhere for the person reading it;
aimed at the proxy they work as soon as the reader starts the single port-forward.

Give Alertmanager a volume. Silences and the notification log live on disk, so without one a restart re-notifies
everything and forgets every silence — including one placed deliberately mid-incident.

### What stays quiet

Alert fatigue is the failure mode that arrives first. Two things prevent it, and the second matters more than any
routing rule.

Inhibitions, on top of the chart's defaults: a route with no ready backends suppresses the error-rate and latency alerts
for the same namespace; an absent Celery worker suppresses the queue, task-failure and beat alerts; a failing ACME order
suppresses the expiry warning for the same certificate.

> [!NOTE]
> In Alertmanager a label absent from both the source and the target counts as equal. An `equal` list
> naming a label that neither alert carries silences everything the target matcher covers. Only use
> labels confirmed on both sides — `namespace` always exists, `node` usually does not.

Then disable the built-in rules that can never be true here. A managed control plane exposes no scheduler,
controller-manager, etcd or kube-proxy, so those targets are permanently down and their alerts fire forever, teaching
everyone to ignore the mailbox before a real alert ever arrives.

```yaml
kubeControllerManager: { enabled: false }
kubeScheduler: { enabled: false }
kubeEtcd: { enabled: false }
kubeProxy: { enabled: false }
```

### The dead man's switch

If Prometheus stops evaluating, Alertmanager crashes, or egress breaks, alerts simply stop — and silence is
indistinguishable from everything being well. It is the one failure that disables every other alert in this document at
once.

kube-prometheus-stack ships `Watchdog`, an alert that fires permanently for exactly this purpose. The
`heartbeat` receiver posts it to an external service every five minutes, and that service raises the alarm when the
pings stop. It has to be external: a dead man's switch inside the thing it watches is not one. Set the external check
period to 17 minutes, which tolerates a missed beat and a rolling restart while still catching a dead stack inside
twenty.

> [!NOTE]
> The residency argument that keeps error tracking self-hosted does not extend to this. The heartbeat
> payload is an alert name and a timestamp; it never carries portal data. Prefer an EU-hosted
> service regardless, to keep the conversation short.

Until such a service is procured, a scheduled GitHub Actions workflow modelled on
`deploy-token-check.yml` can poll Alertmanager through the API server's service proxy and open a labelled issue when
`Watchdog` is absent. It needs a service account of its own with `get` on
`services/proxy` in the monitoring namespace — not the deploy token, which has no rights there and must not gain any.
Two limits are worth knowing: GitHub disables scheduled workflows after sixty days without repository activity, which
any quiet stretch will reach, and scheduled runs drift under load. A stopgap, not a control to depend on.

### The notification secret

Created by hand by an administrator, following the convention every other secret here uses, and referenced by name only.

```bash
kubectl -n monitoring create secret generic alertmanager-notify \
  --from-literal=smtp-password='<relay-password>' \
  --from-literal=heartbeat-url='https://<heartbeat-service>/<token>'
```

`alertmanagerSpec.secrets: ['alertmanager-notify']` mounts it at
`/etc/alertmanager/secrets/alertmanager-notify/<key>`, so renaming the secret means editing those paths too.

> [!NOTE]
> Use `--from-literal`, never `--from-file`. A file written by an editor carries a trailing newline,
> and a heartbeat URL with a newline in it requests a URL that does not exist — a dead man's switch
> that was dead all along.

Once this is installed the command moves to the Secrets section of [deployments.md](deployments.md)
with the others.

### Proving it works

Test the egress assumption before building anything else; it is the one most likely to be wrong. Scaleway restricts
outbound SMTP on its compute products, and port 25 is not an option.

```bash
kubectl -n monitoring run smtp-probe --rm -it --restart=Never --image=busybox:1.36 \
  -- nc -zv smtp.kiesraad.nl 587
```

Then, in order: `amtool check-config` for a parse; `amtool config routes test` to assert that a critical alert in dev
reaches the dev receiver rather than `page`; and a synthetic alert posted straight to `/api/v2/alerts` with a two-minute
`endsAt` to prove delivery end to end. The synthetic alert changes no rule and no manifest and expires by itself.
Confirm the resolved mail as well as the firing one — `send_resolved` is the difference between knowing an incident
ended and assuming it.

## Error tracking

Prometheus reports the error rate and Loki holds the error text. Neither groups exceptions, deduplicates them, or says
that one is new since the last release. That is a separate capability, and nothing above covers it.

**Bugsink**, self-hosted in the `monitoring` namespace. It speaks the Sentry protocol, so the official SDKs are the
clients — `sentry-sdk` for Django and Celery, `@sentry/react` for the frontend — and the footprint is one container plus
a database rather than the Kafka and ClickHouse that Sentry's own distribution pulls in.

Keeping the official SDKs is the point: the DSN is the only thing tying the application to Bugsink, so the server can be
swapped without touching application code. The same portability argument that favours Prometheus over Cockpit. GlitchTip
covers the same ground and is ruled out on prior operational experience with it.

Self-hosting also settles data residency before it is asked. Exception payloads from an electoral body leaving for a
service outside the EU is a procurement and AVG question, not a configuration flag.

### Before it is switched on

- **Scrub the payloads.** Sentry-protocol clients attach request bodies, query parameters and local variables by
  default. An exception in the EML importer or a `VoteCount` serializer would put pre-publication vote counts into the
  error store, which is precisely the material that must not leak. `send_default_pii=False` and a `before_send` scrubber
  are a precondition, not hardening to add later.
- **Initialise per worker process.** The importer fans out over `ProcessPoolExecutor`, and
  `CELERY_WORKER_MAX_TASKS_PER_CHILD=5` recycles worker processes constantly, so the SDK has to be set up on process
  start rather than at import time in the parent.
- **The frontend boundary is not a global handler.** `ErrorBoundaryPage` catches render and loader errors inside the
  router; there is no `window.onerror` or `unhandledrejection` handler, so a failure in an async callback outside the
  React tree currently vanishes. `@sentry/react` installs those.

This replaces nothing above. Error tracking answers what broke and whether it is new; Prometheus answers whether the
service is healthy.

## Access

Port-forwarding only. Nothing in the `monitoring` namespace gets a hostname, a certificate or a route through the
Gateway.

One port-forward, to a small reverse proxy that serves an index of everything behind it.

```bash
kubectl -n monitoring port-forward svc/monitoring-proxy 9090:80
```

<http://localhost:9090> then lists the services and links to each. One port and one URL to remember, and the list stays
correct as services come and go. 9090 rather than 8080 because `docker compose`
publishes the whole application stack on 8080, and reaching for monitoring while the stack is up is exactly when the
collision would bite.

| Path            | Service                                   |
|-----------------|-------------------------------------------|
| `/`             | the index itself                          |
| `/grafana`      | `kube-prometheus-stack-grafana`           |
| `/prometheus`   | `kube-prometheus-stack-prometheus:9090`   |
| `/alertmanager` | `kube-prometheus-stack-alertmanager:9093` |

Bugsink would take a `/bugsink` entry alongside these if it is ever adopted; it is not built.

### The proxy

An nginx `Deployment`, `Service` and `ConfigMap` in `k8s-config/infra/monitoring-proxy.yaml`, applied with
`kubectl apply -f` alongside the chart installs. Deliberately not a chart: it holds one config file and one page of
HTML, and a chart would be more machinery than content.

The ConfigMap carries both the nginx configuration and the index page, so **adding a service is one edit in one file** —
a `location` block and a line in the index:

```nginx
location /prometheus/ {
  proxy_pass http://kube-prometheus-stack-prometheus:9090/prometheus/;
  proxy_set_header Host $host;
}
```

Nothing else moves: no new port-forward, no new bookmark, and nothing for anyone else on the team to learn when the
stack grows a component.

> [!NOTE]
> Each backend has to be told the path it is served under, or it issues root-relative asset URLs and
> redirects that escape the prefix. Prometheus and Alertmanager take `routePrefix` alongside
> `externalUrl`; Grafana needs `GF_SERVER_SERVE_FROM_SUB_PATH=true` with a matching
> `GF_SERVER_ROOT_URL`. Anything that cannot be told its prefix does not belong behind the proxy —
> give it its own port-forward instead.

Service names follow the release names; `kubectl -n monitoring get svc` lists what is actually there. Reaching any of
this still requires cluster credentials, the bar `kubectl logs` sets today — the proxy changes how many commands are
involved, not who may run them.

Alertmanager still needs outbound access to deliver notifications, which is unrelated to whether anything is reachable
inbound: 587 to the mail relay and 443 to the heartbeat service. No
`NetworkPolicy` exists in this project today, so pod egress is open — but if policies are ever introduced, the
monitoring namespace needs an explicit allowance, and that allowance is the thing that silently breaks alerting.
Scaleway also restricts outbound SMTP on its compute products, which is why the probe under Alerting comes before the
rest of the design.

Two reasons this stays the default rather than becoming a hostname behind basic auth:

- **Prometheus and Alertmanager have no authentication of their own.** Their query endpoints and the silence controls
  are open to whoever reaches them. Only Grafana and Bugsink have accounts.
- **The application Gateway cannot carry these routes anyway.** `01-gateway.yaml` sets
  `allowedRoutes.namespaces.from: Same` and pins both listeners to the application hostname, so a route from another
  namespace has nothing to attach to. Widening it would also tie the ability to see what is wrong to the release that
  may be what is wrong.

If on-call ever needs a browser instead of a terminal, the shape that fits the existing patterns is a second Gateway in
the monitoring namespace with its own hostname, its own `Certificate` and
`Issuer` (both namespaced, so they are duplicated rather than shared), a Traefik `IPAllowList`
middleware through `ExtensionRef`, and Grafana's own login rather than the basic-auth middleware. Exposing Prometheus or
Alertmanager is not part of that shape.

### Bugsink and browser events

Backend and Celery errors reach Bugsink over cluster DNS, so port-forwarding covers the whole backend case. Frontend
errors do not: `@sentry/react` posts from the visitor's browser, so the ingest endpoint has to be reachable from the
internet even when the UI is not.

Frontend error tracking is therefore out of reach until that is settled. Splitting ingest onto its own public route
while the UI stays internal is the likely answer, with the DSN as its only credential.

## Retention

Thirty days for both metrics and logs: long enough to compare this week against last month, short enough that the volume
stays predictable.

### Metrics

Prometheus evicts whole blocks, never individual samples. It writes two-hour blocks and compacts them into larger ones,
up to a tenth of the retention period, and a block is dropped only once its entire time range has aged out. Thirty days
therefore holds up to about thirty-three. Retention is a floor, not a ceiling.

```yaml
prometheus:
  prometheusSpec:
    retention: 30d
    retentionSize: 40GB
    storageSpec:
      volumeClaimTemplate:
        spec:
          accessModes: [ "ReadWriteOnce" ]
          resources:
            requests:
              storage: 50Gi
```

Both limits are set and whichever trips first wins. Time alone is the trap: Prometheus does not stop writing when the
disk fills, it crashes — precisely when something interesting is happening.
`retentionSize` sits at roughly 80% of the volume because the WAL, head chunks and compaction working space all need
room the retention figure does not account for.

Two things follow from `storageSpec`:

- **It is not optional.** Without it the pod falls back to `emptyDir` and loses every metric on restart, including the
  restart being investigated.
- **Size it generously now.** A StatefulSet's `volumeClaimTemplates` are immutable, so growing the volume later needs an
  expansion-capable storage class and a recreation of the StatefulSet with an orphan cascade. Storage is cheaper than
  that procedure.

At roughly 100k active series on a 30s scrape, expect about half a gigabyte a day, so thirty days lands near 17GB and a
50Gi volume keeps real headroom.

### Keeping anything longer

Prometheus retention is global. There is no per-series retention, so keeping one period for years is not a setting — it
is all metrics or none.

Snapshot instead. With the admin API enabled, `POST /api/v1/admin/tsdb/snapshot` writes a hardlink snapshot of the TSDB,
which is copied to object storage using the same bucket and credential convention the application already follows. That
leaves an immutable, dated archive a throwaway Prometheus can mount and query years later, while routine retention stays
at thirty days. It belongs in a runbook rather than in a values file.

> [!NOTE]
> Enabling the admin API also enables `delete_series`. On a component with no authentication of its
> own that is defensible behind port-forward-only access, but it is a deliberate choice rather than a
> default.

Continuous long-term querying is the other answer, and it is where `remote_write` to Cockpit earns its place.
Downsampled recording rules into a second, long-retention Prometheus are a third option, worth the moving parts only if
multi-year trends are genuinely wanted.

### Logs

Loki works differently, and its compactor has to be switched on explicitly.

```yaml
limits_config:
  retention_period: 720h
compactor:
  retention_enabled: true
  delete_request_store: s3
```

With `retention_enabled` left at its default of false, chunks stay on object storage forever no matter what
`retention_period` says. That is the usual way a Loki bill grows quietly.

Unlike Prometheus, Loki does support per-stream retention, so a `retention_stream` override can hold Traefik access logs
longer than Celery debug output if that ever becomes worth the configuration.

> [!NOTE]
> Do not reach for an object-storage lifecycle rule instead. It deletes chunks the index still
> references, which surfaces as query errors rather than as clean expiry.

Bugsink prunes its own events on its own schedule; nothing above covers it.

## Deliberately not included

- **Distributed tracing.** For four deployments and one queue, OpenTelemetry is cost without payoff. Alloy leaves the
  door open if the import pipeline ever grows enough hops to need it.
- **An APM product.** Request timing from Traefik plus ORM metrics from `django-prometheus` covers the questions that
  actually get asked.
- **A paging product.** PagerDuty and Opsgenie are priced for a rotation, and there is no rotation to page. The route
  tree already separates `page` from `warn`, so adopting one later is a receiver swap.

## Open questions

- Who is on the rota, and what is promised out of hours? The routing distinguishes Page from Warn, but nothing in the
  cluster can make a phone ring in a room with nobody in it.
- Does an alerting mailbox and an SMTP relay credential actually exist? Both are requests to other teams, and they have
  the longest lead time of anything here.
