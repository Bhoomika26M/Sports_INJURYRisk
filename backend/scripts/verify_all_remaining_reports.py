import urllib.request, json

# 1. Login
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/auth/login',
    data=json.dumps({'email': 'coach@demo.com', 'password': 'demo123'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
res = urllib.request.urlopen(req)
token = json.loads(res.read())['access_token']
headers = {'Authorization': f'Bearer {token}'}

# 2. Get athletes
req_ath = urllib.request.Request('http://127.0.0.1:8000/api/v1/athletes?page_size=100', headers=headers)
athletes_resp = json.loads(urllib.request.urlopen(req_ath).read())
athletes = athletes_resp['items']
print(f"Total roster athletes returned: {len(athletes)}")

for a in athletes:
    ath_id = a['id']
    name = a.get('full_name') or a.get('user', {}).get('full_name', 'Unknown')
    # Get videos
    req_v = urllib.request.Request(f'http://127.0.0.1:8000/api/v1/videos?athlete_id={ath_id}', headers=headers)
    vids_data = json.loads(urllib.request.urlopen(req_v).read())
    vids = vids_data['items'] if isinstance(vids_data, dict) and 'items' in vids_data else (vids_data['videos'] if isinstance(vids_data, dict) and 'videos' in vids_data else vids_data)


    print(f"\n--- {name} ({a['sport_type']}, {a.get('position')}) ---")
    print(f"  Videos: {len(vids)}")
    for v in vids:
        vid_id = v['id']
        status = v['processing_status']
        print(f"  Video {vid_id} [{v['movement_type']}] status: {status}")
        if status == 'completed':
            # Check risk-score
            try:
                req_rs = urllib.request.Request(f'http://127.0.0.1:8000/api/v1/videos/{vid_id}/risk-score', headers=headers)
                rs_data = json.loads(urllib.request.urlopen(req_rs).read())
                overall = rs_data.get('overall_score')
                cat = rs_data.get('risk_category')
                print(f"    -> Score: {overall} / 100 ({cat} risk)")
                print(f"    -> Breakdown: {list(rs_data.get('score_breakdown', {}).keys())}")
            except Exception as e:
                print(f"    -> Risk score error: {e}")

            # Check downloads (CSV, PDF, Excel)
            for fmt, path in [('CSV', f'/videos/{vid_id}/biomechanics/export.csv'),
                              ('PDF', f'/videos/{vid_id}/report.pdf'),
                              ('Excel', f'/videos/{vid_id}/report.xlsx')]:
                try:
                    req_dl = urllib.request.Request(f'http://127.0.0.1:8000/api/v1{path}', headers=headers)
                    dl_res = urllib.request.urlopen(req_dl)
                    print(f"    -> {fmt} download: HTTP {dl_res.status} ({len(dl_res.read())} bytes)")
                except Exception as e:
                    print(f"    -> {fmt} download error: {e}")
