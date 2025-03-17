from fastapi import FastAPI, Request
from datetime import datetime
from pymongo import MongoClient, DESCENDING, ASCENDING
import httpx, asyncio, time
import PodioAPIWorkTEMP as fs
# comment
app = FastAPI()

podio_creds = {
    1: {
        'user': 'podio_user',
        'password': 'podio_password',
        'client_id': 'datasync1',
        'client_secret': 'podio_secret'
    },
    2: {
        'user': 'podio_user',
        'password': 'podio_password',
        'client_id': 'datasync2',
        'client_secret': 'podio_secret'
    },
    3: {
        'user': 'podio_user',
        'password': 'podio_password',
        'client_id': 'datasync3',
        'client_secret': 'podio_secret'
    },
    4: {
        'user': 'podio_user',
        'password': 'podio_password',
        'client_id': 'datasync4',
        'client_secret': 'podio_secret'
    }
}

mongo_connection_string = 'mongo_db_connect_string'
org_id = 1078713
base_url = 'https://api.podio.com/'

async def update_podio_creds():
    count = 0
    secret_no = (secret_no + 1) % len(podio_creds.keys())
    username = podio_creds[secret_no]['user']
    password = podio_creds[secret_no]['password']
    client_id = podio_creds[secret_no]['client_id']
    client_secret = podio_creds[secret_no]['client_secret']
    return [count, secret_no, username, password, client_id, client_secret]

# Helper function to verify hooks
async def verify_hook(data):
    hook_id = data['hook_id']
    url = f'https://api.podio.com/hook/{hook_id}/verify/validate'
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        return response.status_code

