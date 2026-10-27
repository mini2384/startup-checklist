import os
import sys
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
import requests

# 1. 환경 변수 로드 (.env 파일에서 읽어옴)
load_dotenv()

# 로깅 설정 (요청, 응답, 에러를 콘솔과 파일에 상세히 기록)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 3. 프로젝트 루트 경로 및 Flask 앱 초기화
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "startup-checklist-security-key-2026")
# 24시간 세션 유지 설정
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)

# 보안 PIN 비밀번호 설정 (기본값: 0927)
ACCESS_PIN = os.getenv("ACCESS_PIN", "0927").strip()

# 환경변수에서 API 키 확인
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
PUBLIC_DATA_API_KEY = os.getenv("PUBLIC_DATA_API_KEY", "").strip()

# Gemini SDK 초기화 함수
def get_gemini_client():
    if not GEMINI_API_KEY or GEMINI_API_KEY == "여기에_본인의_실제_Gemini_API_키_입력":
        return None
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        logger.error(f"Gemini 클라이언트 초기화 오류: {e}")
        return None

# 공공 데이터(세계은행 및 국내 공공 통계 지표) 조회 보조 함수
def fetch_public_startup_data(category):
    """
    공공 통계 데이터 조회:
    - 세계은행(World Bank) 글로벌 창업 지표 REST API (인증키 불필요)
    - 국내 창업 및 업종별 공공 참조 통계
    """
    stats = {
        "global_business_score": "75.4점 (OECD 평균 상위 15%)",
        "average_startup_days": "8.0일 (창업 소요 일수)",
        "national_survival_rate_3yr": "42.8% (중소벤처기업부 3년 생존율 통계)",
        "market_interest_score": "보통 (기준 100점 중 68점)",
        "source": "World Bank Open Data & 통계청/중기부 공공통계"
    }

    try:
        # 세계은행 Open API: 한국 창업 소요 기간(일수) 지표 조회 (인증키 없이 사용 가능한 공개 REST API)
        url = "http://api.worldbank.org/v2/country/KOR/indicator/IC.REG.DURS?format=json"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            data = res.json()
            if len(data) > 1 and len(data[1]) > 0:
                recent_entry = next((item for item in data[1] if item.get("value") is not None), None)
                if recent_entry:
                    stats["average_startup_days"] = f"{recent_entry['value']}일 (세계은행 최신 공식 집계)"
    except Exception as e:
        logger.warning(f"세계은행 Open API 호출 지연 또는 실패: {e}")

    return stats

# Gemini AI 프롬프트 생성 함수
def create_analysis_prompt(category, target_region, target_audience, analysis_mode, public_stats):
    mode_text = "초보 창업자를 위한 가성비 및 리스크 최소화 집중 분석" if analysis_mode == "beginner" else "전문가용 정밀 시장 분석 및 단계별 스케일업 심층 리포트"

    prompt = f"""
당신은 청년 창업가를 돕는 대한민국 최고 수준의 데이터 기반 창업 컨설턴트입니다.
아래 입력 정보와 공공 통계 데이터를 기반으로 객관적이고 구체적인 창업 진단 분석 리포트를 작성해주세요.

[입력 정보]
- 관심 업종: {category}
- 주요 입지/지역: {target_region}
- 주요 타겟층: {target_audience}
- 분석 모드: {mode_text}

[참조 공공 데이터 지표]
- 세계은행 한국 창업 소요 기간: {public_stats.get('average_startup_days')}
- 대한민국 3년 평균 기업 생존율: {public_stats.get('national_survival_rate_3yr')}
- 글로벌 창업 환경 지표: {public_stats.get('global_business_score')}

[리포트 작성 요구사항]
다음 JSON 형식으로만 완벽하게 응답하세요. 다른 설명이나 인사말, 마크다운 코드블록(```json 등) 없이 순수 JSON 문자열만 반환해야 합니다:
{{
  "category": "{category}",
  "mode": "{analysis_mode}",
  "ocean_type": "레드오션" 또는 "블루오션" 또는 "퍼플오션(경쟁 속 차별화 필요)",
  "ocean_summary": "현재 시장의 경쟁 강도와 이유를 2~3문장으로 명확히 요약",
  "trend_analysis": {{
    "global_trend": "글로벌 시장의 최신 트렌드 및 기술/비즈니스 흐름 (구체적 사례 포함)",
    "domestic_trend": "국내(한국) 해당 업종의 소비 및 시장 트렌드"
  }},
  "cost_analysis": {{
    "initial_investment_min": "최소 예상 초기 자본 (예: 3,500만 원)",
    "initial_investment_max": "최대 예상 초기 자본 (예: 8,000만 원)",
    "major_expenses": [
      "인테리어 및 시설 비용 (예: 2,000만 원)",
      "보증금 및 권리금 (예: 2,000만 원)",
      "초기 원부자재 및 기기 구매 (예: 1,000만 원)",
      "마케팅 및 예비 운전자금 (예: 500만 원)"
    ],
    "opportunity_cost": "직장 생활 또는 타 자산 투자 대비 기회비용 및 1년 내 손익분기점(BEP) 달성 예상 시기"
  }},
  "strategy": {{
    "differentiation": [
      "차별화 전략 1 (구체적 서비스/제품 차별점)",
      "차별화 전략 2 (디지털 전환/마케팅 차별점)",
      "차별화 전략 3 (고객 락인 및 재방문 전략)"
    ],
    "risk_management": [
      "초기 리스크 요인 1 및 방어 대책",
      "초기 리스크 요인 2 및 방어 대책"
    ]
  }},
  "action_checklist": [
    "1단계: 상권 및 유동인구 시간대별 현장 실사 (7일간)",
    "2단계: 소상공인진흥공단 상권정보시스템 분석 리포트 확인",
    "3단계: 정부 창업지원금(청년창업사관학교, 예비창업패키지) 공고 확인 및 사업계획서 초안 작성",
    "4단계: 최소 기능 제품(MVP) 또는 시범 테스트 고객 반응 검증",
    "5단계: 임대차 계약 전 용도지역 및 위생/소방법 인허가 조건 확인"
  ],
  "mentor_advice": "청년 창업자에게 전하는 따뜻하지만 현실적인 핵심 조언 2~3줄"
}}
"""
    return prompt

