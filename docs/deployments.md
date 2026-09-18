## Deploy configuration

This file gives an overview on how to deploy the application to a Kubernetes (k8s) cluster, either locally or a managed one.

The directory ./k8s-config/ contains all the configuration necessary: the application Helm chart, the
`service-accounts` chart, the `monitoring` chart, and values files for the one-time infra setup.

Commands in this file have to be run from ./k8s-config/.

### Helm chart

The Helm chart is divided into several yaml files, see ./k8s-config/templates.

- `00-config.yaml`: The `ConfigMap` with generic configuration values.
- `01-gateway.yaml`: The Gateway config incl. which ports to use and the cert-manager `Issuer` configuration.
- `02-httproute.yaml`: The route definition for `/api` and `/`, including a redirect from http -> https and the traefik middleware config.
- `03-frontend.yaml`: Frontend deployment and service.
- `04-backend.yaml`: Backend deployment and service, incl. an init job which runs the migrations.
- `05-celery.yaml`: Celery and Celery beat deployments.
- `06-services.yaml`: Several `StatefulSet`s for PostgreSQL/Redis/Object storage services (local deployments only).

There is one main `values.yaml` file, and a file per environment. Each environment file overrides certain values for the
environment's deployments. Helm reads `values.yaml` itself as the chart's defaults, so only the environment file is
passed on the command line.

Every command below writes the namespace as `uitslagenportaal-[env]`; substitute the environment you are deploying to,
`uitslagenportaal-dev` for the one CD deploys. The manifests take their namespace from the release, so the `-n` flag is
the only thing that decides where they land.

### One-time infra setup

To set up the infrastructure for the cluster, it needs to be done only once.
That's why the values-files are not part of the chart.

1. Install the Gateway API (for provider-independent routing):
   ```bash
   kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.1/standard-install.yaml
   ```

2. Add the chart repos:
   ```bash
   helm repo add traefik  https://traefik.github.io/charts
   helm repo add jetstack https://charts.jetstack.io
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm repo add grafana https://grafana.github.io/helm-charts
   helm repo update
   ```

3. Install the monitoring stack. Traefik and cert-manager depend on the `monitoring.coreos.com` CRDs.
   Create the namespace and the Loki secret first (see the Secrets section below), then:
   ```bash
   helm dependency build monitoring
   helm upgrade --install monitoring monitoring -n monitoring --wait --timeout 15m
   ```
   For local deploys, skip the Loki secret and add `-f monitoring/values-local.yaml`.

4. Install Traefik as an ingress controller and Gateway API implementation:
   ```bash
   helm upgrade --install traefik traefik/traefik --version 41.4.0 -n traefik --create-namespace -f infra/traefik-values.yaml --wait --timeout 10m
   ```

5. Install cert-manager to issue the TLS certificates:
   ```bash
   helm upgrade --install cert-manager jetstack/cert-manager --version v1.21.1 -n cert-manager --create-namespace -f infra/cert-manager-values.yaml --wait --timeout 10m
   ```

### Monitoring

Installed in step 3 above: metrics, logs and alert rules for the whole cluster.

> [!NOTE]
> Alertmanager is installed with no receiver configured, so alerts are grouped and visible in its UI
> and **sent to nobody**. Deciding the channel and configuring it is separate work; until then this
> stack tells you what is wrong only once you go and look.

#### Reaching the monitoring UIs

Port-forwarding only: nothing in the `monitoring` namespace has a hostname, a certificate or a route through the
Gateway. One forward covers all of it.

```bash
kubectl -n monitoring port-forward svc/monitoring-proxy 9090:80
```

<http://localhost:9090> lists the services and links to each: `/grafana`, `/prometheus` and
`/alertmanager`. Port 9090 rather than 8080 because `docker compose` publishes the application stack on 8080, and
wanting monitoring while that is running is exactly when the two would collide.

Grafana's login is `admin`, with a password the chart generates on first install:

```bash
kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d
```

### Secrets

