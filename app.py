"""
FakeScope v5 — app.py
Flask backend: 6 languages, BERT + Groq AI, global sources
"""
from flask import Flask, request, jsonify, Response, stream_with_context
import json, hashlib, time
from datetime import datetime
from detector import FakeNewsDetector, NewsSearcher, SUPPORTED_LANGS
from analytics import AnalyticsManager

app = Flask(__name__, static_folder=None)
detector = FakeNewsDetector()
news_searcher = NewsSearcher()
analytics = AnalyticsManager()
cache = {}

# ── helpers ───────────────────────────────────────────────────────────────────
def _get_lang(data: dict) -> str:
    lang = (data.get('lang') or 'ru').strip().lower()
    return lang if lang in SUPPORTED_LANGS else 'ru'

# ── routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    # Track visitor
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'unknown')
    lang = request.args.get('lang', 'ru')
    analytics.track_visitor(ip, user_agent, lang)
    
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/translations.json')
def translations():
    with open('translations.json', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/analyze', methods=['POST'])
def analyze():
    data  = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No data"}), 400
    title = (data.get('title') or '').strip()
    text  = (data.get('text')  or '').strip()
    url   = (data.get('url')   or '').strip()
    lang  = _get_lang(data)
    if not title and not text:
        return jsonify({"error": "Provide title or text"}), 400
    if not url:
        return jsonify({"error": "Source URL required"}), 400
    key = hashlib.md5(f"{title}{url}{lang}".encode()).hexdigest()
    if key in cache:
        r = dict(cache[key]); r["from_cache"] = True; return jsonify(r)
    try:
        result = detector.analyze(title=title, text=text, url=url, lang=lang)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if "error" not in result and len(cache) < 200:
        cache[key] = result
    return jsonify(result)


@app.route('/analyze_stream', methods=['POST'])
def analyze_stream():
    data  = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    text  = (data.get('text')  or '').strip()
    url   = (data.get('url')   or '').strip()
    lang  = _get_lang(data)
    if not url:
        return jsonify({"error": "URL required"}), 400

    # Step labels per language
    STEPS = {
        "ru": ["Анализ источника...","Анализ текста...","Поиск в мировых СМИ...",
               "Факт-чекинг (Wikipedia)...","BERT нейросеть...","Groq AI (глубокий анализ)..."],
        "en": ["Analysing source...","Analysing text...","Searching global media...",
               "Fact-checking (Wikipedia)...","BERT neural network...","Groq AI (deep analysis)..."],
        "de": ["Quelle analysieren...","Text analysieren...","Globale Medien durchsuchen...",
               "Faktencheck (Wikipedia)...","BERT neuronales Netz...","Groq KI (Tiefenanalyse)..."],
        "fr": ["Analyse de la source...","Analyse du texte...","Recherche médias mondiaux...",
               "Vérification des faits (Wikipedia)...","Réseau neuronal BERT...","Groq IA (analyse approfondie)..."],
        "es": ["Analizando fuente...","Analizando texto...","Buscando en medios globales...",
               "Verificación de hechos (Wikipedia)...","Red neuronal BERT...","Groq IA (análisis profundo)..."],
        "zh": ["分析来源...","分析文本...","搜索全球媒体...","核实事实（维基百科）...","BERT神经网络...","Groq AI（深度分析）..."],
    }
    steps = STEPS.get(lang, STEPS["en"])

    def generate():
        def send(tp, payload):
            msg = {"type": tp}; msg.update(payload)
            return f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

        t0 = time.time()
        try:
            # Step 1: Source
            yield send("progress", {"step":1,"total":6,"label":steps[0]})
            source_r = detector.source_analyzer.analyze(url, lang)
            ai_flag  = " 🤖" if source_r.get("ai_used") else ""
            yield send("step_done", {"step":1,"label":f"{source_r['verdict']}{ai_flag}","data":source_r})

            # Step 2: Text
            yield send("progress", {"step":2,"total":6,"label":steps[1]})
            text_r = detector.text_analyzer.analyze(title, text, lang)
            yield send("step_done", {"step":2,"label":text_r['verdict'],"data":text_r})

            # Step 3: Cross-reference
            yield send("progress", {"step":3,"total":6,"label":steps[2]})
            crossref_r = detector.crossref.analyze(title, text, lang)
            tc, tf = crossref_r['trusted_count'], crossref_r['total_found']
            cr_label = {
                "ru": f"Найдено: {tf} ({tc} надёжных)",
                "en": f"Found: {tf} ({tc} reliable)",
                "de": f"Gefunden: {tf} ({tc} seriös)",
                "fr": f"Trouvé: {tf} ({tc} fiables)",
                "es": f"Encontrado: {tf} ({tc} fiables)",
                "zh": f"找到: {tf} ({tc} 可靠)",
            }.get(lang, f"Found: {tf} ({tc} reliable)")
            yield send("step_done", {"step":3,"label":cr_label,"data":crossref_r})

            # Step 4: Fact-check
            yield send("progress", {"step":4,"total":6,"label":steps[3]})
            fact_r = detector.fact_checker.analyze(title, text, lang)
            fc_label = {
                "ru":"Факт-чекинг завершён","en":"Fact-check complete",
                "de":"Faktencheck abgeschlossen","fr":"Vérification terminée",
                "es":"Verificación completada","zh":"事实核查完成",
            }.get(lang, "Fact-check complete")
            yield send("step_done", {"step":4,"label":fc_label,"data":fact_r})

            # Step 5: BERT
            yield send("progress", {"step":5,"total":6,"label":steps[4]})
            bert_r = detector.bert.analyze(title, text)
            if bert_r.get("available"):
                lbl = bert_r.get("label","?")
                conf = bert_r.get("confidence", bert_r.get("score",50))
                bert_label = f"BERT → {lbl} ({conf}%)"
            else:
                bert_label = {
                    "ru":"BERT не загружен","en":"BERT not loaded",
                    "de":"BERT nicht geladen","fr":"BERT non chargé",
                    "es":"BERT no cargado","zh":"BERT未加载",
                }.get(lang, "BERT not loaded")
            yield send("step_done", {"step":5,"label":bert_label,"data":bert_r})

            # Step 6: Groq deep analysis
            yield send("progress", {"step":6,"total":6,"label":steps[5]})
            import detector as det_module
            groq_r = None
            groq_active = bool(det_module.GROQ_API_KEY)
            if groq_active:
                groq_r = det_module.groq_deep_analyze(title, text, source_r, crossref_r, bert_r, lang)

            if groq_r and groq_r.get("ai_powered"):
                groq_label = f"Groq → {groq_r.get('score',0)}/100 · {groq_r.get('verdict','')[:40]}"
            else:
                groq_label = {
                    "ru":"Groq: ключ не задан","en":"Groq: no key set",
                    "de":"Groq: kein Key","fr":"Groq: pas de clé",
                    "es":"Groq: sin clave","zh":"Groq: 未设置密钥",
                }.get(lang, "Groq: no key set")
            yield send("step_done", {"step":6,"label":groq_label,"data":groq_r or {}})

            # Final
            deep_r = detector.deep_analyzer.analyze(
                title, text, source_r, text_r, crossref_r, fact_r, bert_r, groq_r, lang)
            final = deep_r["score"]
            tl, tc_col, te = detector._trust(final, lang)
            from datetime import datetime
            result = {
                "title":title,"url":url,
                "timestamp":datetime.now().strftime("%d.%m.%Y %H:%M"),
                "analysis_time":round(time.time()-t0,1),
                "final_score":final,"trust_level":tl,"trust_color":tc_col,"trust_emoji":te,
                "explanation":deep_r.get("explanation",""),
                "source":source_r,"text":text_r,"crossref":crossref_r,
                "factcheck":fact_r,"bert":bert_r,"deep":deep_r,
                "hash":hashlib.md5(f"{title}{url}".encode()).hexdigest()[:8],
                "lang":lang,
                "models_used":deep_r.get("model",""),
                "scores_breakdown":deep_r.get("scores_breakdown",{}),
            }
            cache[hashlib.md5(f"{title}{url}{lang}".encode()).hexdigest()] = result
            yield send("result", result)
        except Exception as e:
            yield send("error", {"message": str(e)})

    return Response(stream_with_context(generate()),
                    mimetype='text/event-stream',
                    headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})