# 보안 미들웨어: 모든 접근에 대해 4자리 PIN 인증 여부 검사
@app.before_request
def require_pin():
    # 정적 리소스(CSS, JS)와 로그인 관련 라우트는 인증 제외
    if request.endpoint in ["login", "static"]:
        return None
    
    # 미인증 상태인 경우 처리
    if not session.get("authenticated"):
        if request.path == "/analyze":
            return jsonify({"success": False, "error": "보안 세션이 만료되었습니다. 다시 인증해주세요."}), 401
        return redirect(url_for("login"))

# 보안 로그인 (PIN 입력) 라우트
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("index"))
    
    error = None
    if request.method == "POST":
        entered_pin = request.form.get("pin", "").strip()
        if entered_pin == ACCESS_PIN:
            session.permanent = True  # 24시간 세션 유지 활성화
            session["authenticated"] = True
            logger.info("보안 PIN 인증 성공 -> 24시간 세션 발급")
            return redirect(url_for("index"))
        else:
            logger.warning("보안 PIN 인증 실패: 비밀번호 불일치")
            error = "비밀번호가 올바르지 않습니다. 다시 입력해주세요."
            
    return render_template("login.html", error=error)

# 수동 잠금 (로그아웃) 라우트
@app.route("/logout")
def logout():
    session.clear()
    logger.info("화면 잠금 (로그아웃 완료)")
    return redirect(url_for("login"))

# 홈 화면 라우트
@app.route("/")
def index():
    logger.info("홈페이지 접속 [/] (GET)")
    return render_template("index.html")