Several secrets are needed to configure the services in the Chart.
Some secrets are automatically configured when deploying locally because they are based on the locally deployed services.
In production, however, it's required to set these to the values to the managed services credentials.

If the namespace does not exist yet, create it: `kubectl create namespace uitslagenportaal-[env]`.

> [!NOTE]
> Replace `\` with `` ` `` when running commands in Powershell

**DB**

```bash
kubectl -n uitslagenportaal-[env] create secret generic db-creds \
  --from-literal=DB_HOST=0.0.0.0 \
  --from-literal=DB_PORT=5432 \
  --from-literal=DB_USER=uitslagenportaal \
  --from-literal=DB_NAME='rdb' \
  --from-literal=DB_PASSWORD='<db-password>' \
  --from-file=DB_CA_CERT=rdb-rdb-uitslagenportaal.pem
```

**Redis**

```bash
kubectl -n uitslagenportaal-[env] create secret generic redis-creds \
  --from-literal=REDIS_HOST=''  \
  --from-literal=REDIS_PORT=6379  \
  --from-literal=REDIS_USER=''  \
  --from-literal=REDIS_PASSWORD='' \
  --from-file=REDIS_CA_CERT=redis-redis-uitslagenportaal.pem
```


**Object storage**

```bash
kubectl -n uitslagenportaal-[env] create secret generic s3-creds \
  --from-literal=S3_BUCKET_NAME='uitslagenportaal'  \
  --from-literal=S3_ACCESS_KEY=''  \
  --from-literal=S3_SECRET_KEY=''  \
  --from-literal=S3_ADDRESSING_STYLE='virtual'  \
  --from-literal=S3_ENDPOINT_URL='https://s3.nl-ams.scw.cloud'  \
  --from-literal=S3_PUBLIC_DOMAIN='uitslagenportaal.s3.nl-ams.scw.cloud'  \
  --from-literal=S3_URL_PROTOCOL='https:'
```

**Application secrets**

> [!NOTE]
> Note: Changing the SECRET_KEY will invalidate all hashed data! Don't recreate it in production.

```bash
kubectl -n uitslagenportaal-[env] create secret generic uitslagenportaal-secrets \
  --from-literal=SECRET_KEY="$(openssl rand -base64 48)"
```

**Importer secrets**

```bash
kubectl -n uitslagenportaal-[env] create secret generic importer-creds \
  --from-literal=GITHUB_TOKEN="" \
  --from-literal=GITHUB_INGRESS_REPO=""
```

**Monitoring**

In the `monitoring` namespace rather than an environment's, because the stack is installed once for the cluster. Create
the namespace first: `kubectl create namespace monitoring`. Grafana's admin secret is generated by the chart; only
Loki's object storage credentials are created by hand, and not at all for a local deploy.

```bash
kubectl -n monitoring create secret generic loki-s3-creds \
  --from-literal=AWS_ACCESS_KEY_ID='' \
  --from-literal=AWS_SECRET_ACCESS_KEY=''
```

Loki needs a bucket of its own, separate from the application's: its retention differs and log chunks should not share a
bucket with election documents.

> [!NOTE]
> Use `--from-literal` here, never `--from-file`. A file written by an editor carries a trailing
> newline, and a credential with a newline in it fails in ways that do not look like a credential
> problem.

**Basic authentication**

The whole site sits behind HTTP basic auth, with the credentials in a secret holding
htpasswd lines. Create it before installing the chart: `basicAuth.enabled` is true by
default, and while the secret is missing Traefik fails the route with a 5xx instead of
asking for a password.

```bash
kubectl -n uitslagenportaal-[env] create secret generic basic-auth-creds \
  --from-literal=users="$(htpasswd -nbB <user> '<password>')"
```

> [!NOTE]
> Windows has no `htpasswd`; `docker run --rm httpd:2 htpasswd -nbB <user> '<password>'` prints the same line.

Certificate issuance is unaffected: cert-manager attaches its own HTTP-01 route to the
Gateway, and that route carries no auth filter.


### Automatic deploy

#### Service account

For the CD pipeline we need a service account and store a token for this account in a GitHub secret.

