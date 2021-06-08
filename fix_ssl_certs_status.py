# Sometimes k8s cert-manager requests/orders are hanging or failing and this is the script to automate deletion of such stale resources

import sys
import time
import json
import argparse
from datetime import datetime, timedelta, timezone
from pprint import pprint
from kubernetes import client, config
from kubernetes.client.rest import ApiException

MINIMUM_AGE_MINUTES = 60

def get_problematic_certificaterequests(api_instance, knamespace=None):
    '''Problematic certificaterequests means no status or failed'''
    kgroup      = "cert-manager.io"
    kversion    = "v1"
    kplural     = "certificaterequests"

    problematic_crs = []

    api_response = api_instance.list_cluster_custom_object(kgroup, kversion, kplural)
    resp = dict(api_response.items())
    for crs in resp['items']:
        crs_ok          = False
        crs_namespace   = crs['metadata']['namespace']
        crs_time        = crs['metadata']['managedFields'][0]['time']
        crs_time        = datetime.strptime(crs_time, '%Y-%m-%dT%H:%M:%S%z')
        assert crs_time.tzname() == 'UTC'
        
        if crs_time + timedelta(minutes=MINIMUM_AGE_MINUTES) > datetime.now(timezone.utc):
            # CRS created less than MINIMUM_AGE_MINUTES ago
            continue

        if knamespace and knamespace != crs_namespace:
            continue    # only include objects from namespace set in params

        if crs.get('status'):
            crs_ok      = (crs['status']['conditions'][0]['status'] == 'True')
        
        if not crs_ok:
            problematic_crs.append(crs)

    return problematic_crs


def get_orders_by_name(api_instance, cert_name):
    '''Find orders matching label app.kubernetes.io/instance=resource_name'''
    kgroup      = "acme.cert-manager.io"
    kversion    = "v1"
    kplural     = "orders"

    orders = []
    api_response = api_instance.list_cluster_custom_object(kgroup, kversion, kplural)
    resp = dict(api_response.items())

    for order in resp['items']:
        order_name      = order['metadata']['name']
        label_name      = order['metadata']['annotations']['cert-manager.io/certificate-name']
        if label_name == cert_name:
            orders.append(order)

    return orders

if __name__ == '__main__':
    parsea = argparse.ArgumentParser()
    parsea.add_argument('cluster', help='Context name from ~/kube/config')
    parsea.add_argument('-n' , '--namespace', help='Optional namespace to use as filter')
    args = parsea.parse_args()
    
    configuration = config.load_kube_config(context=args.cluster)

    with client.ApiClient(configuration) as api_client:
        api_instance = client.CustomObjectsApi(api_client)
       
        # Automatic fixing of expired certs:
        # 1. find cerfificate requests that failed or have empty status
        # 2. using label app.kubernetes.io/instance= find a matching order
        # 3. delete both certificate request and order (deletion order IS important, crs must be deleted first, 
        #    otherwise new one will be created but not order and it will hang again)
        resources_to_delete = []
        try:
            problematic_crs = get_problematic_certificaterequests(api_instance, args.namespace)
            if not problematic_crs:
                print(f'No certificate requests problems found on {args.cluster}')
                sys.exit()

            print('To be deleted:')
            for crs in problematic_crs:
                crs_name        = crs['metadata']['name'].strip()
                crs_namespace   = crs['metadata']['namespace']
                cert_name  = crs['metadata']['annotations']['cert-manager.io/certificate-name']
                crs_status      = "Unknown status"
                crs_reason      = "Unknown reason"
                crs_msg         = "Unknown msg"
                if crs.get('status'):
                    crs_reason  = crs['status']['conditions'][0]['reason']
                    crs_msg     = crs['status']['conditions'][0]['message']
                    crs_status  = f'{crs_reason}: ' + crs_msg
                
                problematic_orders = get_orders_by_name(api_instance, cert_name)
                crs_to_delete = f"certificaterequest.cert-manager.io/{crs_name}"
                print(f"{crs_namespace:<20}{crs_to_delete}")

                # API Docs: https://cert-manager.io/v1.2-docs/reference/api-docs/
                # Also: `kubectl api-resources`
                resources_to_delete.append({
                        'ns'        : crs_namespace, 
                        'group'     : 'cert-manager.io',
                        'version'   : 'v1',
                        'plural'    : 'certificaterequests',
                        'name'      : crs_name 
                })

                for order_name in map(lambda x: x['metadata']['name'], problematic_orders):
                    # API Docs: https://cert-manager.io/v1.2-docs/reference/api-docs/
                    # Also: `kubectl api-resources`
                    resources_to_delete.append({
                        'ns'        : crs_namespace, 
                        'group'     : 'acme.cert-manager.io',
                        'version'   : 'v1',
                        'plural'    : 'orders',
                        'name'      : order_name 
                    })
                    print(f"{crs_namespace:<20}\t-order.acme.cert-manager.io/{order_name}")
               
        except ApiException as e:
            print("Exception when calling CustomObjectsApi->list_cluster_custom_object: %s\n" % e)

        # Actual delete happens here, after confirmation
        decide = input("Is this ok [Y/n]: ").strip()
        if decide == 'Y':
            print('Proceeding to delete')
            for rdel in resources_to_delete:
                try:
                    rns     = rdel['ns']
                    rgroup  = rdel['group']
                    rversion= 'v1'
                    rplural = rdel['plural']
                    rname   = rdel['name']
                    
                    # For development, dryRun
                    #api_response = api_instance.delete_namespaced_custom_object(rgroup, rversion, rns, rplural, rname, dry_run='All')
                    #pprint(api_response)
                    
                    api_response = api_instance.delete_namespaced_custom_object(rgroup, rversion, rns, rplural, rname)
                    resp_status = api_response['status'].upper()
                    resp_kind   = api_response['details']['kind']
                    resp_name   = api_response['details']['name']
                    print(f'{resp_status:<15}{resp_kind:<30}{resp_name}')
                except ApiException as e:
                    print("Exception when calling CustomObjectsApi->delete_namespaced_custom_object: %s\n" % e)    
        else:
            print('Not doing anything, exit')
        


        
    

