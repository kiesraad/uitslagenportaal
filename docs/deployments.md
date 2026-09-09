## Deploy configuration

This file gives an overview on how to deploy the application to a Kubernetes (k8s) cluster, either locally or a managed one.

The directory ./k8s-config/ contains all the configuration necessary, including a Helm chart and values files for the one-time infa setup.

Commands in this file have to be run from ./k8s-config/.

### Helm chart

The Helm chart is divided into several yaml files, see ./k8s-config/templates.

- `00-config.yaml`: The `ConfigMap` with generic configuration values.
- `01-gateway.yaml`: The Gateway config incl. which ports to use and de cert-manager `Issuer` configuration.
- `02-httproute.yaml`: The route definition for `/api` and `/`, including a redirect from http -> https and the traefik middleware config.
- `03-frontend.yaml`: Frontend deployment and service.
- `04-backend.yaml`: Backend deployment and service, incl. an init job which runs the migrations.
- `05-celery.yaml`: Celery and Celery beat deployments.
- `06-services.yaml`: Several `StatefulSet`s for PostgreSQL/Redis/Object storage services (local deployments only).

There are two values-files: `values.yaml` and `values-local.yaml`. 
The first defines all chart values for a general deployment, and `values-local.yaml` overrides certain values for local deploys. 

### One-time infra setup

To set up the infrastructure for the cluster, it needs to be done only once.
That's why the values-files are not part of the chart.

1. Install the Gateway API (for provider-independent routing):
   ```bash
   kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.1/standard-install.yaml
   ```

2. Add the traefik/cert-manager repos
   ```bash
    helm repo add traefik  https://traefik.github.io/charts
    helm repo add jetstack https://charts.jetstack.io
    helm repo update
    ```

3. Install Traefik as an ingress controller and Gateway API implementation:
   ```bash
   helm upgrade --install traefik traefik/traefik --version 41.4.0 -n traefik --create-namespace -f infra/traefik-values.yaml --wait --timeout 10m
   ```

4. Install cert-manager to issue the TLS certificates:
   ```bash
   helm upgrade --install cert-manager jetstack/cert-manager --version v1.21.1 -n cert-manager --create-namespace -f infra/cert-manager-values.yaml --wait --timeout 10m
   ```

### Secrets

Several secrets are needed to configure the services in the Chart.
Some secrets are automatically configured when deploying locally because they are based on the locally deployed services.
In production, however, it's required to set these to the values to the managed services credentials.

If no `uitlsagenportaal` namespace exists, create it: `kubectl create namespace uitslagenportaal`.

> [!NOTE]
> Replace `\` with `` ` `` when running commands in Powershell

**DB**

```bash
kubectl -n uitslagenportaal create secret generic db-creds \
  --from-literal=DB_HOST=172.16.0.7 \
  --from-literal=DB_PORT=5432 \
  --from-literal=DB_USER=uitslagenportaal \
  --from-literal=DB_NAME='rdb' \
  --from-literal=DB_PASSWORD='<db-password>' \
  --from-file=DB_CA_CERT=rdb-rdb-uitslagenportaal.pem
```

**Redis**

```bash
kubectl -n uitslagenportaal create secret generic redis-creds \
  --from-literal=REDIS_HOST=''  \
  --from-literal=REDIS_PORT=6379  \
  --from-literal=REDIS_USER=''  \
  --from-literal=REDIS_PASSWORD='' \
  --from-file=REDIS_CA_CERT=redis-redis-uitslagenportaal.pem
```


**Object storage**

```bash
kubectl -n uitslagenportaal create secret generic s3-creds \
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
kubectl -n uitslagenportaal create secret generic uitslagenportaal-secrets \
  --from-literal=SECRET_KEY="$(openssl rand -base64 48)"
```

**Importer secrets**

```bash
kubectl -n uitslagenportaal create secret generic importer-creds \
  --from-literal=GITHUB_TOKEN="" \
  --from-literal=GITHUB_INGRESS_REPO=""
```

**Basic authentication**

The whole site sits behind HTTP basic auth, with the credentials in a secret holding
htpasswd lines. Create it before installing the chart: `basicAuth.enabled` is true by
default, and while the secret is missing Traefik fails the route with a 5xx instead of
asking for a password.

```bash
kubectl -n uitslagenportaal create secret generic basic-auth-creds \
  --from-literal=users="$(htpasswd -nbB <user> '<password>')"
```

> [!NOTE]
> Windows has no `htpasswd`; `docker run --rm httpd:2 htpasswd -nbB <user> '<password>'` prints the same line.

Certificate issuance is unaffected: cert-manager attaches its own HTTP-01 route to the
Gateway, and that route carries no auth filter.

### Deploy the Helm chart

The Helm chart contains the application-specific configuration.

#### Managed cluster deploy

On a managed Kubernetes cluster at a hosting provider.

1. Run the commands for the one-time infa setup, see above, if not done before.
2. Make sure the secrets are set, see the Secrets section above.
3. Install the helm chart:
   ```bash
   helm upgrade --install uitslagenportaal . -n uitslagenportaal -f values.yaml
   ```
   

#### Local deploy

E.g. on a Kubernetes cluster from Docker Desktop or kind

1. Run the commands for the one-time infa setup, see above, if not done before.
2. Add a hosts value in `C:\Windows\System32\drivers\etc\hosts` or `/etc/hosts`:
   `127.0.0.1  uitslagenportaal.localdev`
3. Set the importer secrets (services secrets are created by `06-services.yaml`).
4. Install the helm chart:
   ```bash
   helm upgrade --install uitslagenportaal . -n uitslagenportaal --create-namespace -f values.yaml -f values-local.yaml
   ```