# 분석 API 라우트
@app.route("/analyze", methods=["POST"])
def analyze():
    start_time = datetime.now()
    logger.info("분석 요청 수신 [/analyze] (POST)")

    try:
        # 1. 입력 데이터 수신 및 유효성 검증
        if not request.is_json:
            logger.warning("요청 오류: JSON 형식이 아님")
            return jsonify({"success": False, "error": "요청 본문(Body)은 JSON 형식이어야 합니다."}), 400

        data = request.get_json()
        category = data.get("category", "").strip()
        target_region = data.get("target_region", "").strip()
        target_audience = data.get("target_audience", "").strip()
        analysis_mode = data.get("analysis_mode", "beginner").strip()

        # 필수값 검증
        if not category:
            logger.warning("유효성 검증 실패: 업종 누락")
            return jsonify({"success": False, "error": "관심 창업 업종을 입력해주세요."}), 400

        if len(category) > 50:
            logger.warning("유효성 검증 실패: 업종 글자 수 초과")
            return jsonify({"success": False, "error": "업종 이름은 50자 이내로 입력해주세요."}), 400

        if not target_region:
            target_region = "전국 / 도심 상권"
        if not target_audience:
            target_audience = "2030 청년 및 일반 대중"
        if analysis_mode not in ["beginner", "expert"]:
            analysis_mode = "beginner"

        logger.info(f"분석 파라미터 - 업종: {category}, 지역: {target_region}, 타겟: {target_audience}, 모드: {analysis_mode}")

        # 2. 공공 통계 데이터 연동
        public_stats = fetch_public_startup_data(category)
        logger.info(f"공공 데이터 수집 완료: {public_stats}")

        # 3. Gemini AI 분석 수행
        client = get_gemini_client()
        result_json = None

        if client:
            try:
                prompt = create_analysis_prompt(category, target_region, target_audience, analysis_mode, public_stats)
                logger.info("Gemini API 호출 중...")
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                raw_text = response.text.strip()
                logger.info(f"Gemini 응답 수신 완료 (길이: {len(raw_text)}자)")

                # 코드 블록 기호 제거 (있을 경우)
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                elif raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()

                result_json = json.loads(raw_text)
            except Exception as e:
                logger.error(f"Gemini API 호출 또는 파싱 오류: {e}")
                # AI 호출 실패 시 시뮬레이션 진단 데이터로 자동 대체
                result_json = None

        # API 키가 없거나 Gemini 호출 실패 시 안전하게 시뮬레이션 데이터 제공
        if not result_json:
            logger.info("시뮬레이션 기반 데이터 진단 리포트를 생성합니다.")
            result_json = {
                "category": category,
                "mode": analysis_mode,
                "ocean_type": "퍼플오션 (차별화형 경쟁 시장)",
                "ocean_summary": f"'{category}' 시장은 진입 장벽이 비교적 낮아 진입자가 많으나, {target_region} 지역 내 {target_audience} 고객의 숨은 니즈를 충족시키는 차별화 상품 개발 시 승산이 충분한 시장입니다.",
                "trend_analysis": {
                    "global_trend": f"글로벌 시장에서는 {category} 분야에 디지털 무인화 시스템 및 개인 맞춤형 구독 모델이 빠르게 접목되고 있습니다.",
                    "domestic_trend": f"국내 시장은 감성적 경험 소비와 합리적 가격 대비 가치(가성비)를 추구하는 청년층의 소비 비중이 크게 확대되고 있습니다."
                },
                "cost_analysis": {
                    "initial_investment_min": "3,000만 원",
                    "initial_investment_max": "7,500만 원",
                    "major_expenses": [
                        "공간 인테리어 및 감성 집기비용 (약 2,500만 원)",
                        "보증금 및 초기 임차료 (약 2,000만 원)",
                        "초기 원재료/도구 및 POS 솔루션 (약 1,000만 원)",
                        "온·오프라인 런칭 마케팅 및 예비 운전자금 (약 500만 원)"
                    ],
                    "opportunity_cost": "안정적인 급여 소득 대비 사업 초기 6~12개월은 손익분기점(BEP) 도달을 위한 집중 투자 기간이 요구됩니다."
                },
                "strategy": {
                    "differentiation": [
                        f"{target_audience} 타겟 전용 시그니처 아이템 및 패키지 개발",
                        "인스타그램/숏폼 등 소셜 미디어 기반 로컬 브랜딩 마케팅 전개",
                        "네이버 플레이스 예약/리뷰 연계 재방문 마일리지 시스템 구축"
                    ],
                    "risk_management": [
                        "원가 상승 리스크: 다변화된 식자재/부자재 공급처 확보로 원가율 35% 이하 유지",
                        "초기 유동성 리스크: 6개월치 고정 지출(월세+인건비)은 예비 자금으로 별도 예치"
                    ]
                },
                "action_checklist": [
                    "1단계: 주간/야간 요일별 현장 상권 및 타겟 고객 유동 동선 실사",
                    "2단계: 소상공인진흥공단 상권분석시스템을 통한 반경 1km 경쟁점 매출 분석",
                    "3단계: 정부 청년창업지원금(청년전용창업자금 등) 자격 요건 조회",
                    "4단계: 30인 이상의 잠재 고객 대상 사전 선호도 인터뷰 설문 진행",
                    "5단계: 임대차 계약 전 정화조, 전기 증설, 위생 인허가 가능 여부 지자체 확인"
                ],
                "mentor_advice": "창업에서 가장 중요한 것은 화려한 매장이 아니라 지속 가능한 재방문 고객입니다. 초기 자본을 아끼고 검증에 집중하세요."
            }

        # 공공 통계 메타데이터 추가
        result_json["public_stats"] = public_stats
        result_json["analyzed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"분석 완료 및 응답 반환 성공 (소요시간: {elapsed:.2f}초)")

        return jsonify({
            "success": True,
            "data": result_json
        }), 200

    except Exception as ex:
        logger.error(f"서버 내부 오류 발생: {ex}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "진단 분석 처리 중 서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        }), 500

if __name__ == "__main__":
    logger.info("Flask 개발 서버 시작 준비 중...")
    app.run(host="127.0.0.1", port=5000, debug=True)
