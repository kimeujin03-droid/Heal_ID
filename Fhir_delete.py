import requests

# 1. Fhir서버에 삭제할 환자 ID 목록
target_ids = [1, 2 ]  # 여기에 삭제할 환자 ID들을 넣으세요
FHIR_SERVER_URL = ""

for pid in target_ids:

    url = f"{FHIR_SERVER_URL}/{pid}"
    response = requests.delete(url)
    
    # 200(성공) 또는 204(삭제됨/내용없음)면 성공
    if response.status_code in [200, 204]:
        print(f"✅ ID {pid} 삭제 완료!")
    elif response.status_code == 404:
        print(f"⚠️ ID {pid}는 이미 없거나 찾을 수 없습니다.")
    else:
        print(f"❌ ID {pid} 삭제 실패 (에러코드: {response.status_code})")


print("끝! ✨")
