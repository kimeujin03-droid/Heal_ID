import mysql.connector
from config import DB_CONFIG, FHIR_SERVER_URL
import datetime
import requests
import time

# ==================================================================
# [최적화] DB 커넥션 풀 사용 (매번 연결 생성/종료 비용 감소)
# ==================================================================
_connection_pool = None

def get_connection_pool():
    """커넥션 풀을 반환합니다 (싱글톤 패턴)"""
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="heal_id_pool",
                pool_size=5,
                **DB_CONFIG
            )
            print("[INIT] DB 커넥션 풀 생성 완료")
        except mysql.connector.Error as err:
            print(f"❌ [DB 오류] 커넥션 풀 생성 실패: {err}")
    return _connection_pool

def get_db_connection():
    """커넥션 풀에서 연결을 가져옵니다."""
    try:
        pool = get_connection_pool()
        if pool:
            conn = pool.get_connection()
            return conn, conn.cursor(dictionary=True)
    except mysql.connector.Error as err:
        print(f"❌ [DB 오류] 커넥션 가져오기 실패: {err}")
    return None, None

# ==================================================================
# [최적화] 캐시: 환자 존재 여부 (5초마다 같은 ID 조회 방지)
# ==================================================================
_patient_cache = {}
_cache_timestamp = {}
CACHE_TTL = 300  # 5분 캐시

def check_patient_exists(patient_id):
    """환자 존재 여부를 캐시와 함께 확인합니다."""
    current_time = time.time()
    
    # 캐시에 있고 유효기간 내면 바로 반환
    if patient_id in _patient_cache:
        if current_time - _cache_timestamp.get(patient_id, 0) < CACHE_TTL:
            return _patient_cache[patient_id]
    
    conn, cursor = get_db_connection()
    if not conn: 
        return False, "DB 연결 실패"

    try:
        cursor.execute("SELECT id, last_updated FROM patients WHERE id = %s", (patient_id,))
        result = cursor.fetchone()
        
        if result:
            last_updated = result.get('last_updated')
            response = (True, str(last_updated) if last_updated else "기존 데이터 있음")
        else:
            response = (False, "신규 등록")
        
        # 캐시 저장
        _patient_cache[patient_id] = response
        _cache_timestamp[patient_id] = current_time
        
        return response
    except Exception as e:
        print(f"⚠️ DB 조회 에러: {e}")
        return False, f"에러: {e}"
    finally:
        if conn: 
            cursor.close()
            conn.close()

def register_or_update_patient(patient_id):
    """환자 정보를 등록하거나 갱신합니다."""
    conn, cursor = get_db_connection()
    if not conn: 
        return False, "DB 연결 실패"

    try:
        # UPSERT 패턴으로 변경 (SELECT 후 INSERT/UPDATE보다 효율적)
        sql = """
            INSERT INTO patients (id, last_updated) 
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE last_updated = %s
        """
        now = datetime.datetime.now()
        cursor.execute(sql, (patient_id, now, now))
        conn.commit()
        
        # 캐시 갱신
        _patient_cache[patient_id] = (True, str(now))
        _cache_timestamp[patient_id] = time.time()
        
        return True, f"환자 ID [{patient_id}] DB 처리 완료."
    except mysql.connector.Error as err:
        print(f"⚠️ DB 저장 에러: {err}")
        return False, f"DB 오류: {err}"
    finally:
        if conn:
            cursor.close()
            conn.close()

# ==================================================================
# [최적화 제거] FHIR 서버 전송 함수 (5초마다 호출 시 불필요)
# 필요할 때만 명시적으로 호출하도록 변경
# ==================================================================
def send_to_fhir_server(fhir_data):
    """FHIR 서버로 환자 데이터 전송 (필요시에만 호출)"""
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(
            f"{FHIR_SERVER_URL}/Patient", 
            json=fhir_data, 
            headers=headers,
            timeout=5  # 타임아웃 추가
        )
        
        if response.status_code in [200, 201]:
            print("[SUCCESS] FHIR 서버 저장 성공")
            
            # ID 추출 최적화
            patient_id = None
            location = response.headers.get('Location', '')
            
            if location and 'Patient/' in location:
                patient_id = location.split('Patient/')[-1].split('/')[0]
            
            if not patient_id:
                try:
                    patient_id = response.json().get('id')
                except:
                    pass
            
            return True, {"id": patient_id or "Unknown"}
        
        error_msg = response.text
        try:
            error_msg = response.json()
        except:
            pass
            
        return False, {"message": f"Server Error {response.status_code}", "detail": error_msg}
        
    except requests.Timeout:
        print(f"[ERROR] FHIR 서버 타임아웃")
        return False, {"message": "Request timeout"}
    except Exception as e:
        print(f"[ERROR] 연결 실패: {e}")
        return False, {"message": str(e)}


    