import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

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
        print(f"ID: {d.get('id')} | Status: {d.get('status')} | Commit: {d.get('commit', {}).get('id')} | CreatedAt: {d.get('createdAt')}")

def trigger_deploy(clear_cache=True):
    payload = {'clearCache': 'clear' if clear_cache else 'do_not_clear'}
    r = requests.post(f'https://api.render.com/v1/services/{SERVICE_ID}/deploys', headers=HEADERS, json=payload)
    print('TRIGGER DEPLOY STATUS:', r.status_code)
    try:
        data = r.json()
        dep = data.get('deploy', {})
        print(f"Novo Deploy Iniciado! ID: {dep.get('id')} | Status: {dep.get('status')}")
        return dep.get('id')
    except Exception:
        print(r.text)
        return None

def wait_for_deploy(deploy_id=None, timeout_sec=300):
    print("[*] Aguardando compilação e deploy na Render...")
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        r = requests.get(f'https://api.render.com/v1/services/{SERVICE_ID}/deploys', headers=HEADERS)
        if r.status_code == 200:
            deploys = r.json()
            if deploys:
                latest = deploys[0].get('deploy', {})
                cur_id = latest.get('id')
                status = latest.get('status')
                commit_id = latest.get('commit', {}).get('id', '')[:7]
                print(f"[{int(time.time() - start_time)}s] Deploy {cur_id} ({commit_id}): Status = {status}")
                if status == 'live':
                    print("✅ DEPLOY CONCLUÍDO COM SUCESSO! O SITE NA NUVEM ESTÁ LIVE!")
                    return True
                elif status in ('build_failed', 'canceled', 'deactivated'):
                    print(f"❌ Deploy terminou com status: {status}")
                    return False
        time.sleep(10)
    print("⚠️ Timeout aguardando deploy.")
    return False

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'list'
    if action == 'list':
        list_deploys()
    elif action == 'trigger':
        dep_id = trigger_deploy(clear_cache=True)
        if dep_id:
            wait_for_deploy(dep_id)
    elif action == 'status':
        list_deploys()

