# python-kubernetes

## Installation
```
virtualenv pvenv
source pvenv/bin/activate
pip install -r requirements.txt
```

## Running
The fix_ssl_certs_status.py script is interactive, it will only delete resources when accepted by user input
```
# login to kubernetes cluster
source pvenv/bin/activate
python fix_ssl_certs_status.py kubernetes_context_name [-n namespace]
```
