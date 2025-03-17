import logging, requests
import pandas as pd
import sys, time, json, re
from dateutil.parser import parse
from datetime import datetime, timedelta

logging.basicConfig(level=logging.ERROR)

class PodioAPI:
    '''
    This Class object will serve as a Podio wrapper. It can use api access to get info from Podio. This can get the data structure info 2x daily to/
    adjust the MongoDB based on any fields being added/deleted/name_changed.  It can also pull actual data from Podio then clean it to get the field label and field value to return to MongoDB
    '''
    def __init__(self, base_url, org_id, username, password, client_id, client_secret):
        self.api_count = 0
        self.data_size = 0
        self.base_url = base_url
        self.org_id = org_id
        self.secret_level = 1
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = self.get_access_token()
        
    def get_access_token(self):
        '''
        Get Podio auth token for API use
        '''
        auth_url = self.base_url + 'oauth/token'
        response = requests.post(auth_url, data={
            'grant_type': 'password',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'username': self.username,
            'password': self.password
        })
        self.api_count += 1
        if response.status_code == 200:
            self.data_size += len(response.content)
            return response.json().get('access_token')

    def clean_item(self, item):
        '''
        This is the item cleaner for actual data from Podio.  The cleaning is slightly different between cleaning actual data and cleaning data structure data
        '''
        if not item:
            return None
        item_dict = {}
        for field in item['fields']:
            field_dict = {}
            field_id = field['field_id']
            field_label = field['label']
            values = field['values']
            field_type = field['type']
            field_external_id = field['external_id']
            match field_type:
                case 'date':
                    value = ','.join([value['start'] for value in values])
                case 'contact':
                    value = ','.join([value['value']['name'] for value in values])
                case 'text':
                    value = ','.join([re.sub(r'<.*?>','',(value['value'])) for value in values])
                case 'category':
                    value = ','.join([value['value']['text'] for value in values])
                case 'app':
                    value = ','.join([str(value['value']['item_id']) for value in values])
                case 'phone' | 'email' | 'number' | 'location':
                    value = ','.join([value['value'] for value in values])
                case 'calculation':
                    if 'start' in values[0].keys():
                        value = ','.join([value['start'] for value in values])
                    else:
                        try:
                            value = [parse(value['value']).strftime('%Y-%m-%d') for value in values]
                            value = ','.join(value)
                        except:
                            value = [value['value'] for value in values]
                            float_values = []
                            for v in value:
                                try:
                                    float_values.append(float(v))
                                except ValueError:
                                    float_values.append(v)

                            value = float_values[0]
                case 'money':
                    value = float(values[0]['value'])
                case _:
                    skip = 1
                    print('skipped')
                    pass # Error logic to send email to CRM Admin for fix
            field_dict = {
                'field_id': field_id,
                'field_label': field_label,
                'field_type': field_type,
                'field_value': value
            }
            item_dict[str(field_id)] = field_dict
        return item_dict

    def get_filtered_items(self, app_id, filters):
        '''
        Resource intensive.  Can only run about 15 consecutive API calls in a minute.  250 API calls in an hour.  Can add sleep func to get past the per minute limit. Can also adjust so every API call it moves the token credentials to a new API token.  This should give enough API calls to run correctly.  This will take a parameter dict to fiter info from Podio and return up to 500 items that match the parameter.  This then uses an offest to continue calling for the rest of the results.  Then cleans and returns
        {
            field label: 
                {
                    field_label: field_value
                    }
            }
        '''
        self.formatted_app_id = str(app_id)
        # if not self.access_token:
        #     logging.error("Getting new access token")
        #     self.access_token = self.get_access_token()

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        url = f'{self.base_url}item/app/{app_id}/filter/'
        limited = 'limit' in filters.keys()
        limit = filters.pop('limit', 500)  # Default limit to 500 if not included in filter
        offset = 0

        all_items = {}
        count = 1
        while True:
            response = requests.post(url, headers=headers, json={'filters': filters, 'limit': limit, 'offset': offset})
            self.data_size += len(response.content)

            if response.status_code == 200:
                self.api_count += 1
                items = response.json()['items']
                if len(items) > 0 :
                    for item in items:
                        item_dict = self.clean_item(item)
                        all_items[item['item_id']] = item_dict
                    offset += len(items)
                else:
                    items = []

                # Break if the number of items is less than the limit (all items gathered) or if response is limited
                if len(items) < limit or limited:
                    return all_items

            elif response.json()['error'] == 'rate_limit':  # Rate limit exceeded.  Can be passed by waiting 5 min.
                if count <= 4:
                    self.secret_level = (self.secret_level + 1) % 4
                    self.client_id = self.secrets[self.secret_level]['client_id']
                    self.client_secret = self.secrets[self.secret_level]['client_secret']
                    self.access_token = self.get_access_token()
                    count += 1
                else:
                    print('Rate limit exceeded.  Sleeping for 300 seconds.')
                    number = 0
                    while number <= 300:
                        sys.stdout.write(f'\r{number}/300')
                        time.sleep(1)
                        sys.stdout.flush()
                        number += 1
                    count = 1
            else:
                logging.error(f"Failed to retrieve items: {response.json()}\n"
                            f"PARAMETERS\nFILTERS: {filters}\nLIMIT: {limit}\nOFFSET: {offset}\nRESPONSE: {response.json()}") # For troubleshooting.  Will want email notification on failure as well as logs.
                return None

    def get_org(self):
        '''
        Non resource intensive.  Can run 1000 API calls an hour no per minute/5minute rates.  This will get the space data structure info.
        '''
        url = f'{self.base_url}org/{self.org_id}/all_spaces'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers)
        self.data_size += len(response.content)
        self.api_count += 1
        return response.json()

    def get_apps_in_space(self, space_id):
        '''
        Non resource intensive.  Can run 1000 API calls an hour no per minute/5minute rates. This will get the apps data structure info for a space.
        '''
        url = self.base_url + f'app/space/{space_id}/'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        space_response = requests.get(url, headers=headers)
        self.api_count += 1
        apps = space_response.json()
        data = []
        for app in apps:
            if space_response.status_code == 200:
                space_app_id = str(app['space_id']) + '.' + str(app['app_id'])
                app_name = app['config']['name']
                tuple = (space_app_id, app_name)
                data.append(tuple)
        return data
    
    def get_app_fields_data(self, app_id):
        '''
        Non resource intensive.  Can run 1000 API calls an hour no per minute/5minute rates. This will get the fields data structure info for an app.
        '''
        url = self.base_url + f'app/{app_id}'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers)
        self.data_size += len(response.content)
        self.api_count += 1
        if 'fields' in response.json().keys():
            fields = response.json()['fields']
            fields_info = {}
            for field in fields:
                field_hidden = field['config']['hidden']
                field_id = field['field_id']
                field_label = field['label']
                field_type = field['type']
                if 'return_type' in field.keys():
                    field_return_type = field['return_type']
                else:
                    field_return_type = field_type
                fields_info[field_id] = {'field_label': field_label, 'field_id': field_id, 'hidden': field_hidden, 'type': field_type, 'return_type': field_return_type}
        else:
            fields_info = {}
        return fields_info

    def get_podio_system_setup(self):
        '''
        Non resource intensive.  This will go through and get all data structure info for every app in every space of a single organization inside of Podio.  It currently takes 380 API calls to run this method(10/10/2024).  If we go above 1000 API calls to run this method we can add a switch to change the API creds with every call.  A single user can have 5 API creds.  This will give a total of 5000 non resource intensive API calls an hour. 
        '''
        print('Getting spaces in organization')
        org_response = self.get_org()  # Getting spaces in organization
        org_info = {}
        for space in org_response:
            space_id = space['space_id']
            if 'name' in space.keys():
                space_name = space['name']
                if space_name != 'Fluent Solar':
                    print(f'Getting apps in space: {space_name}')
                    app_response = self.get_apps_in_space(space_id)  # Getting apps in space
                    for app in app_response:
                        print(f'Getting fields in app: {space_name}/{app[1]}')
                        space_app_id, app_name = app
                        space_id, app_id = space_app_id.split('.')
                        if space_name not in org_info:
                            org_info[space_name] = {}
                        org_info[space_name][app_name] = {
                            'space_app_id': space_app_id,
                            'app_id': app_id,
                            'fields': self.get_app_fields_data(app_id)
                        } # Getting field info in app
        return org_info

    def get_podio_item_values(self, item_id):
        '''
        Resource intensive.  Can only run about 15 consecutive API calls in a minute.  250 API calls in an hour.  Can add sleep func to get past the per minute limit. Can also adjust so every API call it moves the token credentials to a new API token.  This should give enough API calls to run correctly.  This will get a single item's data from Podio then cleans and returns {field label: field value}
        '''
        if not self.access_token:
            self.access_token = self.get_access_token()
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f'{self.base_url}item/{item_id}/value'
        
        response = requests.get(url, headers=headers)
        item = {'fields': response.json()}
        if response.status_code == 200:
            return {'item_id': item_id, 'data': self.clean_item(item)}
        else:
            print(f"Failed to get item {item_id}. Response: {response.json()}")
            return None

    def create_hook(self, url, ref_type, ref_id, event_type):
        # self.access_token = self.get_app_access_token()
        data = {
            'ref_type': ref_type,
            'ref_id': ref_id,
            'type': event_type,
            'url': url
        }
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        url = f'{self.base_url}hook/{ref_type}/{ref_id}/'
        response = requests.post(url, headers=headers, json=data)
        return response.json()
