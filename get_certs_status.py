from kubernetes import client, config
import time
from kubernetes.client.rest import ApiException
from pprint import pprint
import json


def get_crds(api_instance):
    api_response = api_instance.list_custom_resource_definition() #label_selector='app=cert-manager'
    
    ret = []
    for crd in api_response.items:
        info = {}
        conf = crd.metadata.annotations['kubectl.kubernetes.io/last-applied-configuration']
        jres = json.loads(conf)
        info['name'] = jres['metadata']['name']
        labels = jres['metadata'].get('labels')
        if labels:
            info['app'] = labels.get('app')
        
        ret.append(info)
    
    return ret

if __name__ == '__main__':
    configuration = config.load_kube_config(context='blue.k8s.dev.connected-biking.cloud')

    with client.ApiClient(configuration) as api_client:
        api_instance = client.ApiextensionsV1Api(api_client)
        
        try:
            h_col1 = 'NAME'
            h_col2 = 'APP LABEL'
            print(f'{h_col1:<60}{h_col2}')
            
            for crd in get_crds(api_instance):
                name, app = (crd['name'], crd.get('app'))
                print(f'{name:<60}{app}')
        except ApiException as e:
            print("Exception when calling ApiextensionsV1Api->list_custom_resource_definition: %s\n" % e)
