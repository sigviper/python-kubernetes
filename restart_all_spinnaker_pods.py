from kubernetes import client, config
import json

config.load_kube_config(config_file='/etc/rancher/k3s/k3s.yaml', context='default', persist_config=True)

kubens = 'spinnaker'
pod_prefix = 'spin-'

v1 = client.CoreV1Api()
print("Deleting (recreating) pods")
pods_list = v1.list_pod_for_all_namespaces(watch=False)   # class V1PodList
delete_ret = []
for pod in pods_list.items:
    if pod.metadata.namespace == kubens and pod.metadata.name.find(pod_prefix) == 0:
        #print("%s\t%s\t%s" % (pod.status.pod_ip, pod.metadata.namespace, pod.metadata.name))
        api_response = v1.delete_namespaced_pod(pod.metadata.name, kubens)
        delete_ret.append(api_response)

print(delete_ret) # parse json


## Ideas to move forward:
# 1. create pods or deployments to be deleted before deleting
# 2. do something more usefull: list problems with certificaterequests (remember to document install instructions and make em easy)