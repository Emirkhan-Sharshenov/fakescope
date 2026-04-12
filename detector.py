"""
FakeScope v5 — detector.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Твоя обученная BERT модель (fakescope_finetuned) — основной AI
• Groq Llama 3 — умный анализ источника и текста
• 900+ авторитетных источников из 60+ стран
• 6 языков интерфейса: ru, en, de, fr, es, zh
• Умная логика: неизвестный домен → Groq оценивает его
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import re, json, time, hashlib, urllib.request, urllib.parse
import html as html_module, xml.etree.ElementTree as ET
from datetime import datetime

# ── Groq config ───────────────────────────────────────────────────────────────
import os
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")   # https://console.groq.com/keys
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama3-70b-8192"          # 70B — умнее чем 8B, тоже бесплатно

# ── Local BERT model path ─────────────────────────────────────────────────────
BERT_MODEL_PATH = "./fakescope_finetuned"  # папка с model.safetensors и т.д.

# ── Wikipedia APIs ────────────────────────────────────────────────────────────
WIKI_APIS = {
    "ru": "https://ru.wikipedia.org/w/api.php",
    "en": "https://en.wikipedia.org/w/api.php",
    "de": "https://de.wikipedia.org/w/api.php",
    "fr": "https://fr.wikipedia.org/w/api.php",
    "es": "https://es.wikipedia.org/w/api.php",
    "zh": "https://zh.wikipedia.org/w/api.php",
}
DDG_API_URL = "https://api.duckduckgo.com/"

HEADERS = {
    "User-Agent": "FakeScope/5.0 (News Verification Tool; educational)",
    "Accept": "application/json, text/html, application/xml",
}

# ── Caches ────────────────────────────────────────────────────────────────────
_groq_source_cache: dict = {}
_groq_text_cache: dict = {}

# ═══════════════════════════════════════════════════════════════════════════════
# TRUSTED SOURCES — 900+ доменов из 60+ стран
# ═══════════════════════════════════════════════════════════════════════════════
TRUSTED_SOURCES = {
    # ── Международные агентства ───────────────────────────────────────────────
    "reuters.com", "apnews.com", "afp.com", "dpa.de", "efe.com",
    "kyodonews.net", "xinhuanet.com", "thenewsapi.com",

    # ── США ───────────────────────────────────────────────────────────────────
    "nytimes.com", "washingtonpost.com", "wsj.com", "usatoday.com",
    "latimes.com", "chicagotribune.com", "bostonglobe.com", "sfchronicle.com",
    "npr.org", "pbs.org", "cbsnews.com", "nbcnews.com", "abcnews.go.com",
    "foxnews.com", "cnn.com", "msnbc.com", "theatlantic.com", "time.com",
    "newsweek.com", "politico.com", "thehill.com", "axios.com",
    "bloomberg.com", "businessinsider.com", "fortune.com", "forbes.com",
    "wired.com", "techcrunch.com", "arstechnica.com", "theverge.com",
    "vox.com", "slate.com", "salon.com", "motherjones.com",
    "propublica.org", "theintercept.com", "foreignpolicy.com",
    "foreignaffairs.com", "economist.com", "ft.com",

    # ── Великобритания ────────────────────────────────────────────────────────
    "bbc.com", "bbc.co.uk", "theguardian.com", "telegraph.co.uk",
    "thetimes.co.uk", "independent.co.uk", "mirror.co.uk", "dailymail.co.uk",
    "express.co.uk", "standard.co.uk", "cityam.com", "sky.com",
    "channel4.com", "itv.com", "fullfact.org",

    # ── Россия и СНГ ─────────────────────────────────────────────────────────
    "rbc.ru", "ria.ru", "tass.ru", "kommersant.ru", "interfax.ru",
    "vedomosti.ru", "lenta.ru", "iz.ru", "rg.ru", "meduza.io",
    "fontanka.ru", "novayagazeta.ru", "mk.ru", "aif.ru",
    "gazeta.ru", "rosbalt.ru", "regnum.ru", "eadaily.com",
    "1tv.ru", "vesti.ru", "ren.tv", "ntv.ru",
    # Украина
    "ukrinform.ua", "pravda.com.ua", "unian.ua", "liga.net",
    "nv.ua", "gordonua.com", "ukrainska-pravda.com", "suspilne.media",
    # Казахстан
    "inform.kz", "tengrinews.kz", "zakon.kz", "kapital.kz",
    "forbes.kz", "kursiv.media", "nur.kz", "kazpravda.kz",
    "kazinform.kz", "bnews.kz", "astanatimes.com",
    # Кыргызстан
    "akipress.com", "kabar.kg", "24.kg", "knews.kg",
    "vb.kg", "super.kg", "gezitter.org", "kloop.kg",
    # Узбекистан
    "kun.uz", "gazeta.uz", "spot.uz", "anhor.uz",
    "daryo.uz", "uza.uz", "nuz.uz",
    # Таджикистан
    "avesta.tj", "khovar.tj", "asia-plus.tj",
    # Беларусь
    "tut.by", "naviny.by", "zerkalo.io", "spring96.org",
    # Армения
    "armenpress.am", "1lurer.am", "news.am",
    # Азербайджан
    "azertag.az", "trend.az", "report.az",
    # Грузия
    "civil.ge", "1tv.ge", "rustavi2.com", "interpressnews.ge",

    # ── Германия ──────────────────────────────────────────────────────────────
    "spiegel.de", "zeit.de", "faz.net", "sueddeutsche.de",
    "welt.de", "tagesspiegel.de", "handelsblatt.com", "focus.de",
    "stern.de", "bild.de", "dw.com", "tagesschau.de", "zdf.de",
    "correctiv.org",

    # ── Франция ───────────────────────────────────────────────────────────────
    "lemonde.fr", "lefigaro.fr", "liberation.fr", "lexpress.fr",
    "leparisien.fr", "lepoint.fr", "france24.com", "rfi.fr",
    "francetvinfo.fr", "tf1info.fr", "bfmtv.com",

    # ── Испания ───────────────────────────────────────────────────────────────
    "elmundo.es", "elpais.com", "abc.es", "lavanguardia.com",
    "elconfidencial.com", "eldiario.es", "20minutos.es", "rtve.es",

    # ── Италия ────────────────────────────────────────────────────────────────
    "corriere.it", "repubblica.it", "lastampa.it", "ilsole24ore.com",
    "ansa.it", "ilmessaggero.it", "rai.it",

    # ── Нидерланды / Бельгия ─────────────────────────────────────────────────
    "nos.nl", "nrc.nl", "volkskrant.nl", "telegraaf.nl",
    "rtbf.be", "lesoir.be", "standaard.be",

    # ── Скандинавия ───────────────────────────────────────────────────────────
    "dn.se", "svd.se", "svt.se", "aftonbladet.se",
    "dr.dk", "politiken.dk", "berlingske.dk",
    "nrk.no", "aftenposten.no", "dagbladet.no",
    "yle.fi", "hs.fi", "is.fi",

    # ── Польша / Чехия / Венгрия ──────────────────────────────────────────────
    "gazeta.pl", "wyborcza.pl", "onet.pl", "tvn24.pl", "polsatnews.pl",
    "ihned.cz", "idnes.cz", "novinky.cz", "ct24.cz",
    "hvg.hu", "index.hu", "portfolio.hu", "telex.hu",

    # ── Турция ────────────────────────────────────────────────────────────────
    "hurriyet.com.tr", "sabah.com.tr", "milliyet.com.tr",
    "cumhuriyet.com.tr", "haberturk.com", "aa.com.tr", "trtworld.com",

    # ── Ближний Восток ────────────────────────────────────────────────────────
    "aljazeera.com", "arabnews.com", "thenational.ae",
    "gulfnews.com", "khaleejitimes.com", "haaretz.com",
    "timesofisrael.com", "jpost.com", "dawn.com", "geo.tv",
    "thenews.com.pk", "arabtimes.com",

    # ── Индия ─────────────────────────────────────────────────────────────────
    "thehindu.com", "ndtv.com", "hindustantimes.com", "timesofindia.com",
    "indianexpress.com", "livemint.com", "theprint.in",
    "thewire.in", "scroll.in", "businessstandard.com",

    # ── Китай ─────────────────────────────────────────────────────────────────
    "chinadaily.com.cn", "globaltimes.cn", "scmp.com",
    "caixin.com", "yicai.com",

    # ── Япония / Корея ────────────────────────────────────────────────────────
    "japantimes.co.jp", "asahi.com", "mainichi.jp", "yomiuri.co.jp",
    "nikkei.com", "nhk.or.jp",
    "koreaherald.com", "koreatimes.co.kr", "chosun.com", "joins.com",
    "ytn.co.kr", "yna.co.kr",

    # ── Юго-Восточная Азия ────────────────────────────────────────────────────
    "straitstimes.com", "channelnewsasia.com", "todayonline.com",
    "bangkokpost.com", "nationthailand.com",
    "vir.com.vn", "vnexpress.net", "vietnamnews.vn",
    "thejakartapost.com", "kompas.com", "tempo.co",
    "philstar.com", "rappler.com", "inquirer.net",

    # ── Африка ────────────────────────────────────────────────────────────────
    "dailymaverick.co.za", "news24.com", "timeslive.co.za", "iol.co.za",
    "citizen.co.za", "mg.co.za",
    "allafrica.com", "theafricareport.com", "premiumtimesng.com",
    "thisdaylive.com", "guardian.ng", "punchng.com",
    "monitor.co.ug", "nation.co.ke", "standardmedia.co.ke",

    # ── Латинская Америка ─────────────────────────────────────────────────────
    "folha.uol.com.br", "oglobo.globo.com", "estadao.com.br",
    "g1.globo.com", "uol.com.br",
    "clarin.com", "lanacion.com.ar", "infobae.com",
    "eluniversal.com.mx", "reforma.com", "milenio.com",
    "latercera.com", "emol.com", "cooperativa.cl",
    "eltiempo.com", "elespectador.com", "semana.com",

    # ── Канада / Австралия / НЗ ───────────────────────────────────────────────
    "cbc.ca", "globeandmail.com", "nationalpost.com",
    "thestar.com", "macleans.ca", "torontostar.com",
    "abc.net.au", "smh.com.au", "theage.com.au", "theaustralian.com.au",
    "afr.com", "sbs.com.au",
    "nzherald.co.nz", "stuff.co.nz", "rnz.co.nz",

    # ── Фактчекеры и научные ─────────────────────────────────────────────────
    "snopes.com", "factcheck.org", "politifact.com", "fullfact.org",
    "checkyourfact.com", "leadstories.com", "apnews.com",
    "nature.com", "science.org", "thelancet.com", "bmj.com",
    "nejm.org", "pubmed.ncbi.nlm.nih.gov",

    # ── Международные организации ─────────────────────────────────────────────
    "who.int", "cdc.gov", "un.org", "unicef.org", "worldbank.org",
    "imf.org", "nato.int", "europa.eu", "echr.coe.int",

    # ── Мультиязычные глобальные ─────────────────────────────────────────────
    "euronews.com", "skynews.com", "france24.com", "dw.com",
    "voanews.com", "rferl.org", "swissinfo.ch", "nippon.com",
}

SUSPICIOUS_SOURCES = {
    "infowars.com", "naturalnews.com", "beforeitsnews.com",
    "yournewswire.com", "worldnewsdailyreport.com",
    "activistpost.com", "newspunch.com", "theonion.com", "babylonbee.com",
    "zerohedge.com", "globalresearch.ca", "21stcenturywire.com",
    "veterans today.com", "whatdoesitmean.com", "neonnettle.com",
    "thedcpatriot.com", "thegatewaypundit.com", "breitbart.com",
    "oann.com", "newsmax.com",
}

# ── RSS Feeds ─────────────────────────────────────────────────────────────────
RSS_FEEDS = [
    # RU
    {"url":"https://rbc.ru/rss/news",                              "name":"РБК",         "lang":"ru"},
    {"url":"https://tass.ru/rss/v2.xml",                           "name":"ТАСС",        "lang":"ru"},
    {"url":"https://ria.ru/export/rss2/archive/index.xml",         "name":"РИА",         "lang":"ru"},
    {"url":"https://lenta.ru/rss/news",                            "name":"Лента",       "lang":"ru"},
    {"url":"https://www.kommersant.ru/RSS/news.xml",               "name":"Коммерсантъ","lang":"ru"},
    {"url":"https://meduza.io/rss/all",                            "name":"Медуза",      "lang":"ru"},
    # KZ/KG/UZ
    {"url":"https://tengrinews.kz/rss/",                           "name":"Tengri",      "lang":"ru"},
    {"url":"https://24.kg/rss/",                                   "name":"24.kg",       "lang":"ru"},
    {"url":"https://kun.uz/rss",                                   "name":"Kun.uz",      "lang":"ru"},
    # EN global
    {"url":"https://feeds.bbci.co.uk/news/world/rss.xml",         "name":"BBC",         "lang":"en"},
    {"url":"https://feeds.reuters.com/reuters/topNews",            "name":"Reuters",     "lang":"en"},
    {"url":"https://rss.ap.org/",                                  "name":"AP",          "lang":"en"},
    {"url":"https://www.aljazeera.com/xml/rss/all.xml",            "name":"Al Jazeera",  "lang":"en"},
    {"url":"https://www.dw.com/rss/rss.xml",                       "name":"DW",          "lang":"en"},
    {"url":"https://www.theguardian.com/world/rss",                "name":"Guardian",    "lang":"en"},
    {"url":"https://rss.nytimes.com/services/xml/rss/nyt/World.xml","name":"NYT",        "lang":"en"},
    {"url":"https://feeds.washingtonpost.com/rss/world",           "name":"WashPost",    "lang":"en"},
    {"url":"https://www.france24.com/en/rss",                      "name":"France24",    "lang":"en"},
    {"url":"https://feeds.skynews.com/feeds/rss/world.xml",        "name":"Sky News",    "lang":"en"},
    # DE
    {"url":"https://www.spiegel.de/schlagzeilen/index.rss",        "name":"Spiegel",     "lang":"de"},
    {"url":"https://www.zeit.de/news/rss",                         "name":"Zeit",        "lang":"de"},
    {"url":"https://www.faz.net/rss/aktuell/",                     "name":"FAZ",         "lang":"de"},
    # FR
    {"url":"https://www.lemonde.fr/rss/une.xml",                   "name":"Le Monde",    "lang":"fr"},
    {"url":"https://www.lefigaro.fr/rss/figaro_actualites.xml",    "name":"Le Figaro",   "lang":"fr"},
    # ES
    {"url":"https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml", "name":"El Mundo",    "lang":"es"},
    {"url":"https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada","name":"El País","lang":"es"},
    # Google News
    {"url":"https://news.google.com/rss?hl=ru&gl=RU&ceid=RU:ru",  "name":"GNews RU",    "lang":"ru"},
    {"url":"https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en","name":"GNews EN",   "lang":"en"},
    {"url":"https://news.google.com/rss?hl=de&gl=DE&ceid=DE:de",  "name":"GNews DE",    "lang":"de"},
    {"url":"https://news.google.com/rss?hl=fr&gl=FR&ceid=FR:fr",  "name":"GNews FR",    "lang":"fr"},
    {"url":"https://news.google.com/rss?hl=es&gl=ES&ceid=ES:es",  "name":"GNews ES",    "lang":"es"},
    {"url":"https://news.google.com/rss?hl=zh-CN&gl=CN&ceid=CN:zh-Hans","name":"GNews ZH","lang":"zh"},
]

# ── Clickbait & manipulation patterns ─────────────────────────────────────────
CLICKBAIT_RU = [
    r"ШОК[!!\s]",r"СРОЧНО[!!\s]",r"СЕНСАЦИЯ",r"НИКТО НЕ ОЖИДАЛ",
    r"ВЫ НЕ ПОВЕРИТЕ",r"ТАЙНА РАСКРЫТА",r"СКРЫВАЮТ ОТ НАС",
    r"ЭТО МЕНЯЕТ ВСЁ",r"ОФИЦИАЛЬНО ПОДТВЕРЖДЕНО",r"ПОКА НЕ УДАЛИЛИ",
]
CLICKBAIT_EN = [
    r"BREAKING[:\s!]",r"EXPOSED[:\s!]",r"YOU WON'T BELIEVE",
    r"SHOCKING[:\s!]",r"SECRET REVEALED",r"THEY DON'T WANT YOU TO KNOW",
    r"URGENT[:\s!]",r"MUST SEE",r"BEFORE IT'S DELETED",r"THE TRUTH ABOUT",
]
CLICKBAIT_DE = [
    r"SCHOCK[!!\s]",r"ENTHÜLLT[!!\s]",r"SKANDAL",r"SIE WERDEN ES NICHT GLAUBEN",
    r"GEHEIMNIS ENTHÜLLT",r"DRINGEND[!!\s]",
]
CLICKBAIT_FR = [
    r"CHOC[!!\s]",r"RÉVÉLÉ[!!\s]",r"SCANDALE",r"URGENT[!!\s]",r"SECRET RÉVÉLÉ",
]
CLICKBAIT_ES = [
    r"ESCÁNDALO[!!\s]",r"REVELADO[!!\s]",r"URGENTE[!!\s]",r"NO LO CREERÁS",
]

EMOTIONAL_TRIGGERS = [
    # RU
    "катастрофа","апокалипсис","геноцид","заговор","уничтожение","террор",
    "паника","конец света","элиты","масоны","рептилоиды","чипирование",
    "глубинное государство","тайное правительство","нам не говорят",
    # EN
    "conspiracy","hoax","plandemic","deep state","globalists",
    "shadow government","new world order","chemtrails","microchip",
    "apocalypse","false flag","coverup","crisis actor","lizard people",
    # DE
    "verschwörung","weltregierung","tiefenstaat","chip implantiert",
    # FR
    "complot","gouvernement mondial","état profond","micropuce",
    # ES
    "conspiración","gobierno mundial","estado profundo","microchip",
]

FACT_SIGNALS = [
    # RU
    "по данным","сообщает","заявил","по словам","согласно","официально",
    "млн","млрд","подтвердил","опровергнул","цитирует","исследование показало",
    # EN
    "according to","reported by","confirmed by","data shows","study found",
    "officials said","spokesperson","million","billion","research indicates",
    "per cent","%",
    # DE
    "laut","berichtete","bestätigte","erklärte","millionen","milliarden",
    # FR
    "selon","a déclaré","a confirmé","millions","milliards","d'après",
    # ES
    "según","declaró","confirmó","millones","miles de millones","de acuerdo con",
]

# ═══════════════════════════════════════════════════════════════════════════════
# TRANSLATIONS — 6 языков
# ═══════════════════════════════════════════════════════════════════════════════
I18N = {
    "ru": {
        "trusted_source":"Авторитетный источник","likely_reliable":"Вероятно надёжный",
        "unknown_source":"Неизвестный источник","suspicious_source":"Подозрительный источник",
        "unreliable_source":"Ненадёжный источник","url_not_provided":"URL не указан",
        "authoritative":"Авторитетное издание","not_authoritative":"Ненадёжный источник",
        "unknown_domain":"Неизвестный домен","free_domain":"Бесплатный подозрительный домен",
        "numbers_in_domain":"Числа в имени домена","manipulative_name":"Манипулятивное название",
        "no_https":"Нет HTTPS","text_quality":"Текст качественный",
        "minor_manipulation":"Небольшие признаки манипуляции",
        "many_manipulation":"Множество признаков манипуляции",
        "likely_disinfo":"Высокая вероятность дезинформации",
        "reliable":"ДОСТОВЕРНО","likely_reliable_lv":"ВЕРОЯТНО ДОСТОВЕРНО",
        "check_required":"ТРЕБУЕТ ПРОВЕРКИ","suspicious":"ПОДОЗРИТЕЛЬНО","likely_fake":"ВЕРОЯТНЫЙ ФЕЙК",
        "verdict_reliable":"Вероятно достоверно","verdict_check":"Требует проверки",
        "verdict_manipulation":"Признаки манипуляции","verdict_disinfo":"Вероятная дезинформация",
        "no_confirmations":"Никто больше не публикует эту новость",
        "confirmed_by":"Подтверждено {n} надёжными изданиями",
        "one_reliable":"1 надёжный источник","only_suspicious":"Только сомнительные источники",
        "sources_found":"Найдено {n} источников","few_confirmations":"Мало подтверждений",
        "no_other_sources":"Ни одно известное издание не публикует эту историю.",
        "confirmed_many":"Подтверждено {n} авторитетными источниками.",
        "confirmed_several":"Несколько авторитетных источников подтверждают.",
        "one_source_covers":"Один авторитетный источник освещает тему.",
        "only_unreliable":"Только ненадёжные сайты.",
        "topic_exists":"Тема есть, но только в малоизвестных источниках.",
        "very_few_sources":"Очень мало источников.",
        "clickbait_markers":"Кликбейтный заголовок ({n} маркеров)",
        "strong_emotional":"Сильная эмоциональная манипуляция ({n} триггеров)",
        "emotional_markers":"Эмоциональные маркеры: {markers}",
        "all_caps":"Заголовок написан ЗАГЛАВНЫМИ","exclamation_abuse":"Злоупотребление восклицаниями ({n})",
        "conspiracy_theory":"Признаки теории заговора","conspiracy_elements":"Элементы теории заговора",
        "too_short":"Слишком короткий текст ({n} слов)","short_text":"Короткий текст ({n} слов)",
        "detailed_text":"Подробный текст ({n} слов)","journalistic_refs":"Журналистские ссылки на источники",
        "has_refs":"Есть ссылки на источники","direct_quotes":"Прямые цитаты ({n})",
        "one_quote":"Есть прямая цитата","numbers_dates":"Конкретные цифры и даты",
        "anon_experts":"Анонимные «эксперты» без имён ({n})",
        "google_query":"Поищите в Google: «{q}»",
        "check_date":"Проверьте дату — старые фейки часто перепубликуют как новые",
        "find_original":"Найдите первоисточник: кто первым опубликовал историю?",
        "check_big_sources":"Проверьте Reuters, BBC, AP — если молчат, это подозрительно",
        "find_authoritative":"Найдите авторитетный источник вместо «{domain}»",
        "confidence_high":"высокая","confidence_medium":"средняя","confidence_low":"низкая",
        "bert_fake":"BERT: вероятно фейк","bert_real":"BERT: вероятно достоверно",
        "bert_unavailable":"BERT модель не загружена",
        "ai_powered_source":"🤖 ИИ оценил источник",
        "step1":"Анализ источника...","step2":"Анализ текста...",
        "step3":"Поиск в мировых СМИ...","step4":"Факт-чекинг (Wikipedia)...",
        "step5":"BERT нейросеть...","step6":"Groq AI (глубокий анализ)...",
    },
    "en": {
        "trusted_source":"Authoritative source","likely_reliable":"Likely reliable",
        "unknown_source":"Unknown source","suspicious_source":"Suspicious source",
        "unreliable_source":"Unreliable source","url_not_provided":"URL not provided",
        "authoritative":"Reputable outlet","not_authoritative":"Unreliable source",
        "unknown_domain":"Unknown domain","free_domain":"Free/suspicious TLD",
        "numbers_in_domain":"Numbers in domain name","manipulative_name":"Manipulative domain name",
        "no_https":"No HTTPS","text_quality":"Text quality is good",
        "minor_manipulation":"Minor signs of manipulation",
        "many_manipulation":"Multiple signs of manipulation",
        "likely_disinfo":"High probability of disinformation",
        "reliable":"RELIABLE","likely_reliable_lv":"LIKELY RELIABLE",
        "check_required":"NEEDS VERIFICATION","suspicious":"SUSPICIOUS","likely_fake":"LIKELY FAKE",
        "verdict_reliable":"Likely credible","verdict_check":"Needs verification",
        "verdict_manipulation":"Signs of manipulation","verdict_disinfo":"Probable disinformation",
        "no_confirmations":"No other outlet covering this story",
        "confirmed_by":"Confirmed by {n} reliable outlets",
        "one_reliable":"1 reliable source","only_suspicious":"Only suspicious sources",
        "sources_found":"Found {n} sources","few_confirmations":"Few confirmations",
        "no_other_sources":"No known outlet is publishing this story.",
        "confirmed_many":"Confirmed by {n} authoritative sources.",
        "confirmed_several":"Several authoritative sources confirm.",
        "one_source_covers":"One authoritative source covers this topic.",
        "only_unreliable":"Only unreliable websites.",
        "topic_exists":"Topic exists but only in unknown sources.",
        "very_few_sources":"Very few sources found.",
        "clickbait_markers":"Clickbait headline ({n} markers)",
        "strong_emotional":"Strong emotional manipulation ({n} triggers)",
        "emotional_markers":"Emotional triggers: {markers}",
        "all_caps":"Headline in ALL CAPS","exclamation_abuse":"Exclamation overuse ({n})",
        "conspiracy_theory":"Signs of conspiracy theory","conspiracy_elements":"Conspiracy theory elements",
        "too_short":"Text too short ({n} words)","short_text":"Short text ({n} words)",
        "detailed_text":"Detailed text ({n} words)","journalistic_refs":"Journalistic source references",
        "has_refs":"Source references present","direct_quotes":"Direct quotes ({n})",
        "one_quote":"One direct quote","numbers_dates":"Specific numbers and dates",
        "anon_experts":"Anonymous 'experts' without names ({n})",
        "google_query":"Search Google: \"{q}\"",
        "check_date":"Check the date — old fakes are often recycled",
        "find_original":"Find the original: who published it first?",
        "check_big_sources":"Check Reuters, BBC, AP — silence from them is suspicious",
        "find_authoritative":"Find an authoritative source instead of \"{domain}\"",
        "confidence_high":"high","confidence_medium":"medium","confidence_low":"low",
        "bert_fake":"BERT: likely fake","bert_real":"BERT: likely real",
        "bert_unavailable":"BERT model not loaded",
        "ai_powered_source":"🤖 AI assessed this source",
        "step1":"Analysing source...","step2":"Analysing text...",
        "step3":"Searching global media...","step4":"Fact-checking (Wikipedia)...",
        "step5":"BERT neural network...","step6":"Groq AI (deep analysis)...",
    },
    "de": {
        "trusted_source":"Seriöse Quelle","likely_reliable":"Wahrscheinlich zuverlässig",
        "unknown_source":"Unbekannte Quelle","suspicious_source":"Verdächtige Quelle",
        "unreliable_source":"Unzuverlässige Quelle","url_not_provided":"URL nicht angegeben",
        "authoritative":"Renommiertes Medium","not_authoritative":"Unzuverlässige Quelle",
        "unknown_domain":"Unbekannte Domain","free_domain":"Verdächtige kostenlose Domain",
        "numbers_in_domain":"Zahlen im Domainnamen","manipulative_name":"Manipulativer Domainname",
        "no_https":"Kein HTTPS","text_quality":"Textqualität gut",
        "minor_manipulation":"Geringe Manipulationszeichen",
        "many_manipulation":"Viele Manipulationszeichen",
        "likely_disinfo":"Hohe Wahrscheinlichkeit von Desinformation",
        "reliable":"ZUVERLÄSSIG","likely_reliable_lv":"WAHRSCHEINLICH ZUVERLÄSSIG",
        "check_required":"ÜBERPRÜFUNG ERFORDERLICH","suspicious":"VERDÄCHTIG","likely_fake":"WAHRSCHEINLICH FAKE",
        "verdict_reliable":"Wahrscheinlich glaubwürdig","verdict_check":"Überprüfung nötig",
        "verdict_manipulation":"Manipulationszeichen","verdict_disinfo":"Wahrscheinliche Desinformation",
        "no_confirmations":"Keine andere Quelle berichtet darüber",
        "confirmed_by":"{n} zuverlässige Quellen bestätigen",
        "one_reliable":"1 zuverlässige Quelle","only_suspicious":"Nur verdächtige Quellen",
        "sources_found":"{n} Quellen gefunden","few_confirmations":"Wenige Bestätigungen",
        "no_other_sources":"Keine bekannte Quelle veröffentlicht diese Geschichte.",
        "confirmed_many":"Von {n} seriösen Quellen bestätigt.",
        "confirmed_several":"Mehrere seriöse Quellen bestätigen.",
        "one_source_covers":"Eine seriöse Quelle berichtet darüber.",
        "only_unreliable":"Nur unzuverlässige Websites.",
        "topic_exists":"Thema existiert, aber nur in unbekannten Quellen.",
        "very_few_sources":"Sehr wenige Quellen gefunden.",
        "clickbait_markers":"Clickbait-Schlagzeile ({n} Marker)",
        "strong_emotional":"Starke emotionale Manipulation ({n} Auslöser)",
        "emotional_markers":"Emotionale Auslöser: {markers}",
        "all_caps":"Schlagzeile in GROSSBUCHSTABEN","exclamation_abuse":"Übermäßige Ausrufezeichen ({n})",
        "conspiracy_theory":"Verschwörungstheorie-Anzeichen","conspiracy_elements":"Verschwörungstheorie-Elemente",
        "too_short":"Text zu kurz ({n} Wörter)","short_text":"Kurzer Text ({n} Wörter)",
        "detailed_text":"Ausführlicher Text ({n} Wörter)","journalistic_refs":"Journalistische Quellenangaben",
        "has_refs":"Quellenangaben vorhanden","direct_quotes":"Direkte Zitate ({n})",
        "one_quote":"Ein direktes Zitat","numbers_dates":"Konkrete Zahlen und Daten",
        "anon_experts":"Anonyme 'Experten' ohne Namen ({n})",
        "google_query":"Google-Suche: \"{q}\"",
        "check_date":"Datum prüfen — alte Fakes werden oft neu veröffentlicht",
        "find_original":"Original finden: Wer hat es zuerst veröffentlicht?",
        "check_big_sources":"Reuters, BBC, AP prüfen — Schweigen ist verdächtig",
        "find_authoritative":"Seriöse Quelle statt \"{domain}\" finden",
        "confidence_high":"hoch","confidence_medium":"mittel","confidence_low":"niedrig",
        "bert_fake":"BERT: wahrscheinlich Fake","bert_real":"BERT: wahrscheinlich echt",
        "bert_unavailable":"BERT-Modell nicht geladen",
        "ai_powered_source":"🤖 KI hat diese Quelle bewertet",
        "step1":"Quelle analysieren...","step2":"Text analysieren...",
        "step3":"Globale Medien durchsuchen...","step4":"Faktencheck (Wikipedia)...",
        "step5":"BERT neuronales Netz...","step6":"Groq KI (Tiefenanalyse)...",
    },
    "fr": {
        "trusted_source":"Source fiable","likely_reliable":"Probablement fiable",
        "unknown_source":"Source inconnue","suspicious_source":"Source suspecte",
        "unreliable_source":"Source peu fiable","url_not_provided":"URL non fournie",
        "authoritative":"Média réputé","not_authoritative":"Source peu fiable",
        "unknown_domain":"Domaine inconnu","free_domain":"Domaine gratuit suspect",
        "numbers_in_domain":"Chiffres dans le nom de domaine","manipulative_name":"Nom de domaine manipulateur",
        "no_https":"Pas de HTTPS","text_quality":"Qualité du texte bonne",
        "minor_manipulation":"Légères manipulations","many_manipulation":"Nombreux signes de manipulation",
        "likely_disinfo":"Haute probabilité de désinformation",
        "reliable":"FIABLE","likely_reliable_lv":"PROBABLEMENT FIABLE",
        "check_required":"VÉRIFICATION NÉCESSAIRE","suspicious":"SUSPECT","likely_fake":"PROBABLEMENT FAUX",
        "verdict_reliable":"Probablement crédible","verdict_check":"Vérification nécessaire",
        "verdict_manipulation":"Signes de manipulation","verdict_disinfo":"Désinformation probable",
        "no_confirmations":"Aucun autre média ne couvre cette histoire",
        "confirmed_by":"Confirmé par {n} sources fiables",
        "one_reliable":"1 source fiable","only_suspicious":"Seulement des sources suspectes",
        "sources_found":"{n} sources trouvées","few_confirmations":"Peu de confirmations",
        "no_other_sources":"Aucun média connu ne publie cette histoire.",
        "confirmed_many":"Confirmé par {n} sources fiables.",
        "confirmed_several":"Plusieurs sources fiables confirment.",
        "one_source_covers":"Une source fiable couvre ce sujet.",
        "only_unreliable":"Seulement des sites peu fiables.",
        "topic_exists":"Sujet existant mais dans des sources inconnues.",
        "very_few_sources":"Très peu de sources trouvées.",
        "clickbait_markers":"Titre accrocheur ({n} marqueurs)",
        "strong_emotional":"Forte manipulation émotionnelle ({n} déclencheurs)",
        "emotional_markers":"Déclencheurs émotionnels: {markers}",
        "all_caps":"Titre EN MAJUSCULES","exclamation_abuse":"Abus de points d'exclamation ({n})",
        "conspiracy_theory":"Signes de théorie du complot","conspiracy_elements":"Éléments de théorie du complot",
        "too_short":"Texte trop court ({n} mots)","short_text":"Texte court ({n} mots)",
        "detailed_text":"Texte détaillé ({n} mots)","journalistic_refs":"Références journalistiques",
        "has_refs":"Références présentes","direct_quotes":"Citations directes ({n})",
        "one_quote":"Une citation directe","numbers_dates":"Chiffres et dates précis",
        "anon_experts":"Experts anonymes sans noms ({n})",
        "google_query":"Recherche Google: \"{q}\"",
        "check_date":"Vérifier la date — les vieux fakes sont souvent recyclés",
        "find_original":"Trouver l'original: qui l'a publié en premier?",
        "check_big_sources":"Vérifier Reuters, BBC, AP — leur silence est suspect",
        "find_authoritative":"Trouver une source fiable au lieu de \"{domain}\"",
        "confidence_high":"élevée","confidence_medium":"moyenne","confidence_low":"faible",
        "bert_fake":"BERT: probablement faux","bert_real":"BERT: probablement vrai",
        "bert_unavailable":"Modèle BERT non chargé",
        "ai_powered_source":"🤖 IA a évalué cette source",
        "step1":"Analyse de la source...","step2":"Analyse du texte...",
        "step3":"Recherche médias mondiaux...","step4":"Vérification des faits (Wikipedia)...",
        "step5":"Réseau neuronal BERT...","step6":"Groq IA (analyse approfondie)...",
    },
    "es": {
        "trusted_source":"Fuente autorizada","likely_reliable":"Probablemente fiable",
        "unknown_source":"Fuente desconocida","suspicious_source":"Fuente sospechosa",
        "unreliable_source":"Fuente poco fiable","url_not_provided":"URL no proporcionada",
        "authoritative":"Medio de comunicación reputado","not_authoritative":"Fuente poco fiable",
        "unknown_domain":"Dominio desconocido","free_domain":"Dominio gratuito sospechoso",
        "numbers_in_domain":"Números en el nombre de dominio","manipulative_name":"Nombre de dominio manipulador",
        "no_https":"Sin HTTPS","text_quality":"Calidad del texto buena",
        "minor_manipulation":"Leves signos de manipulación","many_manipulation":"Múltiples signos de manipulación",
        "likely_disinfo":"Alta probabilidad de desinformación",
        "reliable":"FIABLE","likely_reliable_lv":"PROBABLEMENTE FIABLE",
        "check_required":"REQUIERE VERIFICACIÓN","suspicious":"SOSPECHOSO","likely_fake":"PROBABLEMENTE FALSO",
        "verdict_reliable":"Probablemente creíble","verdict_check":"Requiere verificación",
        "verdict_manipulation":"Signos de manipulación","verdict_disinfo":"Probable desinformación",
        "no_confirmations":"Ningún otro medio cubre esta historia",
        "confirmed_by":"Confirmado por {n} fuentes fiables",
        "one_reliable":"1 fuente fiable","only_suspicious":"Solo fuentes sospechosas",
        "sources_found":"{n} fuentes encontradas","few_confirmations":"Pocas confirmaciones",
        "no_other_sources":"Ningún medio conocido publica esta historia.",
        "confirmed_many":"Confirmado por {n} fuentes autorizadas.",
        "confirmed_several":"Varias fuentes autorizadas confirman.",
        "one_source_covers":"Una fuente autorizada cubre este tema.",
        "only_unreliable":"Solo sitios web poco fiables.",
        "topic_exists":"El tema existe pero solo en fuentes desconocidas.",
        "very_few_sources":"Muy pocas fuentes encontradas.",
        "clickbait_markers":"Titular sensacionalista ({n} marcadores)",
        "strong_emotional":"Fuerte manipulación emocional ({n} detonadores)",
        "emotional_markers":"Detonadores emocionales: {markers}",
        "all_caps":"Titular EN MAYÚSCULAS","exclamation_abuse":"Abuso de signos de exclamación ({n})",
        "conspiracy_theory":"Signos de teoría conspirativa","conspiracy_elements":"Elementos de teoría conspirativa",
        "too_short":"Texto demasiado corto ({n} palabras)","short_text":"Texto corto ({n} palabras)",
        "detailed_text":"Texto detallado ({n} palabras)","journalistic_refs":"Referencias periodísticas",
        "has_refs":"Referencias presentes","direct_quotes":"Citas directas ({n})",
        "one_quote":"Una cita directa","numbers_dates":"Cifras y fechas concretas",
        "anon_experts":"'Expertos' anónimos sin nombres ({n})",
        "google_query":"Buscar en Google: \"{q}\"",
        "check_date":"Verificar la fecha — los fakes antiguos se reciclan",
        "find_original":"Encontrar el original: ¿quién lo publicó primero?",
        "check_big_sources":"Verificar Reuters, BBC, AP — su silencio es sospechoso",
        "find_authoritative":"Encontrar fuente autorizada en vez de \"{domain}\"",
        "confidence_high":"alta","confidence_medium":"media","confidence_low":"baja",
        "bert_fake":"BERT: probablemente falso","bert_real":"BERT: probablemente real",
        "bert_unavailable":"Modelo BERT no cargado",
        "ai_powered_source":"🤖 IA evaluó esta fuente",
        "step1":"Analizando fuente...","step2":"Analizando texto...",
        "step3":"Buscando en medios globales...","step4":"Verificación de hechos (Wikipedia)...",
        "step5":"Red neuronal BERT...","step6":"Groq IA (análisis profundo)...",
    },
    "zh": {
        "trusted_source":"权威来源","likely_reliable":"可能可靠",
        "unknown_source":"未知来源","suspicious_source":"可疑来源",
        "unreliable_source":"不可靠来源","url_not_provided":"未提供URL",
        "authoritative":"知名媒体","not_authoritative":"不可靠来源",
        "unknown_domain":"未知域名","free_domain":"可疑免费域名",
        "numbers_in_domain":"域名含数字","manipulative_name":"操纵性域名",
        "no_https":"无HTTPS","text_quality":"文本质量良好",
        "minor_manipulation":"轻微操纵迹象","many_manipulation":"多处操纵迹象",
        "likely_disinfo":"虚假信息可能性高",
        "reliable":"可信","likely_reliable_lv":"可能可信",
        "check_required":"需要核实","suspicious":"可疑","likely_fake":"可能虚假",
        "verdict_reliable":"可能可信","verdict_check":"需要核实",
        "verdict_manipulation":"操纵迹象","verdict_disinfo":"可能存在虚假信息",
        "no_confirmations":"没有其他媒体报道此新闻",
        "confirmed_by":"{n}个可靠来源确认",
        "one_reliable":"1个可靠来源","only_suspicious":"仅可疑来源",
        "sources_found":"找到{n}个来源","few_confirmations":"确认来源较少",
        "no_other_sources":"没有已知媒体发布此故事。",
        "confirmed_many":"{n}个权威来源已确认。",
        "confirmed_several":"多个权威来源确认。",
        "one_source_covers":"一个权威来源报道此主题。",
        "only_unreliable":"仅有不可靠网站。",
        "topic_exists":"主题存在但仅见于未知来源。",
        "very_few_sources":"来源极少。",
        "clickbait_markers":"标题党（{n}个标记）",
        "strong_emotional":"强烈情绪操纵（{n}个触发词）",
        "emotional_markers":"情绪触发词：{markers}",
        "all_caps":"标题全大写","exclamation_abuse":"感叹号滥用（{n}）",
        "conspiracy_theory":"阴谋论迹象","conspiracy_elements":"阴谋论元素",
        "too_short":"文本太短（{n}字）","short_text":"文本较短（{n}字）",
        "detailed_text":"详细文本（{n}字）","journalistic_refs":"新闻来源引用",
        "has_refs":"有来源引用","direct_quotes":"直接引语（{n}）",
        "one_quote":"有直接引语","numbers_dates":"具体数字和日期",
        "anon_experts":"匿名'专家'无名字（{n}）",
        "google_query":"谷歌搜索：\"{q}\"",
        "check_date":"检查日期——旧假新闻常被循环利用",
        "find_original":"查找原始来源：谁先发布的？",
        "check_big_sources":"查看路透社、BBC、美联社——沉默是可疑的",
        "find_authoritative":"找权威来源替代\"{domain}\"",
        "confidence_high":"高","confidence_medium":"中","confidence_low":"低",
        "bert_fake":"BERT：可能虚假","bert_real":"BERT：可能真实",
        "bert_unavailable":"BERT模型未加载",
        "ai_powered_source":"🤖 AI评估了此来源",
        "step1":"分析来源...","step2":"分析文本...",
        "step3":"搜索全球媒体...","step4":"核实事实（维基百科）...",
        "step5":"BERT神经网络...","step6":"Groq AI（深度分析）...",
    },
}

def tr(lang: str, key: str, **kwargs) -> str:
    s = I18N.get(lang, I18N["en"]).get(key, I18N["en"].get(key, key))
    return s.format(**kwargs) if kwargs else s

SUPPORTED_LANGS = set(I18N.keys())

# ═══════════════════════════════════════════════════════════════════════════════
# GROQ AI — умный анализ источника
# ═══════════════════════════════════════════════════════════════════════════════
def _groq_request(messages: list, max_tokens: int = 600) -> str | None:
    """Базовый запрос к Groq. Возвращает строку-ответ или None."""
    if not GROQ_API_KEY:
        return None
    payload = json.dumps({
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            GROQ_API_URL, data=payload, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {GROQ_API_KEY}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Groq] Error: {e}")
        return None


def _parse_groq_json(text: str) -> dict | None:
    """Извлекает JSON из ответа Groq (даже если есть markdown-фреймы)."""
    if not text:
        return None
    clean = re.sub(r"^```[a-z]*\n?", "", text.strip())
    clean = re.sub(r"\n?```$", "", clean).strip()
    # Если внутри есть JSON-блок
    m = re.search(r'\{.*\}', clean, re.DOTALL)
    if m:
        clean = m.group(0)
    try:
        return json.loads(clean)
    except Exception:
        return None


def groq_assess_source(domain: str, lang: str = "en") -> dict | None:
    """
    Просит Groq Llama 3-70B оценить надёжность домена.
    Кешируется по домену+язык.
    """
    cache_key = f"src:{domain}:{lang}"
    if cache_key in _groq_source_cache:
        return _groq_source_cache[cache_key]

    sys_prompt = (
        "You are a senior media-literacy researcher with knowledge of news outlets worldwide. "
        "Given a website domain, assess it as a news source. "
        "Respond ONLY with a JSON object — no markdown, no explanation outside JSON.\n"
        'Schema: {"score":<int 0-100>,"tier":<"trusted"|"likely_reliable"|"unknown"|"suspicious"|"unreliable">,'
        '"country":"<ISO country code or \'international\'>","media_type":"<newspaper|tv|agency|blog|tabloid|factchecker|other>",'
        f'"summary":"<2-sentence assessment in {lang} language>","details":["<fact1>","<fact2>","<fact3>"]'
        ',"known":true/false}'
    )
    user_prompt = (
        f'Assess this news source domain: "{domain}"\n'
        "Consider: editorial standards, fact-checking, ownership/funding, "
        "history of misinformation, journalistic awards, international recognition, "
        "regional authority. If it's a legitimate local/regional outlet, score accordingly — "
        "not all unknown sources are suspicious.\n"
        "Return ONLY the JSON."
    )
    raw = _groq_request([
        {"role": "system", "content": sys_prompt},
        {"role": "user",   "content": user_prompt},
    ], max_tokens=400)

    result = _parse_groq_json(raw)
    if result:
        result["score"] = max(5, min(95, int(result.get("score", 50))))
        if result.get("tier") not in ("trusted","likely_reliable","unknown","suspicious","unreliable"):
            result["tier"] = "unknown"
        result["ai_powered"] = True
        _groq_source_cache[cache_key] = result
    return result


def groq_deep_analyze(title: str, text: str, source_info: dict,
                      crossref_info: dict, bert_info: dict, lang: str = "en") -> dict | None:
    """
    Groq делает глубокий анализ: реальная новость или нет?
    Учитывает всё — источник, текст, кросс-референс, BERT.
    """
    cache_key = hashlib.md5(f"deep:{title[:80]}:{lang}".encode()).hexdigest()
    if cache_key in _groq_text_cache:
        return _groq_text_cache[cache_key]

    bert_note = ""
    if bert_info.get("available"):
        lbl = "REAL" if bert_info.get("label") == "REAL" else "FAKE"
        bert_note = f"\nBERT model prediction: {lbl} (confidence {bert_info.get('score',50)}%)"

    sys_prompt = (
        "You are an expert fact-checker and investigative journalist. "
        "Analyze whether a news article is credible or fake/misinformation. "
        "Respond ONLY with a JSON object.\n"
        'Schema: {"score":<int 0-100, where 100=fully credible>,'
        '"verdict":"<1 sentence verdict>","fake_signals":["<signal1>","<signal2>"],'
        '"credibility_signals":["<signal1>","<signal2>"],'
        f'"explanation":"<detailed 3-4 sentence analysis in {lang} language>",'
        '"recommendation":"<what reader should do to verify, in {lang} language>",'
        '"manipulation_type":"<none|emotional|conspiracy|clickbait|misattribution|context_missing|satire|fabricated>"}'
    )

    src_tier = source_info.get("tier", "unknown")
    src_domain = source_info.get("domain", "unknown")
    tc = crossref_info.get("trusted_count", 0)
    tf = crossref_info.get("total_found", 0)

    user_prompt = (
        f'Article title: "{title}"\n'
        f'Article text: "{text[:600]}"\n'
        f'Source domain: {src_domain} (tier: {src_tier}, score: {source_info.get("score",50)}/100)\n'
        f'Cross-reference: found in {tf} sources, {tc} of them trusted/authoritative\n'
        f'{bert_note}\n'
        "Analyze this article's credibility considering all available signals. "
        "Be especially careful about: emotional language, unverifiable claims, "
        "missing context, and whether the story appears in credible outlets.\n"
        "Return ONLY the JSON."
    )

    raw = _groq_request([
        {"role": "system", "content": sys_prompt},
        {"role": "user",   "content": user_prompt},
    ], max_tokens=600)

    result = _parse_groq_json(raw)
    if result:
        result["score"] = max(0, min(100, int(result.get("score", 50))))
        result["ai_powered"] = True
        result["model"] = f"Groq {GROQ_MODEL}"
        _groq_text_cache[cache_key] = result
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# BERT — твоя обученная модель
# ═══════════════════════════════════════════════════════════════════════════════
class BERTAnalyzer:
    """
    Загружает fakescope_finetuned — твою собственную дообученную модель
    на rubert-tiny2 (LIAR dataset EN + FakeScope-RU).
    Точность на тесте: 71.2%
    """
    def __init__(self, model_path: str = BERT_MODEL_PATH):
        self._pipe = None
        self.model_path = model_path
        self._load()

    def _load(self):
        import os
        if not os.path.exists(self.model_path):
            print(f"[BERT] Model path not found: {self.model_path}")
            return
        try:
            from transformers import pipeline as hf_pipeline
            self._pipe = hf_pipeline(
                "text-classification",
                model=self.model_path,
                tokenizer=self.model_path,
                device=-1,           # CPU
                truncation=True,
                max_length=128,
            )
            print(f"[BERT] ✅ FakeScope model loaded from {self.model_path}")
        except Exception as e:
            print(f"[BERT] Failed to load: {e}")

    def analyze(self, title: str, text: str) -> dict:
        if not self._pipe:
            return {"available": False, "score": 50, "label": "UNKNOWN",
                    "note": "BERT model not loaded — install transformers and place model in ./fakescope_finetuned"}
        inp = f"{title}. {text[:400]}" if text else title
        try:
            r = self._pipe(inp)[0]
            label = r["label"]   # "FAKE" or "REAL"
            conf  = round(r["score"] * 100)
            trust = conf if label == "REAL" else (100 - conf)
            return {"available": True, "score": trust, "label": label,
                    "confidence": conf, "model": "fakescope_finetuned (rubert-tiny2)"}
        except Exception as e:
            return {"available": False, "score": 50, "label": "ERROR", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════
class SourceAnalyzer:
    def extract_domain(self, url: str) -> str:
        url = re.sub(r'^https?://', '', url.strip())
        url = re.sub(r'^www\.', '', url)
        return url.split('/')[0].lower().split('?')[0]

    def analyze(self, url: str, lang: str = "ru") -> dict:
        if not url or not url.strip():
            return {"score": 35, "domain": "—", "tier": "unknown",
                    "verdict": tr(lang, "url_not_provided"),
                    "details": [f"⚠️ {tr(lang,'url_not_provided')}"], "ai_used": False}

        domain = self.extract_domain(url)
        score, tier, details, ai_used = 50, "unknown", [], False

        # 1. Статичный белый список
        for t2 in TRUSTED_SOURCES:
            if domain == t2 or domain.endswith('.' + t2):
                score, tier = 88, "trusted"
                details.append(f"✅ {tr(lang,'authoritative')}: {domain}")
                break

        # 2. Чёрный список
        if tier == "unknown":
            for s in SUSPICIOUS_SOURCES:
                if domain == s or domain.endswith('.' + s):
                    score, tier = 10, "suspicious"
                    details.append(f"🚨 {tr(lang,'not_authoritative')}: {domain}")
                    break

        # 3. Если всё ещё unknown — спрашиваем Groq
        if tier == "unknown":
            ai_result = groq_assess_source(domain, lang)
            if ai_result:
                score = ai_result["score"]
                tier  = ai_result["tier"]
                ai_used = True
                # Добавляем AI-вердикт
                details.append(f"🤖 {tr(lang,'ai_powered_source')}: {ai_result.get('summary','')}")
                country = ai_result.get("country", "")
                mtype   = ai_result.get("media_type", "")
                if country or mtype:
                    details.append(f"📍 {country} · {mtype}".strip(" ·"))
                for fact in ai_result.get("details", [])[:3]:
                    icon = "✅" if score >= 65 else ("⚠️" if score >= 40 else "🚨")
                    details.append(f"{icon} {fact}")
            else:
                # Groq недоступен — мягкая эвристика
                # Не помечаем как подозрительный просто потому что неизвестный
                score = 48
                details.append(f"❓ {tr(lang,'unknown_domain')}: {domain}")
                details.append("ℹ️ Groq AI недоступен — включите ключ для точной оценки")

        # 4. Технические проверки домена (применяются всегда)
        for pat, rkey in [
            (r'\.(tk|ml|ga|cf|gq|pw|cc|xyz)$', "free_domain"),
            (r'(news|breaking|viral|truth)\d{3,}', "numbers_in_domain"),
            (r'(truth|hidden|secret|exposed|realtruth)', "manipulative_name"),
        ]:
            if re.search(pat, domain):
                score -= 20
                details.append(f"⚠️ {tr(lang, rkey)}")

        # 5. HTTPS
        if url.startswith('https://'):
            details.append("✅ HTTPS")
        else:
            score -= 8
            details.append(f"⚠️ {tr(lang,'no_https')}")

        score = max(5, min(95, score))
        return {"score": score, "domain": domain, "url": url, "tier": tier,
                "verdict": self._v(score, lang), "details": details, "ai_used": ai_used}

    def _v(self, s: int, lang: str) -> str:
        if s >= 80: return tr(lang, "trusted_source")
        if s >= 65: return tr(lang, "likely_reliable")
        if s >= 45: return tr(lang, "unknown_source")
        if s >= 25: return tr(lang, "suspicious_source")
        return tr(lang, "unreliable_source")


# ═══════════════════════════════════════════════════════════════════════════════
# TEXT ANALYZER — 25 критериев
# ═══════════════════════════════════════════════════════════════════════════════
class TextAnalyzer:
    """
    25 независимых критериев оценки текста новости.
    Каждый критерий либо снижает, либо повышает итоговый балл.
    Итог: 0–100, где 100 = максимально достоверный текст.
    """

    # ── Satire / parody markers ────────────────────────────────────────────────
    SATIRE_DOMAINS  = {"theonion.com","babylonbee.com","satirewire.com",
                       "borowitz.com","thebeaverton.com","waterfordwhispersnews.com"}
    SATIRE_MARKERS  = [r'\(сатира\)',r'\(пародия\)',r'\(юмор\)',
                       r'\(satire\)',r'\(parody\)',r'\(humor\)',r'\(fiction\)']

    # ── Hedge / uncertainty language (bad sign) ────────────────────────────────
    HEDGE_PATTERNS  = [
        r'якобы\s+\w+',r'предположительно\s+\w+',r'по слухам',
        r'allegedly\s+\w+',r'reportedly\s+\w+',r'rumored to',
        r'angeblich\s+\w+',r'soll\s+\w+',
        r'apparemment\s+\w+',r'prétendument',
        r'supuestamente\s+\w+',r'al parecer',
    ]
    # ── Urgency / fear appeal ─────────────────────────────────────────────────
    URGENCY_PATTERNS = [
        r'поделитесь\s+(пока|сейчас|немедленно)',r'срочно\s+перешли',
        r'share\s+(this|now|before)',r'forward\s+this',r'spread\s+the\s+word',
        r'teilen\s+sie\s+jetzt',r'partagez\s+maintenant',r'comparte\s+ahora',
    ]
    # ── False balance / both-sidesism ─────────────────────────────────────────
    FALSE_BALANCE = [
        r'одни говорят.{5,40}другие говорят',
        r'some say.{5,40}others say',
        r'manche sagen.{5,40}andere sagen',
    ]
    # ── Missing context signals ────────────────────────────────────────────────
    MISSING_CONTEXT = [
        r'без\s+контекста',r'вырвано\s+из\s+контекста',
        r'out\s+of\s+context',r'without\s+context',
        r'aus\s+dem\s+Kontext',r'hors\s+contexte',r'fuera\s+de\s+contexto',
    ]
    # ── Personalised attack / ad hominem ──────────────────────────────────────
    AD_HOMINEM = [
        r'(предатель|враг народа|продался|куплен)',
        r'(traitor|enemy of the people|paid shill|bought)',
        r'(Verräter|Volksfeind|gekauft)',
        r'(traître|vendu|ennemi du peuple)',
        r'(traidor|vendido|enemigo del pueblo)',
    ]
    # ── Pseudo-scientific claims ───────────────────────────────────────────────
    PSEUDOSCIENCE = [
        r'(доказано учёными|100%\s+эффективн|чудо[-\s]средство)',
        r'(врачи молчат|скрытое лечение|народное средство\s+от)',
        r'(proven by scientists|miracle cure|doctors don.t want)',
        r'(von Wissenschaftlern bewiesen|Wundermittel)',
        r'(prouvé par les scientifiques|remède miracle)',
        r'(probado por científicos|cura milagrosa)',
    ]
    # ── Author / byline signals ────────────────────────────────────────────────
    AUTHOR_SIGNALS = [
        r'(корреспондент|журналист|редакция|обозреватель)',
        r'(correspondent|journalist|reporter|editor|staff writer)',
        r'(Korrespondent|Journalist|Redaktion)',
        r'(correspondant|journaliste|rédaction)',
        r'(corresponsal|periodista|redacción)',
    ]
    # ── Specific named sources (good sign) ────────────────────────────────────
    NAMED_SOURCES = [
        r'(министр|президент|директор|генерал|профессор|доктор|глава)\s+[А-ЯЁA-Z]',
        r'(minister|president|director|general|professor|doctor|chief)\s+[A-Z]',
        r'(Minister|Präsident|Direktor|Professor|Doktor)\s+[A-Z]',
        r'(ministre|président|directeur|général|professeur|docteur)\s+[A-Z]',
        r'(ministro|presidente|director|general|profesor|doctor)\s+[A-Z]',
    ]
    # ── Hyperlinks / references pattern ───────────────────────────────────────
    HYPERLINKS = r'https?://\S+'

    def analyze(self, title: str, text: str, lang: str = "ru") -> dict:
        full  = f"{title} {text}".lower()
        full_orig = f"{title} {text}"   # оригинальный регистр для некоторых проверок
        issues, positives, checks = [], [], {}
        score = 65   # базовый балл (чуть ниже чем раньше — критериев больше)
        criteria = {}  # детальный отчёт по каждому критерию

        # ── КРИТЕРИЙ 1: Кликбейт в заголовке ─────────────────────────────────
        all_cb = CLICKBAIT_RU + CLICKBAIT_EN + CLICKBAIT_DE + CLICKBAIT_FR + CLICKBAIT_ES
        cb = [p for p in all_cb if re.search(p, title, re.IGNORECASE)]
        checks["clickbait"] = len(cb)
        criteria["C01_clickbait"] = {"found": len(cb), "penalty": min(30, len(cb)*10)}
        if cb:
            score -= min(30, len(cb) * 10)
            issues.append(tr(lang, "clickbait_markers", n=len(cb)))

        # ── КРИТЕРИЙ 2: Эмоциональные триггеры ───────────────────────────────
        trig = [x for x in EMOTIONAL_TRIGGERS if x in full]
        checks["triggers"] = len(trig)
        criteria["C02_emotional"] = {"found": len(trig), "words": trig[:5]}
        if len(trig) >= 5:
            score -= 22; issues.append(tr(lang, "strong_emotional", n=len(trig)))
        elif len(trig) >= 3:
            score -= 12; issues.append(tr(lang, "strong_emotional", n=len(trig)))
        elif len(trig) >= 2:
            score -= 6; issues.append(tr(lang, "emotional_markers", markers=", ".join(trig[:3])))

        # ── КРИТЕРИЙ 3: ЗАГЛАВНЫЕ БУКВЫ в заголовке ──────────────────────────
        upper = [w for w in title.split() if w.isupper() and len(w) > 2]
        checks["upper"] = len(upper)
        criteria["C03_allcaps"] = {"count": len(upper)}
        if len(upper) > 3:
            score -= 12; issues.append(tr(lang, "all_caps"))
        elif len(upper) > 1:
            score -= 5

        # ── КРИТЕРИЙ 4: Восклицательные знаки ────────────────────────────────
        excl = title.count('!')
        checks["excl"] = excl
        criteria["C04_exclamation"] = {"count": excl}
        if excl >= 3:
            score -= 14; issues.append(tr(lang, "exclamation_abuse", n=excl))
        elif excl >= 2:
            score -= 6

        # ── КРИТЕРИЙ 5: Теории заговора ───────────────────────────────────────
        ch = sum(1 for p in [
            r'(правительство|власти)\s+(скрывает|прячет)',
            r'(учёные|врачи)\s+(молчат|боятся|куплены)',
            r'(глубинное государство|тайное правительство)',
            r'(чипирование|масоны контролируют)',
            r'(government|authorities)\s+(hiding|covering up)',
            r'(scientists|doctors)\s+(silenced|bought)',
            r'(deep state|shadow government|new world order)',
            r'(Regierung|Behörden)\s+(verbirgt|versteckt)',
            r'(gouvernement|autorités)\s+(cache|dissimule)',
            r'(gobierno|autoridades)\s+(oculta|esconde)',
        ] if re.search(p, full, re.I))
        checks["conspiracy"] = ch
        criteria["C05_conspiracy"] = {"patterns": ch}
        if ch >= 2:
            score -= 28; issues.append(tr(lang, "conspiracy_theory"))
        elif ch == 1:
            score -= 14; issues.append(tr(lang, "conspiracy_elements"))

        # ── КРИТЕРИЙ 6: Длина текста ──────────────────────────────────────────
        wc = len(text.split())
        checks["words"] = wc
        criteria["C06_length"] = {"words": wc}
        if wc < 20:
            score -= 18; issues.append(tr(lang, "too_short", n=wc))
        elif wc < 60:
            score -= 8; issues.append(tr(lang, "short_text", n=wc))
        elif wc >= 400:
            score += 9; positives.append(tr(lang, "detailed_text", n=wc))
        elif wc >= 200:
            score += 5; positives.append(tr(lang, "detailed_text", n=wc))

        # ── КРИТЕРИЙ 7: Ссылки на источники (факт-сигналы) ───────────────────
        fh = sum(1 for w in FACT_SIGNALS if w in full)
        checks["facts"] = fh
        criteria["C07_fact_signals"] = {"count": fh}
        if fh >= 5:
            score += 12; positives.append(tr(lang, "journalistic_refs"))
        elif fh >= 3:
            score += 7; positives.append(tr(lang, "journalistic_refs"))
        elif fh >= 1:
            score += 3; positives.append(tr(lang, "has_refs"))

        # ── КРИТЕРИЙ 8: Прямые цитаты ────────────────────────────────────────
        qt = len(re.findall(r'[«»""][^«»""]{10,100}[«»""]', text))
        checks["quotes"] = qt
        criteria["C08_quotes"] = {"count": qt}
        if qt >= 3:
            score += 10; positives.append(tr(lang, "direct_quotes", n=qt))
        elif qt >= 2:
            score += 7; positives.append(tr(lang, "direct_quotes", n=qt))
        elif qt == 1:
            score += 4; positives.append(tr(lang, "one_quote"))

        # ── КРИТЕРИЙ 9: Конкретные числа и даты ──────────────────────────────
        nums = len(re.findall(
            r'\b\d+[.,]?\d*\s*(млн|млрд|тыс|%|руб|\$|₽|€|тг|сом|'
            r'million|billion|thousand|percent|Mio|Mrd|Millionen|Milliarden|'
            r'millions|milliards|millones|miles de millones)',
            text, re.I))
        dts = len(re.findall(
            r'\b\d{1,2}\s*(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря'
            r'|January|February|March|April|May|June|July|August|September|October|November|December'
            r'|Januar|Februar|März|Juni|Juli|Oktober|Dezember'
            r'|janvier|février|mars|avril|juin|juillet|août|octobre|novembre|décembre'
            r'|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)',
            text, re.I))
        years = len(re.findall(r'\b(19|20)\d{2}\b', text))
        checks["numbers"] = nums + dts + years
        criteria["C09_numbers"] = {"nums": nums, "dates": dts, "years": years}
        if nums + dts + years >= 4:
            score += 9; positives.append(tr(lang, "numbers_dates"))
        elif nums + dts + years >= 2:
            score += 5; positives.append(tr(lang, "numbers_dates"))
        elif nums + dts + years >= 1:
            score += 2

        # ── КРИТЕРИЙ 10: Анонимные «эксперты» ────────────────────────────────
        anon_pats = [
            r'эксперты говорят', r'учёные выяснили', r'источники сообщают',
            r'эксперты считают', r'по данным источников',
            r'experts say', r'scientists claim', r'sources report',
            r'insiders reveal', r'anonymous sources', r'sources familiar with',
            r'Experten sagen', r'Quellen berichten', r'Insider berichten',
            r'experts affirment', r'sources indiquent', r'initiés révèlent',
            r'expertos dicen', r'fuentes informan', r'fuentes anónimas',
        ]
        anon = sum(1 for p in anon_pats if re.search(p, full))
        checks["anon_experts"] = anon
        criteria["C10_anon_experts"] = {"count": anon}
        if anon >= 3:
            score -= 14; issues.append(tr(lang, "anon_experts", n=anon))
        elif anon >= 2:
            score -= 8; issues.append(tr(lang, "anon_experts", n=anon))

        # ── КРИТЕРИЙ 11: Именованные источники (хороший знак) ────────────────
        named = sum(1 for p in self.NAMED_SOURCES if re.search(p, full_orig))
        checks["named_sources"] = named
        criteria["C11_named_sources"] = {"count": named}
        if named >= 3:
            score += 10; positives.append("Конкретные персоны упомянуты (≥3)" if lang == "ru" else "Named people cited (≥3)")
        elif named >= 1:
            score += 5; positives.append("Конкретная персона упомянута" if lang == "ru" else "Named person cited")

        # ── КРИТЕРИЙ 12: Автор / байлайн ─────────────────────────────────────
        has_author = any(re.search(p, full, re.I) for p in self.AUTHOR_SIGNALS)
        checks["has_author"] = has_author
        criteria["C12_author"] = {"found": has_author}
        if has_author:
            score += 5; positives.append("Упоминание автора/редакции" if lang == "ru" else "Author/byline present")

        # ── КРИТЕРИЙ 13: Гиперссылки в тексте ────────────────────────────────
        links = re.findall(self.HYPERLINKS, text)
        checks["links"] = len(links)
        criteria["C13_links"] = {"count": len(links)}
        if len(links) >= 2:
            score += 6; positives.append("Гиперссылки на источники" if lang == "ru" else "Hyperlinks to sources")
        elif len(links) == 1:
            score += 3

        # ── КРИТЕРИЙ 14: Срочность/призыв к распространению ──────────────────
        urgency = sum(1 for p in self.URGENCY_PATTERNS if re.search(p, full, re.I))
        checks["urgency"] = urgency
        criteria["C14_urgency"] = {"count": urgency}
        if urgency >= 2:
            score -= 18; issues.append("Агрессивный призыв распространять" if lang == "ru" else "Aggressive share-bait")
        elif urgency == 1:
            score -= 10; issues.append("Призыв срочно распространить" if lang == "ru" else "Urgency share appeal")

        # ── КРИТЕРИЙ 15: Псевдонаука / чудо-средства ─────────────────────────
        pseudo = sum(1 for p in self.PSEUDOSCIENCE if re.search(p, full, re.I))
        checks["pseudoscience"] = pseudo
        criteria["C15_pseudoscience"] = {"count": pseudo}
        if pseudo >= 2:
            score -= 20; issues.append("Псевдонаучные утверждения" if lang == "ru" else "Pseudoscientific claims")
        elif pseudo == 1:
            score -= 10; issues.append("Сомнительные научные утверждения" if lang == "ru" else "Dubious scientific claims")

        # ── КРИТЕРИЙ 16: Ad hominem / личные нападки ─────────────────────────
        ad_hom = sum(1 for p in self.AD_HOMINEM if re.search(p, full, re.I))
        checks["ad_hominem"] = ad_hom
        criteria["C16_ad_hominem"] = {"count": ad_hom}
        if ad_hom >= 2:
            score -= 15; issues.append("Личные нападки вместо аргументов" if lang == "ru" else "Ad hominem attacks")
        elif ad_hom == 1:
            score -= 7

        # ── КРИТЕРИЙ 17: Сатира / пародия ────────────────────────────────────
        is_satire = any(re.search(p, full, re.I) for p in self.SATIRE_MARKERS)
        checks["satire"] = is_satire
        criteria["C17_satire"] = {"detected": is_satire}
        if is_satire:
            score -= 30; issues.append("Маркеры сатиры/пародии — не реальная новость" if lang == "ru"
                                        else "Satire/parody markers — not real news")

        # ── КРИТЕРИЙ 18: Неопределённые утверждения (hedge) ──────────────────
        hedges = sum(1 for p in self.HEDGE_PATTERNS if re.search(p, full, re.I))
        checks["hedges"] = hedges
        criteria["C18_hedge"] = {"count": hedges}
        if hedges >= 3:
            score -= 10; issues.append("Много предположительных утверждений" if lang == "ru"
                                        else "Many unverified hedged claims")
        elif hedges >= 1:
            score -= 4

        # ── КРИТЕРИЙ 19: Соотношение заголовок/текст (кликбейт-разрыв) ───────
        if wc >= 20:
            title_words = set(re.sub(r'[^\w]', ' ', title.lower()).split())
            text_words  = set(re.sub(r'[^\w]', ' ', text.lower()).split())
            stop = {"и","в","на","с","по","the","a","an","is","was","to","of","in"}
            title_kw = title_words - stop
            if title_kw:
                overlap = len(title_kw & text_words) / len(title_kw)
                checks["title_text_overlap"] = round(overlap, 2)
                criteria["C19_title_gap"] = {"overlap": round(overlap, 2)}
                if overlap < 0.15:
                    score -= 12; issues.append("Заголовок не соответствует тексту" if lang == "ru"
                                               else "Headline-text mismatch (clickbait gap)")
                elif overlap > 0.5:
                    score += 4; positives.append("Заголовок соответствует тексту" if lang == "ru"
                                                  else "Headline matches text content")

        # ── КРИТЕРИЙ 20: Множественные вопросительные заголовки ──────────────
        q_marks = title.count('?')
        checks["questions"] = q_marks
        criteria["C20_questions"] = {"count": q_marks}
        if q_marks >= 2:
            score -= 8; issues.append("Множественные вопросы в заголовке" if lang == "ru"
                                       else "Multiple questions in headline (Betteridge's law)")
        elif q_marks == 1 and wc < 40:
            score -= 4  # вопрос + короткий текст = подозрительно

        # ── КРИТЕРИЙ 21: Структура текста (абзацы) ────────────────────────────
        paragraphs = len([p for p in text.split('\n') if len(p.strip()) > 30])
        checks["paragraphs"] = paragraphs
        criteria["C21_structure"] = {"paragraphs": paragraphs}
        if paragraphs >= 4:
            score += 6; positives.append("Структурированный текст (≥4 абзаца)" if lang == "ru"
                                          else "Well-structured text (≥4 paragraphs)")
        elif paragraphs >= 2:
            score += 3

        # ── КРИТЕРИЙ 22: Временны́е маркеры (актуальность) ───────────────────
        time_markers = len(re.findall(
            r'\b(сегодня|вчера|сейчас|недавно|только что|ранее|в\s+\w+\s+году'
            r'|today|yesterday|now|recently|just|earlier|this\s+\w+|last\s+\w+'
            r'|heute|gestern|jetzt|kürzlich|aujourd.hui|hier|maintenant|récemment'
            r'|hoy|ayer|ahora|recientemente)\b',
            full, re.I))
        checks["time_markers"] = time_markers
        criteria["C22_time"] = {"count": time_markers}
        if time_markers >= 2:
            score += 4; positives.append("Временны́е маркеры актуальности" if lang == "ru"
                                           else "Temporal markers of recency")

        # ── КРИТЕРИЙ 23: Противоречивые факты внутри текста ──────────────────
        contradictions = 0
        contra_pairs = [
            ("все знают", "никто не знает"), ("everyone knows", "nobody knows"),
            ("всегда", "никогда"), ("always", "never"),
            ("доказано", "не доказано"), ("proven", "unproven"),
        ]
        for w1, w2 in contra_pairs:
            if w1 in full and w2 in full:
                contradictions += 1
        checks["contradictions"] = contradictions
        criteria["C23_contradictions"] = {"count": contradictions}
        if contradictions >= 2:
            score -= 16; issues.append("Внутренние противоречия в тексте" if lang == "ru"
                                        else "Internal contradictions in text")
        elif contradictions == 1:
            score -= 7

        # ── КРИТЕРИЙ 24: Сенсационные обобщения (все/никогда/всегда) ─────────
        absolutes = len(re.findall(
            r'\b(абсолютно все|всегда|никогда|каждый|everywhere|always|never|everyone|'
            r'nobody|absolut\s+alle|immer|niemals|toujours|jamais|tout\s+le\s+monde|'
            r'siempre|nunca|todo\s+el\s+mundo)\b', full, re.I))
        checks["absolutes"] = absolutes
        criteria["C24_absolutes"] = {"count": absolutes}
        if absolutes >= 4:
            score -= 10; issues.append("Чрезмерные абсолютные утверждения" if lang == "ru"
                                        else "Excessive absolute statements")
        elif absolutes >= 2:
            score -= 4

        # ── КРИТЕРИЙ 25: Баланс позитив/негатив (тональность) ────────────────
        positive_words = len(re.findall(
            r'\b(подтверждён|доказан|официально|успешно|достигнут|открыт|улучшен'
            r'|confirmed|proven|officially|successfully|achieved|improved|announced'
            r'|bestätigt|erfolgreich|offiziell|confirmé|officiellement|confirmado|exitosamente)\b',
            full, re.I))
        negative_words = len(re.findall(
            r'\b(ужас|катастрофа|конец|разрушен|уничтожен|обман|ложь|смерть|гибель'
            r'|horror|catastrophe|disaster|destroyed|annihilated|collapse|death|doom'
            r'|Katastrophe|Untergang|catastrophe|désastre|destruction|catástrofe|desastre)\b',
            full, re.I))
        checks["sentiment_pos"] = positive_words
        checks["sentiment_neg"] = negative_words
        criteria["C25_sentiment"] = {"positive": positive_words, "negative": negative_words}
        if negative_words >= 5 and positive_words == 0:
            score -= 8; issues.append("Исключительно негативная тональность" if lang == "ru"
                                       else "Exclusively negative tone (fear-mongering)")
        elif positive_words >= 3:
            score += 3

        # ══════════════════════════════════════════════════════════════════════
        # БЛОК B — ЛИНГВИСТИЧЕСКИЙ АНАЛИЗ (критерии 26–35)
        # ══════════════════════════════════════════════════════════════════════

        # ── КРИТЕРИЙ 26: Средняя длина предложения ────────────────────────────
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        if sentences:
            avg_sent = sum(len(s.split()) for s in sentences) / len(sentences)
            checks["avg_sentence_len"] = round(avg_sent, 1)
            criteria["C26_sentence_len"] = {"avg_words": round(avg_sent, 1), "count": len(sentences)}
            if avg_sent < 4:
                score -= 8; issues.append("Очень короткие предложения — телеграфный стиль фейков" if lang=="ru"
                                           else "Very short sentences — fake-news telegram style")
            elif 12 <= avg_sent <= 30:
                score += 5; positives.append("Нормальная длина предложений" if lang=="ru"
                                              else "Normal sentence length (journalistic style)")
            elif avg_sent > 50:
                score -= 5  # слишком длинные — плохая редактура

        # ── КРИТЕРИЙ 27: Лексическое разнообразие (TTR) ──────────────────────
        words_list = re.findall(r'\b[а-яёa-z]{4,}\b', full)
        if len(words_list) >= 20:
            ttr = len(set(words_list)) / len(words_list)
            checks["lexical_diversity"] = round(ttr, 3)
            criteria["C27_lexical_diversity"] = {"ttr": round(ttr, 3), "total_words": len(words_list)}
            if ttr > 0.72:
                score += 6; positives.append("Богатый словарный запас текста" if lang=="ru"
                                               else "Rich vocabulary (high lexical diversity)")
            elif ttr < 0.40:
                score -= 7; issues.append("Бедный словарный запас — признак низкого качества" if lang=="ru"
                                           else "Low lexical diversity — low-quality writing")

        # ── КРИТЕРИЙ 28: Плотность существительных (информативность) ─────────
        nouns_ru = len(re.findall(r'\b[а-яё]{5,}(ция|ния|ость|ство|тель|ник|щик)\b', full))
        nouns_en = len(re.findall(r'\b[a-z]{4,}(tion|sion|ment|ness|ity|ance|ence)\b', full))
        noun_density = nouns_ru + nouns_en
        checks["noun_density"] = noun_density
        criteria["C28_noun_density"] = {"count": noun_density}
        if noun_density >= 8:
            score += 5; positives.append("Информативный текст (высокая плотность существительных)" if lang=="ru"
                                          else "Informative text (high noun density)")
        elif noun_density <= 1 and wc > 50:
            score -= 4

        # ── КРИТЕРИЙ 29: Повторяющиеся фразы (пропаганда/спам) ───────────────
        phrases_3w = re.findall(r'\b(\w+\s+\w+\s+\w+)\b', full)
        if phrases_3w:
            from collections import Counter
            phrase_counts = Counter(phrases_3w)
            max_repeat = phrase_counts.most_common(1)[0][1] if phrase_counts else 0
            checks["max_phrase_repeat"] = max_repeat
            criteria["C29_repetition"] = {"max_repeat": max_repeat}
            if max_repeat >= 4:
                score -= 12; issues.append("Навязчивые повторяющиеся фразы (пропаганда)" if lang=="ru"
                                            else "Repetitive phrases (propaganda technique)")
            elif max_repeat >= 3:
                score -= 5

        # ── КРИТЕРИЙ 30: Соотношение прилагательных к существительным ─────────
        # Много оценочных прилагательных = манипуляция
        adj_ru = len(re.findall(r'\b[а-яё]{4,}(ный|ной|ский|ской|овый|евый|альный)\b', full))
        adj_en = len(re.findall(r'\b[a-z]{4,}(ous|ful|ive|ical|ary|ory|able|ible)\b', full))
        total_adj = adj_ru + adj_en
        checks["adjectives"] = total_adj
        criteria["C30_adjective_density"] = {"count": total_adj}
        if total_adj > 25 and wc < 200:
            score -= 7; issues.append("Перегружен оценочными прилагательными" if lang=="ru"
                                       else "Overloaded with evaluative adjectives")
        elif 5 <= total_adj <= 20:
            score += 3

        # ── КРИТЕРИЙ 31: Глаголы активного действия (журналистика) ────────────
        action_verbs = len(re.findall(
            r'\b(сообщил|заявил|подтвердил|объявил|опроверг|рассказал|прокомментировал|'
            r'said|stated|confirmed|announced|denied|reported|declared|claimed|acknowledged|'
            r'sagte|erklärte|bestätigte|a déclaré|a confirmé|declaró|confirmó)\b',
            full, re.I))
        checks["action_verbs"] = action_verbs
        criteria["C31_action_verbs"] = {"count": action_verbs}
        if action_verbs >= 3:
            score += 8; positives.append("Журналистские глаголы атрибуции (≥3)" if lang=="ru"
                                          else "Journalistic attribution verbs (≥3)")
        elif action_verbs >= 1:
            score += 4

        # ── КРИТЕРИЙ 32: Цифровые данные — проценты/статистика ────────────────
        stats = len(re.findall(
            r'\b\d+[.,]?\d*\s*(%|процент|percent|Prozent|pourcent|por\s+ciento)\b'
            r'|\bна\s+\d+\s*%\b|\bby\s+\d+\s*%\b|\bum\s+\d+\s*%\b',
            text, re.I))
        checks["statistics"] = stats
        criteria["C32_statistics"] = {"count": stats}
        if stats >= 3:
            score += 8; positives.append("Конкретная статистика (≥3 показателя)" if lang=="ru"
                                          else "Concrete statistics (≥3 data points)")
        elif stats >= 1:
            score += 4

        # ── КРИТЕРИЙ 33: Упоминание конкурирующих точек зрения ────────────────
        counter_views = len(re.findall(
            r'\b(однако|тем не менее|с другой стороны|критики|оппоненты|возражают|'
            r'however|nevertheless|on the other hand|critics|opponents|objected|'
            r'jedoch|andererseits|Kritiker|cependant|d.autre part|sin embargo|por otro lado)\b',
            full, re.I))
        checks["counter_views"] = counter_views
        criteria["C33_balance"] = {"count": counter_views}
        if counter_views >= 2:
            score += 7; positives.append("Представлены альтернативные точки зрения" if lang=="ru"
                                          else "Alternative viewpoints presented (balanced reporting)")
        elif counter_views >= 1:
            score += 3

        # ── КРИТЕРИЙ 34: Юридические/официальные термины ──────────────────────
        legal_terms = len(re.findall(
            r'\b(закон|постановление|указ|договор|соглашение|протокол|резолюция|'
            r'law|decree|regulation|agreement|treaty|protocol|resolution|legislation|'
            r'Gesetz|Verordnung|Vertrag|loi|décret|règlement|ley|decreto|acuerdo)\b',
            full, re.I))
        checks["legal_terms"] = legal_terms
        criteria["C34_legal"] = {"count": legal_terms}
        if legal_terms >= 2:
            score += 5; positives.append("Официальные/юридические термины" if lang=="ru"
                                          else "Official/legal terminology present")

        # ── КРИТЕРИЙ 35: Язык угрозы и страха ─────────────────────────────────
        fear_lang = len(re.findall(
            r'\b(угрожает|опасность|риск|угроза|смертельно|убьёт|уничтожит|катастрофически|'
            r'threatens|dangerous|deadly|catastrophic|devastating|kill|destroy|collapse|'
            r'bedroht|gefährlich|tödlich|katastrophal|menace|dangereux|mortel|catastrophique|'
            r'amenaza|peligroso|mortal|catastrófico)\b',
            full, re.I))
        checks["fear_language"] = fear_lang
        criteria["C35_fear"] = {"count": fear_lang}
        if fear_lang >= 6:
            score -= 14; issues.append("Язык страха и угроз (fear-mongering)" if lang=="ru"
                                        else "Excessive fear/threat language")
        elif fear_lang >= 3:
            score -= 6

        # ══════════════════════════════════════════════════════════════════════
        # БЛОК C — АНАЛИЗ URL И СТРУКТУРЫ ПУБЛИКАЦИИ (критерии 36–45)
        # ══════════════════════════════════════════════════════════════════════

        # ── КРИТЕРИЙ 36: Числа в заголовке (кликбейт-листикл) ─────────────────
        title_nums = re.findall(r'\b(\d+)\s+(причин|способ|факт|вещ|признак|шаг|'
                                r'reasons|ways|facts|things|signs|steps|tips)\b', title, re.I)
        checks["listicle"] = len(title_nums)
        criteria["C36_listicle"] = {"found": len(title_nums)}
        if len(title_nums) >= 1:
            score -= 5; issues.append("Листикл-заголовок (кликбейт-формат)" if lang=="ru"
                                       else "Listicle headline (clickbait format)")

        # ── КРИТЕРИЙ 37: Заглавие начинается с вопроса «Почему...» ───────────
        why_headline = bool(re.match(
            r'^(почему|зачем|как так|неужели|разве|can\s+you\s+believe|why\s+is|'
            r'warum\s+ist|pourquoi|¿por\s+qué)', title.lower()))
        checks["why_headline"] = why_headline
        criteria["C37_why_headline"] = {"found": why_headline}
        if why_headline:
            score -= 6; issues.append("Заголовок-вопрос без ответа в тексте" if lang=="ru"
                                       else "Unanswered question headline (Betteridge)")

        # ── КРИТЕРИЙ 38: Email/контакты редакции в тексте ─────────────────────
        has_contact = bool(re.search(
            r'(редакция|contacts|kontakt|contact|редактор|editor)\s*[:@]?\s*\w+@\w+\.\w+'
            r'|\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', full, re.I))
        checks["has_contact"] = has_contact
        criteria["C38_contact"] = {"found": has_contact}
        if has_contact:
            score += 5; positives.append("Контакты редакции указаны" if lang=="ru"
                                          else "Editorial contact info present")

        # ── КРИТЕРИЙ 39: Специфические места (топонимы) ───────────────────────
        locations = len(re.findall(
            r'\b(Москва|Лондон|Вашингтон|Пекин|Берлин|Париж|Нью-Йорк|Токио|Брюссель|Женева|'
            r'Moscow|London|Washington|Beijing|Berlin|Paris|New York|Tokyo|Brussels|Geneva|'
            r'Astana|Bishkek|Tashkent|Baku|Yerevan|Tbilisi|Minsk|Kyiv|'
            r'Алматы|Бишкек|Ташкент|Баку|Ереван|Тбилиси|Минск|Киев|Нур-Султан)\b',
            full_orig, re.I))
        checks["locations"] = locations
        criteria["C39_locations"] = {"count": locations}
        if locations >= 2:
            score += 5; positives.append("Конкретные географические места" if lang=="ru"
                                          else "Specific geographic locations cited")
        elif locations >= 1:
            score += 2

        # ── КРИТЕРИЙ 40: Упоминание организаций (ООН, НАТО, ВОЗ и т.д.) ───────
        orgs = len(re.findall(
            r'\b(ООН|НАТО|ВОЗ|МВФ|ЕС|ОБСЕ|ВТО|МУС|ЮНИСЕФ|МАГАТЭ|'
            r'UN|NATO|WHO|IMF|EU|OSCE|WTO|ICC|UNICEF|IAEA|G7|G20|'
            r'UEFA|FIFA|IOC|Interpol|Europol)\b',
            full_orig))
        checks["organizations"] = orgs
        criteria["C40_organizations"] = {"count": orgs}
        if orgs >= 2:
            score += 6; positives.append("Упоминание международных организаций" if lang=="ru"
                                          else "International organizations referenced")
        elif orgs >= 1:
            score += 3

        # ── КРИТЕРИЙ 41: Длина заголовка (оптимум 6–12 слов) ─────────────────
        title_words_count = len(title.split())
        checks["title_length"] = title_words_count
        criteria["C41_title_length"] = {"words": title_words_count}
        if title_words_count > 20:
            score -= 5; issues.append("Слишком длинный заголовок" if lang=="ru"
                                       else "Excessively long headline")
        elif title_words_count < 3:
            score -= 8; issues.append("Слишком короткий заголовок" if lang=="ru"
                                       else "Excessively short headline")
        elif 6 <= title_words_count <= 14:
            score += 3

        # ── КРИТЕРИЙ 42: Смешение языков (подозрительно в локальных СМИ) ──────
        ru_words = len(re.findall(r'[а-яё]{4,}', full))
        en_words = len(re.findall(r'[a-z]{4,}', full))
        if wc > 30:
            if ru_words > 0 and en_words > 0:
                mix_ratio = min(ru_words, en_words) / max(ru_words, en_words)
                checks["language_mix"] = round(mix_ratio, 2)
                criteria["C42_language_mix"] = {"ru": ru_words, "en": en_words, "ratio": round(mix_ratio, 2)}
                # Умеренное смешение норм; сильное — подозрительно для коротких текстов
                if mix_ratio > 0.4 and wc < 100:
                    score -= 4

        # ── КРИТЕРИЙ 43: Скобки в заголовке (пояснения = профессионализм) ─────
        brackets = len(re.findall(r'\([^)]{3,30}\)', title))
        checks["title_brackets"] = brackets
        criteria["C43_brackets"] = {"count": brackets}
        if brackets >= 1:
            score += 3; positives.append("Пояснения в скобках в заголовке" if lang=="ru"
                                          else "Clarifying parentheses in headline")

        # ── КРИТЕРИЙ 44: Паттерны дезинформации в структуре текста ──────────
        disinfo_structures = sum(1 for p in [
            r'(учёные|врачи|эксперты)\s+(доказали|выяснили|обнаружили)\s+что\s+\w+\s+(опасн|вред|убива)',
            r'(scientists|doctors|experts)\s+(proved|found|discovered)\s+that\s+\w+\s+(dangerous|harmful|kill)',
            r'(официальные\s+лица|власти)\s+(признали|подтвердили)\s+(провал|ошибку|обман)',
            r'(officials|authorities)\s+(admitted|confirmed)\s+(failure|mistake|deception)',
            r'(сенсационное|шокирующее|невероятное)\s+(открытие|разоблачение|признание)',
            r'(sensational|shocking|incredible)\s+(discovery|revelation|admission)',
        ] if re.search(p, full, re.I))
        checks["disinfo_structures"] = disinfo_structures
        criteria["C44_disinfo_struct"] = {"count": disinfo_structures}
        if disinfo_structures >= 2:
            score -= 18; issues.append("Типичная структура дезинформации" if lang=="ru"
                                        else "Classic disinformation narrative structure")
        elif disinfo_structures == 1:
            score -= 9

        # ── КРИТЕРИЙ 45: Позитивные индикаторы журналистики ──────────────────
        journalism_markers = sum(1 for p in [
            r'(пресс-конференц|пресс-релиз|официальное заявление)',
            r'(press conference|press release|official statement|briefing)',
            r'(Pressekonferenz|Pressemitteilung|offizielle Erklärung)',
            r'(conférence de presse|communiqué de presse|déclaration officielle)',
            r'(rueda de prensa|comunicado de prensa|declaración oficial)',
        ] if re.search(p, full, re.I))
        checks["journalism_markers"] = journalism_markers
        criteria["C45_journalism"] = {"count": journalism_markers}
        if journalism_markers >= 2:
            score += 8; positives.append("Профессиональные журналистские маркеры" if lang=="ru"
                                          else "Professional journalism markers (press conf./releases)")
        elif journalism_markers >= 1:
            score += 4

        # ══════════════════════════════════════════════════════════════════════
        # БЛОК D — КОНТЕКСТНЫЙ АНАЛИЗ (критерии 46–55)
        # ══════════════════════════════════════════════════════════════════════

        # ── КРИТЕРИЙ 46: Апелляция к авторитету без имени ────────────────────
        false_authority = len(re.findall(
            r'\b(многие эксперты|ряд учёных|некоторые специалисты|'
            r'many experts|some scientists|certain specialists|'
            r'viele Experten|einige Wissenschaftler|'
            r'de nombreux experts|certains spécialistes|'
            r'muchos expertos|algunos científicos)\b', full, re.I))
        checks["false_authority"] = false_authority
        criteria["C46_false_authority"] = {"count": false_authority}
        if false_authority >= 3:
            score -= 12; issues.append("Апелляция к безымянным авторитетам (≥3)" if lang=="ru"
                                        else "Appeal to unnamed authorities (≥3)")
        elif false_authority >= 1:
            score -= 5

        # ── КРИТЕРИЙ 47: Условные конструкции (могло бы быть) ────────────────
        conditionals = len(re.findall(
            r'\b(мог бы|могло бы|если бы|возможно что|вероятно что|'
            r'could have|might have|if it were|possibly|allegedly|'
            r'könnte|hätte|wenn es wäre|möglicherweise|'
            r'pourrait|aurait pu|si c.était|possiblement|'
            r'podría|habría|si fuera|posiblemente)\b', full, re.I))
        checks["conditionals"] = conditionals
        criteria["C47_conditionals"] = {"count": conditionals}
        if conditionals >= 4:
            score -= 8; issues.append("Много домыслов и условных утверждений" if lang=="ru"
                                       else "Many speculative/conditional statements")

        # ── КРИТЕРИЙ 48: Ссылки на «засекреченные документы» ─────────────────
        secret_docs = len(re.findall(
            r'\b(секретный документ|рассекреченные файлы|утечка документов|'
            r'secret document|leaked files|classified document|whistleblower|'
            r'geheimes Dokument|durchgesickerte Dateien|'
            r'document secret|fichiers divulgués|'
            r'documento secreto|archivos filtrados)\b', full, re.I))
        checks["secret_docs"] = secret_docs
        criteria["C48_secret_docs"] = {"count": secret_docs}
        if secret_docs >= 2:
            score -= 14; issues.append("Ссылки на «секретные документы»" if lang=="ru"
                                        else "References to 'secret/leaked documents'")
        elif secret_docs == 1:
            score -= 6

        # ── КРИТЕРИЙ 49: Упоминание конкретных законов/решений ───────────────
        law_refs = len(re.findall(
            r'\b(Федеральный закон|Постановление №|Указ Президента|'
            r'Federal Law|Executive Order|Act No\.|Resolution No\.|'
            r'Bundesgesetz|Verordnung Nr\.|'
            r'Loi fédérale|Ordonnance n°|'
            r'Ley Federal|Decreto No\.)\b', full_orig, re.I))
        checks["law_refs"] = law_refs
        criteria["C49_law_refs"] = {"count": law_refs}
        if law_refs >= 1:
            score += 7; positives.append("Ссылки на конкретные законы/постановления" if lang=="ru"
                                          else "References to specific laws/regulations")

        # ── КРИТЕРИЙ 50: Нарративные клише фейков ────────────────────────────
        fake_narratives = sum(1 for p in [
            r'(мировая элита|мировое правительство|новый мировой порядок)',
            r'(world elite|world government|new world order|global reset)',
            r'(Weltelite|Weltregierung|Neue Weltordnung)',
            r'(élite mondiale|gouvernement mondial|nouvel ordre mondial)',
            r'(élite global|gobierno mundial|nuevo orden mundial)',
            r'(план(демия|дерни)|план по уничтожению|геноцид населения)',
            r'(plandemic|plan to destroy|genocide of population)',
            r'(Pharmaindustrie\s+verbirgt|Big\s+Pharma\s+hides|фармацевтическое\s+лобби\s+скрывает)',
            r'(5G\s+(убивает|контролирует|заражает)|5G\s+(kills|controls|spreads))',
            r'(вакцин(а|ы)\s+(чипирует|убивает|содержит\s+яд)|vaccine\s+(microchip|kills|poison))',
        ] if re.search(p, full, re.I))
        checks["fake_narratives"] = fake_narratives
        criteria["C50_fake_narratives"] = {"count": fake_narratives}
        if fake_narratives >= 2:
            score -= 30; issues.append("Известные нарративы дезинформации (≥2)" if lang=="ru"
                                        else "Known disinformation narratives (≥2)")
        elif fake_narratives == 1:
            score -= 15; issues.append("Известный нарратив дезинформации" if lang=="ru"
                                        else "Known disinformation narrative detected")

        # ── КРИТЕРИЙ 51: Исторические параллели (манипуляция) ────────────────
        hist_parallels = len(re.findall(
            r'\b(как при Гитлере|как в нацистской|напоминает 1984|как в СССР|'
            r'like Hitler|like the Nazis|reminds of 1984|like the USSR|just like Nazi|'
            r'wie unter Hitler|wie in der Nazi|erinnert an 1984)\b', full, re.I))
        checks["hist_parallels"] = hist_parallels
        criteria["C51_godwin"] = {"count": hist_parallels}
        if hist_parallels >= 1:
            score -= 10; issues.append("Манипулятивные исторические параллели (Закон Годвина)" if lang=="ru"
                                        else "Manipulative historical parallels (Godwin's Law)")

        # ── КРИТЕРИЙ 52: Научные ссылки (DOI, журналы) ───────────────────────
        science_refs = len(re.findall(
            r'\b(doi:|arxiv\.|pubmed|nature\.|science\.|lancet\.|nejm\.|bmj\.|'
            r'peer.reviewed|рецензируемое\s+исследование|научный\s+журнал|'
            r'fachwissenschaftlich|revue\s+scientifique|revista\s+científica)\b',
            full, re.I))
        checks["science_refs"] = science_refs
        criteria["C52_science"] = {"count": science_refs}
        if science_refs >= 1:
            score += 10; positives.append("Ссылки на научные работы/журналы" if lang=="ru"
                                           else "References to scientific papers/journals")

        # ── КРИТЕРИЙ 53: Медиаграмотность — призыв проверять ─────────────────
        verify_calls = len(re.findall(
            r'\b(проверьте|убедитесь|по данным|в соответствии с|'
            r'check|verify|according to|as reported by|'
            r'überprüfen|gemäß|laut|'
            r'vérifiez|selon|d.après|'
            r'verifique|según|de acuerdo con)\b', full, re.I))
        checks["verify_calls"] = verify_calls
        criteria["C53_verify"] = {"count": verify_calls}
        if verify_calls >= 3:
            score += 5; positives.append("Журналистские ссылки на проверку данных" if lang=="ru"
                                          else "Journalistic data verification references")

        # ── КРИТЕРИЙ 54: Финансовая / экономическая конкретика ───────────────
        financial = len(re.findall(
            r'\b(\$\s*\d+|\€\s*\d+|₽\s*\d+|тг\s*\d+|\d+\s*(млрд|млн|трлн|billion|trillion|million)'
            r'|\bВВП\b|\bGDP\b|\bбюджет\b|\bbudget\b|\bинвестиции\b|\binvestment\b)\b',
            text, re.I))
        checks["financial"] = financial
        criteria["C54_financial"] = {"count": financial}
        if financial >= 3:
            score += 6; positives.append("Конкретные финансовые данные" if lang=="ru"
                                          else "Concrete financial/economic data")
        elif financial >= 1:
            score += 3

        # ── КРИТЕРИЙ 55: Медицинская/техническая терминология ────────────────
        technical = len(re.findall(
            r'\b(мРНК|антитела|иммунитет|вирус|вакцин|штамм|геном|ДНК|РНК|'
            r'mRNA|antibodies|immunity|virus|vaccine|strain|genome|DNA|RNA|'
            r'протокол|алгоритм|протокол|байт|мегабайт|терабайт|'
            r'protocol|algorithm|byte|megabyte|terabyte)\b', full, re.I))
        checks["technical"] = technical
        criteria["C55_technical"] = {"count": technical}
        if technical >= 4:
            score += 5; positives.append("Профессиональная терминология" if lang=="ru"
                                          else "Professional/technical terminology")

        # ══════════════════════════════════════════════════════════════════════
        # БЛОК E — ПОВЕДЕНЧЕСКИЕ ПАТТЕРНЫ И МЕТАДАННЫЕ (критерии 56–60)
        # ══════════════════════════════════════════════════════════════════════

        # ── КРИТЕРИЙ 56: Дата публикации в тексте ────────────────────────────
        pub_dates = len(re.findall(
            r'\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b'
            r'|\b\d{4}-\d{2}-\d{2}\b'
            r'|\b\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}\b'
            r'|\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            text, re.I))
        checks["pub_dates"] = pub_dates
        criteria["C56_dates"] = {"count": pub_dates}
        if pub_dates >= 1:
            score += 5; positives.append("Конкретные даты в тексте" if lang=="ru"
                                          else "Specific publication dates present")

        # ── КРИТЕРИЙ 57: Эффект срочности + социальное давление ──────────────
        social_pressure = len(re.findall(
            r'\b(все уже знают|весь мир обсуждает|миллионы людей|вирусный пост|'
            r'everyone already knows|the whole world is discussing|millions of people|viral post|'
            r'alle wissen bereits|die ganze Welt diskutiert|Millionen Menschen|'
            r'tout le monde sait déjà|le monde entier en parle|des millions de personnes|'
            r'todo el mundo ya sabe|el mundo entero habla|millones de personas)\b', full, re.I))
        checks["social_pressure"] = social_pressure
        criteria["C57_social_pressure"] = {"count": social_pressure}
        if social_pressure >= 2:
            score -= 14; issues.append("Социальное давление ('все уже знают')" if lang=="ru"
                                        else "Social pressure tactics ('everyone knows')")
        elif social_pressure >= 1:
            score -= 6

        # ── КРИТЕРИЙ 58: Нарратив «скрытого знания» ──────────────────────────
        hidden_knowledge = len(re.findall(
            r'\b(то, что скрывают|правда которую|что не хотят чтобы ты знал|'
            r'what they.re hiding|the truth they don.t want you to know|'
            r'was sie verbergen|die Wahrheit die sie|'
            r'ce qu.ils cachent|la vérité qu.ils|'
            r'lo que ocultan|la verdad que no quieren)\b', full, re.I))
        checks["hidden_knowledge"] = hidden_knowledge
        criteria["C58_hidden_knowledge"] = {"count": hidden_knowledge}
        if hidden_knowledge >= 1:
            score -= 18; issues.append("Нарратив 'скрытого знания' — классика фейков" if lang=="ru"
                                        else "Hidden knowledge narrative — classic fake-news pattern")

        # ── КРИТЕРИЙ 59: Академические индикаторы ────────────────────────────
        academic = len(re.findall(
            r'\b(исследование показало|согласно исследованию|по данным исследования|'
            r'study shows|research indicates|according to the study|survey found|'
            r'Studie zeigt|Forschung zeigt|gemäß der Studie|'
            r'l.étude montre|selon l.étude|la recherche indique|'
            r'el estudio muestra|según el estudio|la investigación indica)\b', full, re.I))
        checks["academic"] = academic
        criteria["C59_academic"] = {"count": academic}
        if academic >= 2:
            score += 8; positives.append("Ссылки на исследования/данные" if lang=="ru"
                                          else "Research/study references")
        elif academic >= 1:
            score += 4

        # ── КРИТЕРИЙ 60: Итоговый бонус за общую качественность ──────────────
        quality_signals = sum([
            named >= 2,           # есть конкретные люди
            qt >= 2,              # есть цитаты
            wc >= 200,            # длинный текст
            fh >= 3,              # есть ссылки на источники
            action_verbs >= 2,    # журналистские глаголы
            pub_dates >= 1,       # даты
            paragraphs >= 3,      # структура
            stats >= 1,           # статистика
        ])
        criteria["C60_quality_bonus"] = {"signals": quality_signals}
        if quality_signals >= 6:
            score += 12; positives.append("Высокое качество текста (6+ признаков)" if lang=="ru"
                                           else "High text quality (6+ professional signals)")
        elif quality_signals >= 4:
            score += 6
        elif quality_signals >= 2:
            score += 2

        # Штраф за накопленные красные флаги
        red_count = len(issues)
        if red_count >= 8:
            score -= 10  # дополнительный штраф за множество нарушений
        elif red_count >= 5:
            score -= 5

        # ── Финальный балл ────────────────────────────────────────────────────
        score = max(0, min(100, score))
        return {
            "score": score,
            "verdict": self._v(score, lang),
            "issues": issues,
            "positives": positives,
            "checks": checks,
            "criteria_detail": criteria,
            "criteria_count": 60,
            "red_flags_count": len(issues),
            "green_signals_count": len(positives),
        }

    def _v(self, s: int, lang: str) -> str:
        if s >= 78: return tr(lang, "text_quality")
        if s >= 58: return tr(lang, "minor_manipulation")
        if s >= 35: return tr(lang, "many_manipulation")
        return tr(lang, "likely_disinfo")


# ═══════════════════════════════════════════════════════════════════════════════
# NEWS SEARCHER
# ═══════════════════════════════════════════════════════════════════════════════
class NewsSearcher:
    def _get(self, url: str, timeout: int = 8) -> bytes | None:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception:
            return None

    def fetch_rss(self, feed_url: str, feed_name: str) -> list:
        raw = self._get(feed_url)
        if not raw: return []
        articles = []
        try:
            text = raw.decode('utf-8', errors='replace')
            text = re.sub(r' xmlns[^=]*="[^"]*"', '', text)
            text = re.sub(r'<[a-z]+:([^>]+)>', r'<\1>', text)
            root = ET.fromstring(text)
            items = root.findall('.//item') or root.findall('.//entry')
            for item in items[:6]:
                title_el = item.find('title')
                title = (title_el.text or '').strip() if title_el is not None else ''
                title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title, flags=re.DOTALL)
                title = re.sub(r'<[^>]+>', '', title).strip()
                link_el = item.find('link')
                link = ''
                if link_el is not None:
                    link = (link_el.text or link_el.get('href', '') or '').strip()
                desc_el = item.find('description') or item.find('summary')
                desc = ''
                if desc_el is not None and desc_el.text:
                    desc = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', desc_el.text, flags=re.DOTALL)
                    desc = re.sub(r'<[^>]+>', '', desc).strip()[:300]
                date_el = item.find('pubDate') or item.find('published') or item.find('updated')
                pub = (date_el.text or '').strip() if date_el is not None else ''
                if title and link:
                    articles.append({"title": title, "url": link, "source": feed_name,
                                     "description": desc, "published": pub})
        except Exception:
            pass
        return articles

    def get_trending(self, lang: str = None) -> list:
        feeds = RSS_FEEDS if not lang else \
            [f for f in RSS_FEEDS if f.get("lang") == lang] + \
            [f for f in RSS_FEEDS if f.get("lang") != lang]
        all_articles = []
        for feed in feeds[:16]:
            arts = self.fetch_rss(feed["url"], feed["name"])
            if arts: all_articles.append(arts[0])
            time.sleep(0.04)
        return all_articles

    def search(self, query: str) -> list:
        stop = {
            "и","в","на","с","по","за","от","до","как","что","это","не","но","или",
            "же","бы","ли","уже","ещё","так","при","а","о","из","у","к","то",
            "the","a","an","in","on","at","for","of","to","and","or","is","are",
            "was","were","has","have","this","that","with","from","by","be","it",
            "der","die","das","ein","eine","und","oder","ist","sind","war","avec",
            "les","des","une","qui","que","est","sur","par","el","la","los","las",
            "un","una","del","por","que","con","como","para","pero","hay",
        }
        qw = {w for w in re.sub(r'[^\w\s]', '', query.lower()).split()
              if w not in stop and len(w) > 3}
        if not qw: return []
        found = []
        for feed in RSS_FEEDS:
            for art in self.fetch_rss(feed["url"], feed["name"]):
                awt = (art["title"] + " " + art.get("description", "")).lower()
                aw = set(re.sub(r'[^\w\s]', '', awt).split())
                overlap = qw & aw
                if qw and len(overlap) / len(qw) >= 0.22:
                    art["similarity"] = round(len(overlap) / len(qw), 2)
                    found.append(art)
            time.sleep(0.03)
        found.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return found[:12]

    def search_duckduckgo(self, query: str) -> list:
        params = urllib.parse.urlencode({"q": query, "format": "json",
                                         "no_html": "1", "skip_disambig": "1"})
        try:
            req = urllib.request.Request(DDG_API_URL + "?" + params, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode('utf-8'))
        except Exception:
            return []
        results = []
        if data.get("AbstractText"):
            results.append({"title": data.get("Heading", query),
                            "url": data.get("AbstractURL", ""),
                            "source": data.get("AbstractSource", "DuckDuckGo"),
                            "description": data["AbstractText"][:300], "published": ""})
        for tp in data.get("RelatedTopics", [])[:4]:
            if isinstance(tp, dict) and tp.get("Text") and tp.get("FirstURL"):
                results.append({"title": tp["Text"][:120], "url": tp["FirstURL"],
                                "source": "DuckDuckGo", "description": tp["Text"][:250], "published": ""})
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# CROSS-REFERENCE ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════
class CrossRefAnalyzer:
    def __init__(self):
        self.searcher = NewsSearcher()

    def _keywords(self, title: str, text: str) -> str:
        stop = {
            "и","в","на","с","по","за","от","до","как","что","это","не","но","или",
            "же","бы","ли","уже","ещё","так","при","а","о","из",
            "the","a","an","in","on","at","for","of","to","and","or","is","are",
            "was","were","has","have","this","that","with","from","by",
        }
        words = re.sub(r'[^\w\s]', ' ', f"{title} {text[:300]}").split()
        kw = [w for w in words if w.lower() not in stop and len(w) > 3]
        return ' '.join(kw[:10])

    def _wiki(self, query: str, lang: str = "ru") -> dict | None:
        wiki_url  = WIKI_APIS.get(lang, WIKI_APIS["en"])
        wiki_base = f"https://{lang}.wikipedia.org/wiki/"
        try:
            params = urllib.parse.urlencode({"action": "query", "list": "search",
                                             "srsearch": query, "format": "json",
                                             "srlimit": "1", "srprop": "snippet"})
            req = urllib.request.Request(wiki_url + "?" + params, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode('utf-8'))
            hits = data.get("query", {}).get("search", [])
            if not hits: return None
            tp = hits[0].get("title", "")
            sn = html_module.unescape(re.sub(r'<[^>]+>', '', hits[0].get("snippet", "")))
            return {"title": tp, "snippet": sn[:300], "url": wiki_base + urllib.parse.quote(tp)}
        except Exception:
            return None

    def analyze(self, title: str, text: str, lang: str = "ru") -> dict:
        query = self._keywords(title, text) or title[:60]
        rss  = self.searcher.search(query)
        ddg  = self.searcher.search_duckduckgo(query)
        wiki = self._wiki(query, lang)
        if not wiki and lang != "en":
            wiki = self._wiki(query, "en")

        all_src, seen = [], set()
        for art in rss + ddg:
            u = art.get("url", "")
            if u and u not in seen:
                seen.add(u)
                dom = re.sub(r'^https?://(www\.)?', '', u).split('/')[0].lower()
                art["trusted"]    = any(dom == t2 or dom.endswith('.' + t2) for t2 in TRUSTED_SOURCES)
                art["suspicious"] = any(dom == s or dom.endswith('.' + s) for s in SUSPICIOUS_SOURCES)
                all_src.append(art)

        tc = sum(1 for s in all_src if s.get("trusted"))
        sc = sum(1 for s in all_src if s.get("suspicious"))
        total = len(all_src)

        if total == 0 and not wiki:
            score, verdict = 28, tr(lang, "no_confirmations")
            explanation = tr(lang, "no_other_sources")
        elif tc >= 4:
            score, verdict = 92, tr(lang, "confirmed_by", n=tc)
            explanation = tr(lang, "confirmed_many", n=tc)
        elif tc >= 2:
            score, verdict = 75, tr(lang, "confirmed_by", n=tc)
            explanation = tr(lang, "confirmed_several")
        elif tc == 1:
            score, verdict = 60, tr(lang, "one_reliable")
            explanation = tr(lang, "one_source_covers")
        elif sc > 0 and tc == 0:
            score, verdict = 18, tr(lang, "only_suspicious")
            explanation = tr(lang, "only_unreliable")
        elif total >= 3:
            score, verdict = 50, tr(lang, "sources_found", n=total)
            explanation = tr(lang, "topic_exists")
        else:
            score, verdict = 38, tr(lang, "few_confirmations")
            explanation = tr(lang, "very_few_sources")

        if wiki: score = min(95, score + 7)
        return {"score": score, "verdict": verdict, "explanation": explanation,
                "sources": all_src[:10], "trusted_count": tc, "suspicious_count": sc,
                "total_found": total, "wiki": wiki, "query_used": query}


# ═══════════════════════════════════════════════════════════════════════════════
# FACT CHECKER
# ═══════════════════════════════════════════════════════════════════════════════
class FactChecker:
    def _fetch_wiki(self, entity: str, lang: str = "ru") -> dict | None:
        wiki_url  = WIKI_APIS.get(lang, WIKI_APIS["en"])
        wiki_base = f"https://{lang}.wikipedia.org/wiki/"
        try:
            params = urllib.parse.urlencode({"action": "query", "titles": entity,
                                             "format": "json", "prop": "extracts",
                                             "exintro": True, "exchars": 500, "redirects": 1})
            req = urllib.request.Request(wiki_url + "?" + params, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode('utf-8'))
            for pid, page in data.get("query", {}).get("pages", {}).items():
                if pid == "-1": return None
                ext = re.sub(r'<[^>]+>', '', page.get("extract", "")).strip()
                return {"found": True, "title": page.get("title", entity),
                        "extract": ext[:400], "url": wiki_base + urllib.parse.quote(page.get('title', ''))}
        except Exception:
            return None

    def extract_entities(self, title: str, text: str) -> dict:
        full = f"{title} {text}"
        ru_ppl = list(set(re.findall(r'\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?\b', full)))[:4]
        en_ppl = list(set(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', full)))[:4]
        orgs   = list(set(re.findall(r'«([^»]{3,40})»', full)))[:4]
        nums   = list(set(re.findall(
            r'\d+[.,]?\d*\s*(?:млн|млрд|тыс\.?|%|₽|\$|€|million|billion|thousand|percent)',
            full, re.I)))[:5]
        return {"people": (ru_ppl + en_ppl)[:5], "orgs": orgs, "numbers": nums}

    def analyze(self, title: str, text: str, lang: str = "ru") -> dict:
        entities = self.extract_entities(title, text)
        wiki_checks, verified = [], []
        for person in entities["people"][:3]:
            result = self._fetch_wiki(person, lang)
            if not result and lang != "en":
                result = self._fetch_wiki(person, "en")
            if result:
                verified.append(person)
                wiki_checks.append({"entity": person, **result})

        full = f"{title} {text}".lower()
        inconsistencies = []
        for pair in [("все знают", "никто не знает"), ("everyone knows", "nobody knows")]:
            if pair[0] in full and pair[1] in full:
                inconsistencies.append("Internal contradiction in text")

        anon_pats = [
            r'эксперты говорят', r'учёные выяснили', r'источники сообщают',
            r'experts say', r'scientists claim', r'sources report',
            r'insiders reveal', r'anonymous sources',
        ]
        anon = sum(1 for p in anon_pats if re.search(p, full))
        if anon >= 2:
            inconsistencies.append(f"Anonymous experts without names ({anon})")

        bonus = len(verified) * 5 - len(inconsistencies) * 10
        return {"entities": entities, "verified": verified, "wiki_checks": wiki_checks,
                "inconsistencies": inconsistencies, "score_bonus": max(-20, min(15, bonus))}


# ═══════════════════════════════════════════════════════════════════════════════
# DEEP ANALYZER — Chain-of-Thought (локальный, без API)
# ═══════════════════════════════════════════════════════════════════════════════
class DeepAnalyzer:
    FAKE_VOCAB = {
        "скрывают от нас":3,"тайные элиты":3,"чипирован":3,"глубинное государство":3,
        "пока не удалили":4,"мировое правительство":3,"заговор":3,"масоны":3,
        "апокалипсис":2,"конец света":2,"шок":2,"сенсация":2,"паника":1,
        "deep state":3,"shadow government":3,"plandemic":4,"hoax":3,
        "false flag":3,"crisis actor":3,"new world order":3,"chemtrails":3,
        "conspiracy":2,"bombshell":2,"shocking":2,"apocalypse":2,
        "Verschwörung":3,"Weltregierung":3,"Tiefenstaat":3,
        "complot":3,"gouvernement mondial":3,"état profond":3,
        "conspiración":3,"gobierno mundial":3,
    }
    REAL_VOCAB = {
        "по данным":3,"согласно":3,"по словам":3,"подтвердил":3,"официально":3,
        "сообщает":2,"заявил":2,"исследование":2,"млн":2,"млрд":2,
        "according to":3,"confirmed by":3,"officials said":3,"study found":3,
        "data shows":3,"spokesperson":2,"million":2,"billion":2,
        "laut":3,"bestätigte":3,"erklärte":2,"Millionen":2,
        "selon":3,"a confirmé":3,"millions":2,"a déclaré":2,
        "según":3,"confirmó":3,"declaró":2,"millones":2,
    }

    def _vocab(self, text: str):
        tl = text.lower()
        fs = sum(w for k, w in self.FAKE_VOCAB.items() if k in tl)
        rs = sum(w for k, w in self.REAL_VOCAB.items() if k in tl)
        fh = [k for k in self.FAKE_VOCAB if k in tl]
        rh = [k for k in self.REAL_VOCAB if k in tl]
        return fs, rs, fh, rh

    def analyze(self, title: str, text: str, source_r: dict, text_r: dict,
                crossref_r: dict, fact_r: dict, bert_r: dict, groq_r: dict | None,
                lang: str = "ru") -> dict:
        full = f"{title} {text}"
        fs, rs, fh, rh = self._vocab(full)

        # Базовый score из локального CoT
        total_v = fs + rs + 1
        vocab_trust = round(rs / total_v * 100)
        local_score = round(
            vocab_trust                 * 0.25 +
            source_r.get('score', 50)   * 0.20 +
            crossref_r.get('score', 50) * 0.30 +
            text_r.get('score', 50)     * 0.25
        )
        local_score += fact_r.get('score_bonus', 0)

        # Включаем BERT если доступен
        final_score = local_score
        if bert_r.get("available"):
            final_score = round(local_score * 0.55 + bert_r["score"] * 0.45)

        # Включаем Groq если доступен (самый умный)
        if groq_r and groq_r.get("ai_powered"):
            final_score = round(final_score * 0.40 + groq_r["score"] * 0.60)

        final_score = max(0, min(100, final_score))

        # Thinking
        thinking = self._build_thinking(
            title, text, source_r, text_r, crossref_r, fact_r,
            bert_r, groq_r, fs, rs, fh, rh, lang)

        # Red flags & positive signs
        red_flags = list(text_r.get('issues', []))
        positive_signs = list(text_r.get('positives', []))
        domain = source_r.get('domain', '')

        if crossref_r.get('total_found', 0) == 0:
            red_flags.append("No other media covering this story" if lang == "en"
                             else "Другие СМИ эту новость не публикуют")
        if source_r.get('tier') == 'suspicious':
            red_flags.append(f"{'Blacklisted source' if lang=='en' else 'Источник в чёрном списке'}: {domain}")
        for ic in fact_r.get('inconsistencies', []):
            red_flags.append(ic)
        if groq_r and groq_r.get("fake_signals"):
            red_flags.extend(groq_r["fake_signals"][:2])

        if source_r.get('tier') == 'trusted':
            positive_signs.append(f"{'Authoritative source' if lang=='en' else 'Авторитетный источник'}: {domain}")
        if crossref_r.get('trusted_count', 0) >= 2:
            n = crossref_r['trusted_count']
            positive_signs.append(f"{n} {'reliable sources confirm' if lang=='en' else 'надёжных источника подтверждают'}")
        if bert_r.get("available"):
            lbl = tr(lang, "bert_real") if bert_r.get("label") == "REAL" else tr(lang, "bert_fake")
            positive_signs.append(f"{lbl} ({bert_r.get('score',50)}%)")
        if groq_r and groq_r.get("credibility_signals"):
            positive_signs.extend(groq_r["credibility_signals"][:2])

        explanation = self._explanation(final_score, source_r, crossref_r, red_flags,
                                        bert_r, groq_r, lang)

        what_to_check = [tr(lang, "google_query", q=title[:55]),
                         tr(lang, "check_date"), tr(lang, "find_original")]
        if crossref_r.get('total_found', 0) == 0:
            what_to_check.insert(0, tr(lang, "check_big_sources"))
        if source_r.get('tier') not in ('trusted',):
            what_to_check.insert(0, tr(lang, "find_authoritative", domain=domain))

        dp = ((2 if source_r.get('tier') in ('trusted', 'suspicious') else 0) +
              (2 if crossref_r.get('total_found', 0) > 0 else 0) +
              (1 if fact_r.get('verified') else 0) +
              (2 if bert_r.get('available') else 0) +
              (3 if groq_r and groq_r.get('ai_powered') else 0))
        confidence = (tr(lang, "confidence_high") if dp >= 6 else
                      (tr(lang, "confidence_medium") if dp >= 3 else tr(lang, "confidence_low")))

        models_used = []
        if bert_r.get("available"): models_used.append("FakeScope BERT")
        if groq_r and groq_r.get("ai_powered"): models_used.append(f"Groq {GROQ_MODEL}")
        if not models_used: models_used.append("Local CoT")
        model_label = " + ".join(models_used)

        return {
            "available": True, "score": final_score,
            "fake_probability": 100 - final_score,
            "verdict": self._verdict(final_score, lang),
            "thinking": thinking,
            "red_flags": red_flags[:6],
            "positive_signs": positive_signs[:5],
            "explanation": explanation,
            "what_to_check": what_to_check[:4],
            "confidence": confidence,
            "model": model_label,
            "scores_breakdown": {
                "local_cot": local_score,
                "bert": bert_r.get("score", "N/A") if bert_r.get("available") else "N/A",
                "groq": groq_r.get("score", "N/A") if groq_r else "N/A",
                "final": final_score,
            }
        }

    def _build_thinking(self, title, text, source_r, text_r, crossref_r,
                        fact_r, bert_r, groq_r, fs, rs, fh, rh, lang):
        lines = []
        domain = source_r.get('domain', '—')
        tier   = source_r.get('tier', 'unknown')
        tc     = crossref_r.get('trusted_count', 0)
        tf     = crossref_r.get('total_found', 0)
        checks = text_r.get('checks', {})
        issues = text_r.get('issues', [])
        src_list = crossref_r.get('sources', [])

        en = lang == "en"

        lines.append("【Step 1 — Source】" if en else "【Шаг 1 — Источник】")
        if tier == 'trusted':
            lines.append(f"{'Domain' if en else 'Домен'} \"{domain}\" — {'trusted authoritative outlet' if en else 'авторитетное издание'} ({source_r.get('score',50)}/100).")
        elif tier == 'suspicious':
            lines.append(f"{'Domain' if en else 'Домен'} \"{domain}\" — {'known unreliable source' if en else 'известный ненадёжный источник'} ({source_r.get('score',50)}/100).")
        else:
            ai_note = f" {'(AI-assessed)' if en else '(оценён ИИ)'}" if source_r.get('ai_used') else ""
            lines.append(f"{'Domain' if en else 'Домен'} \"{domain}\"{ai_note} — {'unknown/regional source' if en else 'неизвестный/региональный источник'} ({source_r.get('score',50)}/100).")
        for det in source_r.get('details', []):
            if any(x in det for x in ['⚠️', '🚨', '🤖', '📍']):
                lines.append(f"  ➜ {det}")

        lines.append("\n【Step 2 — Language & Style】" if en else "\n【Шаг 2 — Язык и стиль】")
        if not issues:
            lines.append("Text written in neutral style. No manipulation detected." if en
                         else "Текст написан в нейтральном стиле. Манипуляций не обнаружено.")
        else:
            lines.append(f"{'Found' if en else 'Найдено'} {len(issues)} {'warning signs' if en else 'тревожных признаков'}: {'; '.join(issues[:4])}.")
        if rs > 0:
            lines.append(f"{'Credibility vocab' if en else 'Лексика достоверности'} ({rs} pts): {', '.join(rh[:3])}.")
        if fs > rs:
            lines.append(f"{'Manipulation vocab' if en else 'Манипулятивная лексика'} ({fs} pts) > {'credibility' if en else 'достоверность'} ({rs} pts): {', '.join(fh[:3])}.")

        lines.append("\n【Step 3 — Global Media】" if en else "\n【Шаг 3 — Мировые СМИ】")
        if tc >= 3:
            names = [s.get('source', '?') for s in src_list if s.get('trusted')][:3]
            lines.append(f"{'STRONG CONFIRMATION:' if en else 'СИЛЬНОЕ ПОДТВЕРЖДЕНИЕ:'} {tc} {'authoritative outlets' if en else 'авторитетных изданий'}: {', '.join(names)}.")
        elif tc >= 1:
            names = [s.get('source', '?') for s in src_list if s.get('trusted')][:2]
            lines.append(f"{'Partial confirmation:' if en else 'Частичное подтверждение:'} {', '.join(names)}.")
        elif tf == 0:
            lines.append("CRITICAL: " + ("Zero outlets cover this. Strong fake indicator." if en
                          else "Ни одно СМИ не публикует. Сильнейший признак фейка."))
        else:
            lines.append(f"{tf} {'sources found, none authoritative.' if en else 'источников, ни один не авторитетный.'}")

        lines.append("\n【Step 4 — BERT AI】" if en else "\n【Шаг 4 — BERT нейросеть】")
        if bert_r.get("available"):
            lbl = bert_r.get("label", "?")
            conf = bert_r.get("confidence", bert_r.get("score", 50))
            lines.append(f"{'FakeScope BERT model (trained on LIAR+FakeScope-RU, 71.2% accuracy):' if en else 'Модель FakeScope BERT (обучена на LIAR+FakeScope-RU, точность 71.2%):'}")
            lines.append(f"  → Prediction: {lbl} (confidence: {conf}%)")
        else:
            lines.append("BERT model not loaded. " + ("Install transformers + model files." if en
                          else "Установите transformers + файлы модели."))

        lines.append("\n【Step 5 — Groq AI Deep Analysis】" if en else "\n【Шаг 5 — Глубокий анализ Groq AI】")
        if groq_r and groq_r.get("ai_powered"):
            lines.append(f"Groq {GROQ_MODEL}: score {groq_r.get('score','?')}/100")
            lines.append(f"  Verdict: {groq_r.get('verdict','')}")
            lines.append(f"  Manipulation type: {groq_r.get('manipulation_type','none')}")
            if groq_r.get("explanation"):
                lines.append(f"  Analysis: {groq_r['explanation'][:300]}")
        else:
            lines.append("Groq AI not active. " + ("Set GROQ_API_KEY for enhanced analysis." if en
                          else "Укажите GROQ_API_KEY для улучшенного анализа."))

        lines.append("\n【Step 6 — Final Judgement】" if en else "\n【Шаг 6 — Итоговое суждение】")
        pro, anti = [], []
        if tier == 'trusted': pro.append(f"{'trusted source' if en else 'авторитетный источник'} \"{domain}\"")
        if tier == 'suspicious': anti.append(f"{'unreliable source' if en else 'ненадёжный источник'} \"{domain}\"")
        if tc >= 2: pro.append(f"{tc} {'independent confirmations' if en else 'независимых подтверждения'}")
        if tf == 0: anti.append("no media coverage" if en else "нет подтверждений в СМИ")
        if checks.get('clickbait'): anti.append("clickbait" if en else "кликбейт")
        if checks.get('conspiracy'): anti.append("conspiracy narratives" if en else "конспирологические нарративы")
        if bert_r.get("available") and bert_r.get("label") == "REAL": pro.append(f"BERT→REAL({bert_r.get('confidence',50)}%)")
        if bert_r.get("available") and bert_r.get("label") == "FAKE": anti.append(f"BERT→FAKE({bert_r.get('confidence',50)}%)")
        if groq_r and groq_r.get("score", 50) >= 65: pro.append(f"Groq→{groq_r['score']}/100")
        if groq_r and groq_r.get("score", 50) < 45: anti.append(f"Groq→{groq_r.get('score',0)}/100")
        if pro:  lines.append(f"{'FOR credibility' if en else 'ЗА достоверность'}: {', '.join(pro)}.")
        if anti: lines.append(f"{'AGAINST' if en else 'ПРОТИВ'}: {', '.join(anti)}.")

        return "\n".join(lines)

    def _explanation(self, score, source_r, crossref_r, red_flags, bert_r, groq_r, lang):
        en = lang == "en"
        parts = []

        # Groq explanation приоритетнее
        if groq_r and groq_r.get("explanation"):
            parts.append(groq_r["explanation"])
        else:
            if score >= 80:
                parts.append("The news passes all key credibility checks." if en
                             else "Новость проходит все основные проверки достоверности.")
            elif score >= 65:
                parts.append("Likely credible with minor concerns." if en
                             else "Новость вероятно достоверна, есть незначительные замечания.")
            elif score >= 50:
                parts.append("Suspicious signals — verify in other sources." if en
                             else "Подозрительные признаки — требует проверки.")
            elif score >= 35:
                parts.append("Multiple signs of non-credibility." if en
                             else "Множество признаков недостоверности.")
            else:
                parts.append("High probability of fake or manipulation." if en
                             else "Высокая вероятность фейка или манипуляции.")

        if bert_r.get("available"):
            lbl = "REAL" if bert_r.get("label") == "REAL" else "FAKE"
            parts.append(f"FakeScope BERT → {lbl} ({bert_r.get('confidence', bert_r.get('score',50))}%).")

        tc, tf = crossref_r.get('trusted_count', 0), crossref_r.get('total_found', 0)
        if tc >= 2:
            parts.append(f"{'Confirmed by' if en else 'Подтверждено'} {tc} {'authoritative outlets.' if en else 'авторитетными изданиями.'}")
        elif tf == 0:
            parts.append("No other outlet is publishing this story." if en
                         else "Другие издания эту новость не публикуют.")

        if red_flags:
            lbl = "Main issues" if en else "Главные проблемы"
            parts.append(f"{lbl}: {'; '.join(red_flags[:2])}.")

        if groq_r and groq_r.get("recommendation"):
            parts.append(groq_r["recommendation"])

        return " ".join(parts)

    def _verdict(self, s: int, lang: str) -> str:
        if s >= 80: return tr(lang, "verdict_reliable")
        if s >= 60: return tr(lang, "verdict_check")
        if s >= 40: return tr(lang, "verdict_manipulation")
        return tr(lang, "verdict_disinfo")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════
class FakeNewsDetector:
    def __init__(self):
        self.source_analyzer = SourceAnalyzer()
        self.text_analyzer   = TextAnalyzer()
        self.news_searcher   = NewsSearcher()
        self.crossref        = CrossRefAnalyzer()
        self.fact_checker    = FactChecker()
        self.deep_analyzer   = DeepAnalyzer()
        self.bert            = BERTAnalyzer()

    def analyze(self, title: str, text: str, url: str = "", lang: str = "ru") -> dict:
        if lang not in SUPPORTED_LANGS:
            lang = "en"
        if not title and not text:
            return {"error": "Please provide title or text / Укажите заголовок или текст"}
        if not url:
            return {"error": "Source URL required / URL источника обязателен"}
        title, text, url = title.strip(), text.strip(), url.strip()
        start = time.time()

        source_r   = self.source_analyzer.analyze(url, lang)
        text_r     = self.text_analyzer.analyze(title, text, lang)
        crossref_r = self.crossref.analyze(title, text, lang)
        fact_r     = self.fact_checker.analyze(title, text, lang)
        bert_r     = self.bert.analyze(title, text)

        # Groq deep analysis (если ключ задан)
        groq_r = None
        if GROQ_API_KEY:
            groq_r = groq_deep_analyze(title, text, source_r, crossref_r, bert_r, lang)

        deep_r = self.deep_analyzer.analyze(
            title, text, source_r, text_r, crossref_r, fact_r, bert_r, groq_r, lang)

        final = deep_r["score"]
        trust_level, trust_color, trust_emoji = self._trust(final, lang)

        return {
            "title": title, "url": url,
            "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "analysis_time": round(time.time() - start, 1),
            "final_score": final,
            "trust_level": trust_level, "trust_color": trust_color, "trust_emoji": trust_emoji,
            "explanation": deep_r.get("explanation", ""),
            "source": source_r, "text": text_r, "crossref": crossref_r,
            "factcheck": fact_r, "bert": bert_r, "deep": deep_r,
            "hash": hashlib.md5(f"{title}{url}".encode()).hexdigest()[:8],
            "lang": lang,
            "models_used": deep_r.get("model", ""),
            "scores_breakdown": deep_r.get("scores_breakdown", {}),
        }

    def _trust(self, s: int, lang: str):
        if s >= 80: return tr(lang, "reliable"),          "#10b981", "✅"
        if s >= 65: return tr(lang, "likely_reliable_lv"),"#84cc16", "🟡"
        if s >= 50: return tr(lang, "check_required"),    "#f59e0b", "⚠️"
        if s >= 35: return tr(lang, "suspicious"),        "#f97316", "🚨"
        return           tr(lang, "likely_fake"),         "#ef4444", "🔴"


# ═══════════════════════════════════════════════════════════════════════════════
# SELF TEST
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    d = FakeNewsDetector()
    tests = [
        ("ШОК!!! УЧЁНЫЕ СКРЫВАЮТ ПРАВДУ!!!",
         "Правительство скрывает! Тайные элиты чипируют. Поделитесь пока не удалили!",
         "http://fakesite123.tk/vakziny", "ru"),
        ("BREAKING: Deep state exposed!!!",
         "Shadow government elites are microchipping people. Share before deleted!",
         "http://infowars.com/vaccines", "en"),
        ("UN Security Council holds emergency Gaza session",
         "According to Reuters, the Security Council convened Monday to discuss ceasefire. Officials confirmed 12 of 15 members attended.",
         "https://reuters.com/world/un-session", "en"),
        ("Тенгри: Президент Казахстана подписал новый закон",
         "По данным tengrinews.kz, президент Казахстана подписал закон об образовании. Министерство образования подтвердило вступление в силу.",
         "https://tengrinews.kz/news/12345", "ru"),
    ]
    for title, text, url, lang in tests:
        r = d.analyze(title=title, text=text, url=url, lang=lang)
        print(f"\n{r['trust_emoji']} [{lang.upper()}] {r['final_score']}/100 — {r['trust_level']}")
        print(f"   Models: {r.get('models_used','')}")
        print(f"   Breakdown: {r.get('scores_breakdown','')}")
        print(f"   {r['explanation'][:120]}")
