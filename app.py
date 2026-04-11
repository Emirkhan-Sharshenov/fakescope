"""
FakeScope v5 — app.py
Flask backend: 6 languages, BERT + Groq AI, global sources
"""
from flask import Flask, request, jsonify, Response, stream_with_context
import json, hashlib, time
from detector import FakeNewsDetector, NewsSearcher, SUPPORTED_LANGS

app = Flask(__name__, static_folder=None)
detector = FakeNewsDetector()
news_searcher = NewsSearcher()
cache = {}

# ── helpers ───────────────────────────────────────────────────────────────────
def _get_lang(data: dict) -> str:
    lang = (data.get('lang') or 'ru').strip().lower()
    return lang if lang in SUPPORTED_LANGS else 'ru'

# ── routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    with open('index.html', 'r', encoding='utf-8') as f:
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
            groq_active = (det_module.GROQ_API_KEY and
                           det_module.GROQ_API_KEY != "YOUR_GROQ_API_KEY_HERE")
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
    groq_active = (bool(det_module.GROQ_API_KEY) and
                   det_module.GROQ_API_KEY != "YOUR_GROQ_API_KEY_HERE")
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


if __name__ == '__main__':
    import detector as det_module
    bert_ok = detector.bert._pipe is not None
    groq_ok = (bool(det_module.GROQ_API_KEY) and
               det_module.GROQ_API_KEY != "YOUR_GROQ_API_KEY_HERE")
    print("\n" + "="*60)
    print("  FakeScope v5  —  http://localhost:5000")
    print(f"  BERT model:  {'✅ loaded' if bert_ok else '❌ not found (place in ./fakescope_finetuned)'}")
    print(f"  Groq AI:     {'✅ active (' + det_module.GROQ_MODEL + ')' if groq_ok else '❌ not set (add key to detector.py)'}")
    print(f"  Languages:   {', '.join(sorted(SUPPORTED_LANGS))}")
    print(f"  Sources:     {len(det_module.TRUSTED_SOURCES)} trusted domains | {len(det_module.RSS_FEEDS)} RSS feeds")
    print("="*60 + "\n")
    app.run(debug=False, host='0.0.0.0', port=5000)