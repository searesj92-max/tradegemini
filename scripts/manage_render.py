import os
import requests
import json
import sys

API_KEY = os.environ.get("RENDER_API_KEY", "").strip()
HEADERS = {
    'Authorization': f'Bearer {API_KEY}',
    'Accept': 'application/json'
}
SERVICE_ID = os.environ.get("RENDER_SERVICE_ID", "srv-darilfh7lnhs73di5ibg")
OWNER_ID = os.environ.get("RENDER_OWNER_ID", "tea-darid017lnhs73dh5qag")

def list_deploys():
    r = requests.get(f'https://api.render.com/v1/services/{SERVICE_ID}/deploys', headers=HEADERS)
    print('DEPLOYS:')
    for item in r.json():
        d = item.get('deploy', {})
        print(f"ID: {d.get('id')} | Status: {d.get('status')} | Trigger: {d.get('trigger')} | CreatedAt: {d.get('createdAt')}")

def trigger_deploy():
    r = requests.post(f'https://api.render.com/v1/services/{SERVICE_ID}/deploys', headers=HEADERS, json={'clearCache': 'do_not_clear'})
    print('TRIGGER DEPLOY STATUS:', r.status_code)
    print(r.text)

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'list'
    if action == 'list':
        list_deploys()
    elif action == 'trigger':
        trigger_deploy()
