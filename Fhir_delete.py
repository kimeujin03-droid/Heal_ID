import requests

# 1. Fhir서버에 삭제할 환자 ID 목록
target_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70]  # 여기에 삭제할 환자 ID들을 넣으세요
FHIR_SERVER_URL = "http://cpslab.jejunu.ac.kr:10002/hapi-fhirstarters-simple-server/Patient/"

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