@app.route('/trending')
def trending():
    lang = request.args.get('lang', 'ru').lower()
    if lang not in SUPPORTED_LANGS: lang = 'ru'
    try:
        articles = news_searcher.get_trending(lang=lang)
        if articles:
            return jsonify({"articles": articles[:9], "ok": True, "lang": lang})
        return jsonify({"articles": [], "ok": False, "error": "RSS unavailable"})
    except Exception as e:
        return jsonify({"articles": [], "ok": False, "error": str(e)})


@app.route('/set_groq_key', methods=['POST'])
def set_groq_key():
    """Set Groq API key at runtime without restarting."""
    import detector as det_module
    data = request.get_json(silent=True) or {}
    key = (data.get('key') or '').strip()
    if not key:
        return jsonify({"ok": False, "error": "Key is empty"}), 400
    det_module.GROQ_API_KEY = key
    det_module._groq_source_cache.clear()
    det_module._groq_text_cache.clear()
    return jsonify({"ok": True, "message": "✅ Groq API key updated. Caches cleared."})


@app.route('/languages')
def languages():
    return jsonify({
        "supported": list(SUPPORTED_LANGS),
        "labels": {"ru":"Русский","en":"English","de":"Deutsch",
                   "fr":"Français","es":"Español","zh":"中文"}
    })