It is a chart of its own rather than part of the application chart, because CD authenticates as this account: managing
its own `Role` would mean granting itself RBAC rights, and with those it could widen its grant to anything in the
namespace. Install it as an administrator, once per environment.

1. Make sure the service account exists or is updated:
   ```bash
   helm upgrade --install uitslagenportaal-service-accounts ./service-accounts -n uitslagenportaal-[env]
   ```
2. Create a token and store it as the `K8S_DEPLOY_TOKEN` secret of the matching GitHub Environment, either by pasting
   the output into GitHub by hand:
   ```bash
   kubectl -n uitslagenportaal-[env] create token uitslagenportaal-deploy --duration=8760h
   ```
   or, with the `gh` CLI installed, by piping it straight in:
   ```bash
   kubectl -n uitslagenportaal-[env] create token uitslagenportaal-deploy --duration=8760h \
     | gh secret set K8S_DEPLOY_TOKEN --repo kiesraad/uitslagenportaal --env [deploy-env-name]
   ```

#### The deployment pipeline

A push to `dev` deploys itself. Once the backend, frontend, Playwright and Helm suites have
all passed and both images are published, the `deploy` job in `branch-ci-cd.yml` upgrades the
release.

The job pins the digests it just built rather than the `:dev` tag in `values-dev.yaml`, so a release records the image
sha it actually ran and `helm rollback` returns to that same image. It
runs with `--rollback-on-failure`, which rolls the manifests back if the rollout fails. Helm cannot undo migrations,
which is why migrations preferably stay backwards-compatible.

It authenticates as the `uitslagenportaal-deploy` service account above, reading these from
the `scaleway-dev` GitHub Environment:

| Kind     | Name                             | Value                                                    |
|----------|----------------------------------|----------------------------------------------------------|
| secret   | `K8S_DEPLOY_TOKEN`               | the service account token                                |
| variable | `K8S_API_SERVER`                 | `clusters[0].cluster.server` from your kubeconfig        |
| variable | `K8S_CA_DATA`                    | `clusters[0].cluster.certificate-authority-data` from it |

#### Watching the token expire

The token from `kubectl create token --duration=8760h` expires, so it needs replacing before it does.
`deploy-token-check.yml` runs on the first of each month and reads the expiry out of the token itself.

Every run writes the expiry date to its job summary. Under 90 days it opens an issue labelled
`renew-deploy-token` and `<environment>`. Adding an environment takes two things: a matrix entry in the workflow naming
it and its namespace, and a `K8S_DEPLOY_TOKEN` secret in the matching GitHub Environment.

### Deploy the Helm chart manually

The Helm chart contains the application-specific configuration.

#### Managed cluster deploy

On a managed Kubernetes cluster at a hosting provider.

1. Run the commands for the one-time infra setup, see above, if not done before.
2. Make sure the secrets are set, see the Secrets section above.
3. Install the helm chart:
   ```bash
   helm upgrade --install uitslagenportaal . -n uitslagenportaal-[env] -f values-[env].yaml
   ```

Note this reverts the cluster to whatever `:dev` points at, because it passes none of the
digest overrides CD uses. To keep the running images, read them off the cluster first and
pass them back in:

```bash
kubectl -n uitslagenportaal-[env] get deploy uitslagenportaal-backend \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
```

#### Local deploy

E.g. on a Kubernetes cluster from Docker Desktop or kind

1. Run the commands for the one-time infra setup, see above, if not done before. Install the monitoring chart with
   `-f monitoring/values-local.yaml`: it keeps Loki's logs on its own volume instead of in object storage, and turns
   off mount propagation for node-exporter, which Docker Desktop refuses.
2. Add a hosts value in `C:\Windows\System32\drivers\etc\hosts` or `/etc/hosts`:
   `127.0.0.1  uitslagenportaal.localdev`
3. Set the importer secrets (services secrets are created by `06-services.yaml`).
4. Install the helm chart:
   ```bash
   helm upgrade --install uitslagenportaal . -n uitslagenportaal-local --create-namespace -f values-local.yaml
   ```
