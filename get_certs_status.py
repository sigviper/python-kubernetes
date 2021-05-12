from kubernetes import client, config
import time
from kubernetes.client.rest import ApiException
from pprint import pprint
import json
import argparse


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


def get_problematic_certificaterequests(api_instance, knamespace=None):
    kgroup      = "cert-manager.io"
    kversion    = "v1"
    kplural     = "certificaterequests"
    kshort       = "crs"

    api_instance = client.CustomObjectsApi(api_client)
    problematic_crs = []

    api_response = api_instance.list_cluster_custom_object(kgroup, kversion, kplural)
    resp = dict(api_response.items())
    for crs in resp['items']:
        crs_name        = crs['metadata']['name']
        crs_namespace   = crs['metadata']['namespace']
        crs_status = "Unknown status"
        crs_ok = False

        if knamespace and knamespace != crs_namespace:
            continue    # only include objects from namespace set in params

        if crs.get('status'):
            crs_reason  = crs['status']['conditions'][0]['reason']
            crs_msg     = crs['status']['conditions'][0]['message']
            crs_status  = f'{crs_reason}: ' + crs_msg
            crs_ok      = (crs['status']['conditions'][0]['status'] == 'True')
        
        if not crs_ok:
            problematic_crs.append([crs_namespace, crs_name, crs_status])

    return sorted(problematic_crs, key=lambda x: (x[0],x[1]))


if __name__ == '__main__':
    parsea = argparse.ArgumentParser()
    parsea.add_argument('cluster', help='Context name from ~/kube/config')
    parsea.add_argument('-n' , '--namespace', help='Optional namespace to use as filter')
    args = parsea.parse_args()
    
    configuration = config.load_kube_config(context=args.cluster)

    with client.ApiClient(configuration) as api_client:
        api_instance = client.ApiextensionsV1Api(api_client)
        
        # Print Custom Resource Definition objects on the cluster:
        # try:
        #     h_col1 = 'CRD NAME'
        #     h_col2 = 'CRD\'s APP LABEL'
        #     print(f'{h_col1:<60}{h_col2}')
            
        #     for crd in get_crds(api_instance):
        #         name, app = (crd['name'], crd.get('app'))
        #         print(f'{name:<60}{app}')
        # except ApiException as e:
        #     print("Exception when calling ApiextensionsV1Api->list_custom_resource_definition: %s\n" % e)

        # Print problematic CertificateRequests
        print('Problematic CertificateRequests')
        try:
            problematic_crs = get_problematic_certificaterequests(api_client, args.namespace)
            h_col1 = 'NAMESPACE'
            h_col2 = 'CertificateRequest'.upper()
            h_col3 = 'STATUS'
            print(f'{h_col1:<20}{h_col2:<64}{h_col3}')
            for problem in problematic_crs:
                cn      = problem[0]
                cname   = problem[1]
                creason = problem[2][:100]
                print(f'{cn:<20}{cname:<64}{creason}')
        except ApiException as e:
            print("Exception when calling CustomObjectsApi->list_cluster_custom_object: %s\n" % e)

    # Automatic fixing of expired certs:
    # find crs, cert, order and secret that come from the same crequest and delete them in following order: secret, cert, order, crs