from kubernetes import client, config

config.load_kube_config()

v1 = client.CoreV1Api()
#print("Listing pods with their IPs:")
ret = v1.list_pod_for_all_namespaces(watch=False)   # class V1PodList
for pod in ret.items:
    if pod.metadata.namespace == "spinnaker":
        print("%s\t%s\t%s" % (pod.status.pod_ip, pod.metadata.namespace, pod.metadata.name))