async def to_do_event_queue_add(data: dict, failed_attempts: int):
    client = MongoClient(mongo_connection_string)
    data['failed_attempts'] = failed_attempts
    data['timestamp'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')
    db = client.test
    collection = db.to_do_event_queue
    collection.insert_one(data)

    print(f'Added {data['item_id']} to "to_do_event_queue".')

async def complete_to_do_event_queue_docs(count, secret_no, podio_creds):
    if count == 990:
        count, secret_no, username, password, client_id, client_secret = await update_podio_creds()
        podio = fs.PodioAPI(base_url, org_id, username, password, client_id, client_secret)
    else:
        secrets = podio_creds[secret_no]
        username = secrets['user']
        password = secrets['password']
        client_id = secrets['client_id']
        client_secret = secrets['client_secret']
        podio = fs.PodioAPI(base_url, org_id, username, password, client_id, client_secret)

    async def process_event(data: dict, count):
        start = time.time()
        if data['type'] in ['item.update', 'item.create']:
            count += 1
            item_id = data['item_id']
            try:
                item_vals = podio.get_podio_item_values(item_id)
                print('item pulled from Podio.')
                item_vals = {str(key): val for key, val in item_vals.items()}
                item_vals['timestamp'] = data['timestamp']
                item_vals['current'] = 1
                client = MongoClient(mongo_connection_string)
                db = client.test
                collection = db.podio_items
                collection.update_many(
                    {'item_id': item_id},
                    {'$set': {'current': 0}}
                )
                print('Previous matching items marked as not current.')
                collection.insert_one(item_vals)
                print('item added to podio_items')
                collection = db.completed_event_queue
                data['completed_timestamp'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')
                collection.insert_one(data)
                print('item added to completed queue')
                collection = db.to_do_event_queue
                collection.delete_many({'item_id': item_id, 'type': 'item.update'})
                collection.delete_many({'item_id': item_id, 'type': 'item.create'})
                print('item removed from to_do_queue')
                result = f'Completed {data['type']} event queue for {data['item_id']}.'
                end = time.time()
                total_time = end - start
                print(f"Time taken for process_event: {total_time:.4f} seconds")

            
            except Exception as e:
                data['failed_attempts'] += 1
                data['timestamp'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')
                await to_do_event_queue_add(data, failed_attempts=data['failed_attempts'])
                if data['failed_attempts'] >= 10:
                    # send email to crm admin
                    pass
                result = f'Failed to complete {data['type']} for {data['item_id']}.\n{e}\n{data}'
        # elif data['type'] == 'item.delete':
        #     item_id = data['item_id']
        #     client = MongoClient(mongo_connection_string)
        #     db = client.test
        #     document_to_update = db.podio_items.find_one({'item_id': item_id}, sort=[('timestamp', -1)])
        #     try:
        #         timestamp = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')
        #         updated_data = {"$set": {"deleted": True, "timestamp": timestamp}}
        #         deleted = db.podio_items.update_one({'_id': document_to_update['_id']}, updated_data)
        #         result = f'Completed {data['type']} event queue for {data['item_id']}.'
        #     except:
        #         data['failed_attempts'] += 1
        #         data['timestamp'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')
        #         await to_do_event_queue_add(data)
        #         if data['failed_apptempts'] >= 10:
        #             # send email to crm admin
        #             pass
        #         result = f'Failed to complete {data['type']} for {data['item_id']}.'

        # elif data['type'] in ['app.create', 'app.update']:
        #     result = f'Passed {data['type']} for {data['app_id']}'
        print(result)
        return
    
    while True:
        client = MongoClient(mongo_connection_string)
        db = client.test
        collection = db.to_do_event_queue
        try:
            oldest_doc = collection.find_one(sort=[('timestamp', ASCENDING)])
            print(f'Item {oldest_doc['item_id']} found in to_do_queue')
            await process_event(oldest_doc, count)
        except TypeError as e:
            print('NoneType pulled from Mongo.  Sleeping')
            await asyncio.sleep(10)
    
@app.post("/item/update")
@app.get("/item/update")
async def item_update(request: Request):
    form_data = await request.form()
    data = {key: value for key, value in form_data.items()}

    if 'item_id' in data.keys():
        await to_do_event_queue_add(data, failed_attempts=0)

    elif 'hook_id' in data.keys():
        status_code = await verify_hook(data)
        print(status_code)
        return status_code
    


#     # # /item/delete route  Can send all create/update/delete to to_do_event_queue and handle separate processes with complete_to_do_event_queue() func
# @app.post("/item/delete")
# @app.get("/item/delete")
# async def item_delete(request: Request):
#     data = await request.form()
#     data_dict = {key: value for key, value in data.items()}
    
#     if 'item_id' in data_dict.keys():
#         await to_do_event_queue_add(data_dict)

#     elif 'hook_id' in data_dict.keys():
#         print(data_dict['hook_id'])
#         status_code = await verify_hook(data_dict['hook_id'])
#         return {'status': 'Webhook verified for item.delete', 'code': status_code}
    
#     return {'status': 'item.delete processed'}

# /app/create route
@app.post("/app/create")
@app.get("/app/create")
async def item_delete(request: Request):
    data = await request.form()
    data_dict = {str(key): value for key, value in data.items()}
    
    if 'app_id' in data_dict.keys():
        await to_do_event_queue_add(data, failed_attempts=0)

    elif 'hook_id' in data_dict.keys():
        status_code = await verify_hook(data_dict['hook_id'])
        return {'status': 'Webhook verified for item.delete', 'code': status_code}
    
    return {'status': 'app.create processed'}

# /app/update route
@app.post("/app/update")
@app.get("/app/update")
async def item_delete(request: Request):
    data = await request.form()
    data_dict = {str(key): value for key, value in data.items()}
    
    if 'app_id' in data_dict.keys():
        await to_do_event_queue_add(data, failed_attempts=0)

    elif 'hook_id' in data_dict.keys():
        status_code = await verify_hook(data_dict['hook_id'])
        return {'status': 'Webhook verified for app.delete', 'code': status_code}
    return {'status': 'app.delete processed'}

@app.on_event('startup')
async def start_sync():
    asyncio.create_task(complete_to_do_event_queue_docs(count=0, secret_no=1, podio_creds=podio_creds))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)