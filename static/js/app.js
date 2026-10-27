// ==========================================================================
// 청년 창업 체크리스트 프론트엔드 비동기 로직 (app.js)
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
    // 1. 주요 DOM 엘리먼트 참조
    const form = document.getElementById("analyze-form");
    const categoryInput = document.getElementById("category");
    const targetRegionInput = document.getElementById("target_region");
    const targetAudienceInput = document.getElementById("target_audience");
    const modeRadios = document.querySelectorAll('input[name="analysis_mode"]');
    const radioCards = document.querySelectorAll(".radio-card");
    const btnSubmit = document.getElementById("btn-submit");
    const btnText = btnSubmit.querySelector(".btn-text");
    const errorMessage = document.getElementById("error-message");
    const loadingSpinner = document.getElementById("loading-spinner");
    const resultSection = document.getElementById("result-section");
    const btnCopy = document.getElementById("btn-copy");
    const btnDownload = document.getElementById("btn-download");

    // 전역 변수: 최근 분석 결과 캐시 (복사 및 다운로드용)
    let currentAnalysisData = null;

    // 2. 라디오 카드 선택 UI 이벤트 연결
    modeRadios.forEach((radio) => {
        radio.addEventListener("change", () => {
            radioCards.forEach((card) => card.classList.remove("selected"));
            const parentCard = radio.closest(".radio-card");
            if (parentCard) {
                parentCard.classList.add("selected");
            }
        });
    });

    // 3. 에러 메시지 표시 보조 함수
    function showError(msg) {
        errorMessage.textContent = msg;
        errorMessage.style.display = "block";
        errorMessage.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    function hideError() {
        errorMessage.textContent = "";
        errorMessage.style.display = "none";
    }

    // 4. 로딩 상태 전환 함수
    function setLoading(isLoading) {
        if (isLoading) {
            btnSubmit.disabled = true;
            btnText.textContent = "시장 분석 및 AI 진단 중...";
            loadingSpinner.style.display = "block";
            resultSection.style.display = "none";
            loadingSpinner.scrollIntoView({ behavior: "smooth", block: "center" });
        } else {
            btnSubmit.disabled = false;
            btnText.textContent = "데이터 기반 종합 진단 리포트 생성하기";
            loadingSpinner.style.display = "none";
        }
    }

    // 5. 폼 제출 이벤트 핸들러
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        hideError();

        // 프론트엔드 입력값 검증
        const category = categoryInput.value.trim();
        const targetRegion = targetRegionInput.value.trim();
        const targetAudience = targetAudienceInput.value.trim();
        
        let selectedMode = "beginner";
        const checkedRadio = document.querySelector('input[name="analysis_mode"]:checked');
        if (checkedRadio) {
            selectedMode = checkedRadio.value;
        }

        if (!category) {
            showError("관심 창업 업종(예: 샐러드 카페, 무인 스터디룸 등)을 반드시 입력해주세요.");
            categoryInput.focus();
            return;
        }

        if (category.length > 50) {
            showError("업종 명칭은 50자 이내로 간결히 입력해주세요.");
            categoryInput.focus();
            return;
        }

        // 서버 전송 데이터 구성
        const payload = {
            category: category,
            target_region: targetRegion,
            target_audience: targetAudience,
            analysis_mode: selectedMode
        };

        setLoading(true);

        try {
            // Flask 백엔드 /analyze 엔드포인트 비동기 호출
            const response = await fetch("/analyze", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                const serverError = result.error || "분석 요청 중 알 수 없는 서버 오류가 발생했습니다.";
                showError(`⚠️ ${serverError}`);
                return;
            }

            // 분석 데이터 보관 및 화면 렌더링
            currentAnalysisData = result.data;
            renderResult(result.data);

        } catch (err) {
            console.error("API 요청 실패:", err);
            showError("서버와의 통신에 실패했습니다. Flask 서버 실행 상태 및 인터넷 연결을 확인해주세요.");
        } finally {
            setLoading(false);
        }
    });

    // 6. 결과 렌더링 함수
    function renderResult(data) {
        // 헤더 정보
        const badgeMode = document.getElementById("res-badge-mode");
        badgeMode.textContent = data.mode === "beginner" ? "🌱 초보자용 가성비 분석" : "🚀 전문가용 심층 리포트";
        document.getElementById("res-category-title").textContent = `[${data.category}] 창업 진단 리포트`;
        document.getElementById("res-analyzed-at").textContent = `분석 일시: ${data.analyzed_at || new Date().toLocaleString()}`;

        // 1. 오션 분석
        const oceanTypeEl = document.getElementById("res-ocean-type");
        const oceanSummaryEl = document.getElementById("res-ocean-summary");
        const oceanBoxEl = document.querySelector(".ocean-box");

        oceanTypeEl.textContent = data.ocean_type;
        oceanSummaryEl.textContent = data.ocean_summary;

        // 오션 타입별 클래스 초기화 및 부여
        oceanBoxEl.classList.remove("ocean-red", "ocean-blue");
        if (data.ocean_type.includes("레드")) {
            oceanBoxEl.classList.add("ocean-red");
        } else if (data.ocean_type.includes("블루")) {
            oceanBoxEl.classList.add("ocean-blue");
        }

        // 2. 공공 통계 메타 지표
        const stats = data.public_stats || {};
        document.getElementById("res-stat-days").textContent = stats.average_startup_days || "8.0일";
        document.getElementById("res-stat-survival").textContent = stats.national_survival_rate_3yr || "42.8%";
        document.getElementById("res-stat-score").textContent = stats.global_business_score || "75.4점";

        // 3. 트렌드 분석
        const trends = data.trend_analysis || {};
        document.getElementById("res-trend-global").textContent = trends.global_trend || "글로벌 트렌드 데이터를 수집 중입니다.";
        document.getElementById("res-trend-domestic").textContent = trends.domestic_trend || "국내 트렌드 데이터를 수집 중입니다.";

        // 4. 비용 분석
        const costs = data.cost_analysis || {};
        const minCost = costs.initial_investment_min || "3,000만 원";
        const maxCost = costs.initial_investment_max || "7,000만 원";
        document.getElementById("res-cost-range").textContent = `${minCost} ~ ${maxCost}`;

        const expensesList = document.getElementById("res-cost-expenses");
        expensesList.innerHTML = "";
        (costs.major_expenses || []).forEach((exp) => {
            const li = document.createElement("li");
            li.textContent = exp;
            expensesList.appendChild(li);
        });

        document.getElementById("res-cost-opportunity").textContent = costs.opportunity_cost || "손익분기점 도달까지 철저한 운전자금 관리가 필요합니다.";

        // 5. 차별화 전략 및 리스크 관리
        const strategy = data.strategy || {};
        const diffList = document.getElementById("res-strategy-diff");
        diffList.innerHTML = "";
        (strategy.differentiation || []).forEach((item) => {
            const li = document.createElement("li");
            li.textContent = item;
            diffList.appendChild(li);
        });

        const riskList = document.getElementById("res-strategy-risk");
        riskList.innerHTML = "";
        (strategy.risk_management || []).forEach((item) => {
            const li = document.createElement("li");
            li.textContent = item;
            riskList.appendChild(li);
        });

        // 6. 액션 체크리스트
        const checklist = document.getElementById("res-action-checklist");
        checklist.innerHTML = "";
        (data.action_checklist || []).forEach((step) => {
            const li = document.createElement("li");
            li.textContent = step;
            checklist.appendChild(li);
        });

        // 7. 멘토 조언
        document.getElementById("res-mentor-advice").textContent = data.mentor_advice || "고객의 진짜 문제를 해결하는 상품에 집중하세요.";

        // 결과 카드 표시 및 스크롤
        resultSection.style.display = "block";
        resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    // 7. 결과 복사 기능
    btnCopy.addEventListener("click", () => {
        if (!currentAnalysisData) return;

        const textToCopy = `
[창업 진단 리포트] ${currentAnalysisData.category}
- 진단 일시: ${currentAnalysisData.analyzed_at}
- 시장 진단: ${currentAnalysisData.ocean_type}
- 시장 현황: ${currentAnalysisData.ocean_summary}

■ 공공 데이터 지표
- 창업 소요 일수: ${currentAnalysisData.public_stats?.average_startup_days}
- 3년 생존율: ${currentAnalysisData.public_stats?.national_survival_rate_3yr}
- 비즈니스 지표: ${currentAnalysisData.public_stats?.global_business_score}

■ 시장 트렌드
- 글로벌: ${currentAnalysisData.trend_analysis?.global_trend}
- 국내: ${currentAnalysisData.trend_analysis?.domestic_trend}

■ 초기 투자 자본 및 비용
- 예상 범위: ${currentAnalysisData.cost_analysis?.initial_investment_min} ~ ${currentAnalysisData.cost_analysis?.initial_investment_max}
- 주요 항목: ${(currentAnalysisData.cost_analysis?.major_expenses || []).join(" / ")}
- 기회비용: ${currentAnalysisData.cost_analysis?.opportunity_cost}

■ 차별화 전략
${(currentAnalysisData.strategy?.differentiation || []).map(s => "- " + s).join("\n")}

■ 리스크 방어 대책
${(currentAnalysisData.strategy?.risk_management || []).map(r => "- " + r).join("\n")}

■ 5단계 액션 체크리스트
${(currentAnalysisData.action_checklist || []).map(c => "[ ] " + c).join("\n")}

■ 멘토 조언:
"${currentAnalysisData.mentor_advice}"
`.trim();

        navigator.clipboard.writeText(textToCopy).then(() => {
            const originalText = btnCopy.textContent;
            btnCopy.textContent = "✅ 복사 완료!";
            setTimeout(() => {
                btnCopy.textContent = originalText;
            }, 2000);
        }).catch(err => {
            alert("클립보드 복사에 실패했습니다. 권한을 확인해주세요.");
        });
    });

    // 8. Markdown 파일 다운로드 기능
    btnDownload.addEventListener("click", () => {
        if (!currentAnalysisData) return;

        const mdContent = `# [창업 진단 리포트] ${currentAnalysisData.category}

> **분석 모드**: ${currentAnalysisData.mode === "beginner" ? "초보자용 가성비 분석" : "전문가용 심층 리포트"}  
> **분석 일시**: ${currentAnalysisData.analyzed_at}  
> **출처**: World Bank Open Data, 대한민국 공공데이터포털, Google Gemini 2.5 Flash

---

## 1. 시장 경쟁 환경 진단
- **오션 분류**: \`${currentAnalysisData.ocean_type}\`
- **진단 총평**:  
  ${currentAnalysisData.ocean_summary}

---

## 2. 공공 통계 참조 지표
| 지표 항목 | 수치 및 현황 | 데이터 출처 |
| :--- | :--- | :--- |
| 한국 창업 소요 기간 | ${currentAnalysisData.public_stats?.average_startup_days} | World Bank Open Data |
| 3년 평균 기업 생존율 | ${currentAnalysisData.public_stats?.national_survival_rate_3yr} | 중소벤처기업부 공식 통계 |
| 글로벌 비즈니스 환경 점수 | ${currentAnalysisData.public_stats?.global_business_score} | OECD / World Bank 평가 |

---

## 3. 국내외 트렌드 분석
### 🌐 글로벌 최신 트렌드
${currentAnalysisData.trend_analysis?.global_trend}

### 🇰🇷 국내 소비 및 시장 트렌드
${currentAnalysisData.trend_analysis?.domestic_trend}

---

## 4. 초기 투자 비용 및 기회비용 분석
- **예상 소요 자본**: **${currentAnalysisData.cost_analysis?.initial_investment_min} ~ ${currentAnalysisData.cost_analysis?.initial_investment_max}**

### 주요 지출 구성
${(currentAnalysisData.cost_analysis?.major_expenses || []).map(exp => `- ${exp}`).join("\n")}

### ⚖️ 기회비용 및 손익분기점(BEP)
${currentAnalysisData.cost_analysis?.opportunity_cost}

---

## 5. 차별화 전략 및 리스크 관리
### 💡 시장 차별화 핵심 전략
${(currentAnalysisData.strategy?.differentiation || []).map(diff => `1. ${diff}`).join("\n")}

### 🛡️ 사전 리스크 방어 대책
${(currentAnalysisData.strategy?.risk_management || []).map(risk => `- ${risk}`).join("\n")}

---

## 6. 창업 준비 5단계 액션 체크리스트
${(currentAnalysisData.action_checklist || []).map(item => `- [ ] ${item}`).join("\n")}

---

## 7. 청년 창업 멘토 조언
> "${currentAnalysisData.mentor_advice}"
`;

        const blob = new Blob([mdContent], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        const safeFilename = currentAnalysisData.category.replace(/[^a-zA-Z0-9가-힣_-]/g, "_");
        a.href = url;
        a.download = `창업진단리포트_${safeFilename}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
});
