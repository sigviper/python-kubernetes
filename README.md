# python-kubernetes

## fix hanging certificate requests
Sometimes k8s [cert-manager](https://cert-manager.io/docs/) requests/orders are hanging or failing. If you need to automate deletion of such stale resources, here is the script: `fix_ssl_certs_status.py`

### Installation
```
virtualenv pvenv
source pvenv/bin/activate
pip install -r requirements.txt
```

### Running
The fix_ssl_certs_status.py script is interactive, it will only delete resources when accepted by user input. The script assumes user has defined context in ~/.kube/config and will attempt the authentication defined there.
```
source pvenv/bin/activate
python fix_ssl_certs_status.py kubernetes_context_name [-n namespace]
```