@app.route('/status')
def status():
    import detector as det_module
    groq_active = bool(det_module.GROQ_API_KEY)
    bert_loaded = detector.bert._pipe is not None
    return jsonify({
        "status": "ok",
        "version": "5.0",
        "cache_size": len(cache),
        "bert_model": "fakescope_finetuned ✅" if bert_loaded else "not loaded ❌",
        "bert_accuracy": "71.2%" if bert_loaded else "N/A",
        "groq_active": groq_active,
        "groq_model": det_module.GROQ_MODEL if groq_active else "inactive",
        "groq_source_cache": len(det_module._groq_source_cache),
        "groq_text_cache": len(det_module._groq_text_cache),
        "trusted_sources": len(det_module.TRUSTED_SOURCES),
        "rss_feeds": len(det_module.RSS_FEEDS),
        "languages": list(SUPPORTED_LANGS),
        "sources": "Global 60+ countries — BBC, Reuters, AP, Al Jazeera, DW, Guardian, NYT, "
                   "France24, РБК, ТАСС, Tengri, 24.kg, Kun.uz…",
    })


@app.route('/feedback', methods=['POST'])
def save_feedback():
    """Save user feedback (thumbs up/down + comment)"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "error": "No data"}), 400
    
    analysis_id = (data.get('analysis_id') or '').strip()
    rating = (data.get('rating') or '').strip().lower()
    comment = (data.get('comment') or '').strip()
    lang = _get_lang(data)
    
    if rating not in ['up', 'down']:
        return jsonify({"ok": False, "error": "Invalid rating"}), 400
    
    ip = request.remote_addr
    success = analytics.save_feedback(ip, analysis_id, rating, comment, lang)
    
    if success:
        return jsonify({
            "ok": True,
            "message": {
                "ru": "✅ Спасибо за отзыв!",
                "en": "✅ Thank you for your feedback!",
                "de": "✅ Danke für Ihr Feedback!",
                "fr": "✅ Merci pour vos commentaires!",
                "es": "✅ ¡Gracias por tu opinión!",
                "zh": "✅ 感谢您的反馈！"
            }.get(lang, "✅ Thank you!")
        })
    else:
        return jsonify({"ok": False, "error": "Failed to save feedback"}), 500


@app.route('/analytics/stats')
def get_analytics():
    """Get public analytics statistics"""
    stats = analytics.get_stats()
    approval_rate = analytics.get_approval_rate()
    
    return jsonify({
        "total_visitors": stats['total_visitors'],
        "total_feedback": stats['total_feedback'],
        "thumbs_up": stats['thumbs_up'],
        "thumbs_down": stats['thumbs_down'],
        "approval_rate": approval_rate,
        "languages": stats['languages'],
        "recent_comments": [
            {
                "rating": f.get('rating'),
                "comment": f.get('comment', ''),
                "language": f.get('language')
            }
            for f in stats['recent_feedback']
            if f.get('comment')  # Only show feedback with comments
        ][:10]  # Last 10 with comments
    })


@app.route('/analytics/detailed')
def get_detailed_analytics():
    """Get detailed analytics metrics for dashboard"""
    detailed = analytics.get_detailed_metrics()
    return jsonify(detailed)


@app.route('/analytics/dashboard')
def analytics_dashboard():
    """Serve analytics dashboard HTML page"""
    dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FakeScope Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #333; margin: 0; }
        .header p { color: #666; margin: 10px 0 0 0; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-card h3 { margin: 0 0 10px 0; color: #333; font-size: 14px; text-transform: uppercase; }
        .stat-value { font-size: 32px; font-weight: bold; color: #007acc; margin: 0; }
        .stat-label { color: #666; font-size: 12px; margin: 5px 0 0 0; }
        .charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .chart-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .chart-card h3 { margin: 0 0 20px 0; color: #333; }
        .chart-container { position: relative; height: 300px; }
        .verification { background: #e8f5e8; border: 1px solid #4caf50; padding: 15px; border-radius: 8px; margin-top: 20px; }
        .verification h4 { margin: 0 0 10px 0; color: #2e7d32; }
        .verification ul { margin: 0; padding-left: 20px; color: #2e7d32; }
        .loading { text-align: center; padding: 50px; color: #666; }
        .error { color: #d32f2f; text-align: center; padding: 20px; }
        
        /* Responsive Design */
        @media(max-width:768px){
            .container { padding: 10px; }
            .header { margin-bottom: 20px; }
            .header h1 { font-size: 24px; }
            .header p { font-size: 14px; }
            .stats-grid { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
            .stat-card { padding: 15px; }
            .stat-value { font-size: 24px; }
            .charts-grid { grid-template-columns: 1fr; gap: 15px; }
            .chart-card { padding: 15px; }
            .verification { padding: 12px; margin-top: 15px; }
            .verification ul { padding-left: 15px; font-size: 14px; }
        }
        
        @media(max-width:480px){
            .container { padding: 5px; }
            .header { margin-bottom: 15px; }
            .header h1 { font-size: 20px; }
            .header p { font-size: 13px; }
            .stats-grid { grid-template-columns: 1fr; gap: 10px; }
            .stat-card { padding: 12px; }
            .stat-value { font-size: 20px; }
            .stat-label { font-size: 11px; }
            .charts-grid { gap: 10px; }
            .chart-card { padding: 12px; }
            .chart-container { height: 250px; }
            .verification { padding: 10px; margin-top: 12px; border-radius: 6px; }
            .verification h4 { font-size: 14px; margin-bottom: 8px; }
            .verification ul { padding-left: 12px; font-size: 13px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 FakeScope Analytics Dashboard</h1>
            <p>Real-time analytics and verification of user engagement</p>
        </div>
        
        <div id="loading" class="loading">Loading analytics data...</div>
        <div id="error" class="error" style="display: none;"></div>
        
        <div id="dashboard" style="display: none;">
            <div class="stats-grid" id="stats-grid">
                <!-- Stats cards will be inserted here -->
            </div>
            
            <div class="charts-grid">
                <div class="chart-card">
                    <h3>📈 Daily Visits (Last 30 Days)</h3>
                    <div class="chart-container">
                        <canvas id="dailyVisitsChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h3>🕐 Hourly Distribution</h3>
                    <div class="chart-container">
                        <canvas id="hourlyChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h3>👍👎 Feedback Trends</h3>
                    <div class="chart-container">
                        <canvas id="feedbackChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h3>🌍 Language Distribution</h3>
                    <div class="chart-container">
                        <canvas id="languageChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="verification">
                <h4>✅ Data Verification</h4>
                <ul id="verification-list">
                    <!-- Verification items will be inserted here -->
                </ul>
            </div>
        </div>
    </div>

    <script>
        let statsData = {};
        let detailedData = {};
        let verificationData = {};

        async function loadData() {
            try {
                const [statsRes, detailedRes, verifyRes] = await Promise.all([
                    fetch('/analytics/stats'),
                    fetch('/analytics/detailed'),
                    fetch('/analytics/verify')
                ]);

                statsData = await statsRes.json();
                detailedData = await detailedRes.json();
                verificationData = await verifyRes.json();

                renderDashboard();
            } catch (error) {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('error').style.display = 'block';
                document.getElementById('error').textContent = 'Error loading analytics data: ' + error.message;
            }
        }

        function renderDashboard() {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('dashboard').style.display = 'block';
            
            renderStatsCards();
            renderCharts();
            renderVerification();
        }

        function renderStatsCards() {
            const grid = document.getElementById('stats-grid');
            const cards = [
                { title: 'Total Visitors', value: statsData.total_visitors, label: 'unique users' },
                { title: 'Total Feedback', value: statsData.total_feedback, label: 'user reviews' },
                { title: 'Approval Rate', value: statsData.approval_rate ? statsData.approval_rate + '%' : 'N/A', label: 'positive feedback' },
                { title: 'Languages', value: Object.keys(statsData.languages).length, label: 'supported' },
                { title: 'Unique Browsers', value: verificationData.verification?.user_agent_diversity || 0, label: 'different user agents' },
                { title: 'Data Storage', value: verificationData.verification?.data_storage || 'Unknown', label: 'storage method' }
            ];

            grid.innerHTML = cards.map(card => `
                <div class="stat-card">
                    <h3>${card.title}</h3>
                    <div class="stat-value">${card.value}</div>
                    <div class="stat-label">${card.label}</div>
                </div>
            `).join('');
        }

        function renderCharts() {
            // Daily Visits Chart
            const dailyCtx = document.getElementById('dailyVisitsChart').getContext('2d');
            new Chart(dailyCtx, {
                type: 'line',
                data: {
                    labels: Object.keys(detailedData.daily_visits || {}),
                    datasets: [{
                        label: 'Visits',
                        data: Object.values(detailedData.daily_visits || {}),
                        borderColor: '#007acc',
                        backgroundColor: 'rgba(0, 122, 204, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });

            // Hourly Distribution Chart
            const hourlyCtx = document.getElementById('hourlyChart').getContext('2d');
            new Chart(hourlyCtx, {
                type: 'bar',
                data: {
                    labels: Object.keys(detailedData.hourly_distribution || {}).map(h => h + ':00'),
                    datasets: [{
                        label: 'Visits',
                        data: Object.values(detailedData.hourly_distribution || {}),
                        backgroundColor: '#4caf50'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });

            // Feedback Trends Chart
            const feedbackCtx = document.getElementById('feedbackChart').getContext('2d');
            const feedbackLabels = Object.keys(detailedData.feedback_trends || {});
            const upData = feedbackLabels.map(date => detailedData.feedback_trends[date]?.up || 0);
            const downData = feedbackLabels.map(date => detailedData.feedback_trends[date]?.down || 0);
            
            new Chart(feedbackCtx, {
                type: 'line',
                data: {
                    labels: feedbackLabels,
                    datasets: [
                        {
                            label: '👍 Positive',
                            data: upData,
                            borderColor: '#4caf50',
                            backgroundColor: 'rgba(76, 175, 80, 0.1)',
                            tension: 0.4
                        },
                        {
                            label: '👎 Negative',
                            data: downData,
                            borderColor: '#f44336',
                            backgroundColor: 'rgba(244, 67, 54, 0.1)',
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });

            // Language Distribution Chart
            const langCtx = document.getElementById('languageChart').getContext('2d');
            const langData = statsData.languages || {};
            new Chart(langCtx, {
                type: 'pie',
                data: {
                    labels: Object.keys(langData),
                    datasets: [{
                        data: Object.values(langData),
                        backgroundColor: [
                            '#007acc', '#4caf50', '#ff9800', '#f44336', '#9c27b0', '#00bcd4'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }

        function renderVerification() {
            const list = document.getElementById('verification-list');
            const verify = verificationData.verification || {};
            
            const items = [
                `Total unique visitors: ${verify.total_unique_visitors || 0}`,
                `Unique feedback givers: ${verify.total_unique_feedback_givers || 0}`,
                `User agent diversity: ${verify.user_agent_diversity || 0} different browsers`,
                `IP hashing: ${verify.ip_hashing || 'SHA256 for privacy'}`,
                `External tracking: ${verify.no_external_tracking ? 'None' : 'Present'}`,
                `Data storage: ${verify.data_storage || 'Unknown'}`,
                `Last updated: ${verificationData.last_updated || 'Unknown'}`
            ];

            list.innerHTML = items.map(item => `<li>${item}</li>`).join('');
        }

        // Load data on page load
        loadData();
        
        // Refresh every 5 minutes
        setInterval(loadData, 300000);
    </script>
</body>
</html>
    """
    return dashboard_html


if __name__ == '__main__':
    import detector as det_module
    bert_ok = detector.bert._pipe is not None
    groq_ok = bool(det_module.GROQ_API_KEY)
    print("\n" + "="*60)
    print("  FakeScope v5  —  http://localhost:5000")
    print(f"  BERT model:  {'✅ loaded' if bert_ok else '❌ not found (place in ./fakescope_finetuned)'}")
    print(f"  Groq AI:     {'✅ active (' + det_module.GROQ_MODEL + ')' if groq_ok else '❌ not set (add key to detector.py)'}")
    print(f"  Languages:   {', '.join(sorted(SUPPORTED_LANGS))}")
    print(f"  Sources:     {len(det_module.TRUSTED_SOURCES)} trusted domains | {len(det_module.RSS_FEEDS)} RSS feeds")
    print("="*60 + "\n")
    app.run(debug=False, host='0.0.0.0', port=5000)
