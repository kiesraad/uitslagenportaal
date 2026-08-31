## Deploy configuration

Commands have to be run from ./k8s-config/.

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

### Deploy the Helm chart

The Helm chart contains the application-specific configuration.

#### Local deploy

E.g. on a Kubernetes cluster from Docker Desktop or kind

1. Run the commands for the one-time infa setup, see above, if not done before.
2. Add a hosts value in `C:\Windows\System32\drivers\etc\hosts` or `/etc/hosts`:
   `127.0.0.1  uitslagenportaal.localdev`
3. Install the helm chart:
   ```bash
   helm upgrade --install uitslagenportaal . -n uitslagenportaal --create-namespace -f values.yaml -f values-local.yaml
   ```
