#!/usr/bin/env python3
"""
generate_premium_report.py — Premium co-branded GEO audit PDF report (v2).

Redesigned for dense, professional layout:
- 2-column cover with gauge + highlights
- No aggressive page breaks — content flows naturally
- Rich auto-generated executive summary
- Findings with business impact explanations
- Action items with effort + score impact estimates
- Score Improvement Forecast section
- Tighter spacing throughout
- Dark mode support (--dark flag)

Usage:
    python3 generate_premium_report.py <json_data> [output.pdf] [options]
    python3 generate_premium_report.py data.json report.pdf --client-url https://example.com
    python3 generate_premium_report.py data.json report.pdf --client-color "#2563eb"
    python3 generate_premium_report.py data.json report.pdf --consultant-name "My Brand"
    python3 generate_premium_report.py data.json report.pdf --dark

Options:
    --client-url URL         Extract brand colors from client website
    --client-color HEX       Override client primary color
    --consultant-name NAME   Your brand name for co-branding
    --consultant-color HEX   Override consultant primary color
    --dark                   Dark mode report (dark background, light text)
"""
import sys, json, os, re, urllib.request
from datetime import datetime
from colorsys import rgb_to_hls, hls_to_rgb

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, white, lightgrey, Color
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
        TableStyle, PageBreak, HRFlowable, KeepTogether, Flowable)
    from reportlab.graphics.shapes import Drawing, Rect, String, Circle
    from reportlab.graphics.charts.barcharts import VerticalBarChart
except ImportError:
    print("ERROR: pip install reportlab"); sys.exit(1)


# ════════════════════════════════════════════════════════════════
# BRAND COLOR EXTRACTION
# ════════════════════════════════════════════════════════════════
def extract_brand_colors(url):
    if not url: return None
    if not url.startswith("http"): url = "https://" + url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; GEOPremium/1.0)"})
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="ignore")[:100000]
    except Exception as e:
        print(f"  Could not fetch {url}: {e}", file=sys.stderr); return None
    colors = []
    m = re.search(r'<meta[^>]*name=["\']theme-color["\'][^>]*content=["\']([^"\']+)', html, re.I)
    if not m: m = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']theme-color', html, re.I)
    if m: colors.append(("theme", m.group(1).strip()))
    for pat in [r'--(?:primary|brand|main)[-_]?color\s*:\s*([^;}\s]+)',
                r'--(?:primary|brand|main)\s*:\s*([^;}\s]+)']:
        m = re.search(pat, html, re.I)
        if m: colors.append(("css-var", m.group(1).strip()))
    m = re.search(r'<(?:header|nav)[^>]*style=["\'][^"\']*background(?:-color)?\s*:\s*([^;"\'\s]+)', html, re.I)
    if m: colors.append(("header-bg", m.group(1).strip()))
    all_hex = re.findall(r'#([0-9a-fA-F]{6})\b', html)
    skip = {"000000","ffffff","f5f5f5","e5e5e5","cccccc","333333","666666","999999","eeeeee","f0f0f0","f8f8f8","fafafa"}
    counts = {}
    for h in all_hex:
        hl = h.lower()
        if hl not in skip: counts[hl] = counts.get(hl, 0) + 1
    if counts:
        top = max(counts, key=counts.get)
        if counts[top] >= 3: colors.append(("freq", f"#{top}"))
    for src, val in colors:
        hx = _norm(val)
        if hx: print(f"  Brand color ({src}): {hx}", file=sys.stderr); return hx
    return None

def _norm(s):
    s = s.strip().lower()
    if re.match(r'^#[0-9a-f]{6}$', s): return s
    if re.match(r'^#[0-9a-f]{3}$', s): return f"#{s[1]*2}{s[2]*2}{s[3]*2}"
    m = re.match(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', s)
    if m: return f"#{int(m.group(1)):02x}{int(m.group(2)):02x}{int(m.group(3)):02x}"
    return None


# ════════════════════════════════════════════════════════════════
# COLOR UTILS
# ════════════════════════════════════════════════════════════════
def hex2rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
def rgb2hex(r, g, b): return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
def lighten(h, a=0.3):
    r, g, b = hex2rgb(h); h2, l, s = rgb_to_hls(r, g, b); l = min(1, l + a)
    return rgb2hex(*hls_to_rgb(h2, l, s))
def darken(h, a=0.15):
    r, g, b = hex2rgb(h); h2, l, s = rgb_to_hls(r, g, b); l = max(0, l - a)
    return rgb2hex(*hls_to_rgb(h2, l, s))
def is_light(h): r, g, b = hex2rgb(h); return 0.299*r + 0.587*g + 0.114*b > 0.5

def build_theme(cp=None, rp=None, dark_mode=False):
    cp = cp or "#2563eb"; rp = rp or "#1a1a2e"
    if not dark_mode:
        return {
            "client": {"primary": cp, "dark": darken(cp, 0.2), "light": lighten(cp, 0.35),
                "bg": lighten(cp, 0.45), "text_on": "#ffffff" if not is_light(cp) else "#1a1a2e"},
            "consultant": {"primary": rp},
            "header": HexColor(rp), "accent": HexColor(cp),
            "accent_light": HexColor(lighten(cp, 0.35)), "accent_bg": HexColor(lighten(cp, 0.45)),
            "success": HexColor("#00b894"), "warning": HexColor("#fdcb6e"),
            "danger": HexColor("#d63031"), "info": HexColor(cp),
            "text": HexColor("#2d3436"), "text_light": HexColor("#636e72"),
            "bg_light": HexColor("#f8f9fa"), "bg_medium": HexColor("#e9ecef"),
            "white": white, "black": HexColor("#000000"),
            "dark_mode": False, "page_bg": None,
        }
    else:
        accent_bright = lighten(cp, 0.15)
        return {
            "client": {"primary": cp, "dark": darken(cp, 0.1), "light": lighten(cp, 0.2),
                "bg": "#1e2a3a", "text_on": "#ffffff"},
            "consultant": {"primary": "#e0e0e0"},
            "header": HexColor("#e8eaed"), "accent": HexColor(accent_bright),
            "accent_light": HexColor(lighten(cp, 0.1)), "accent_bg": HexColor("#1e2a3a"),
            "success": HexColor("#2ecc71"), "warning": HexColor("#f1c40f"),
            "danger": HexColor("#e74c3c"), "info": HexColor(accent_bright),
            "text": HexColor("#e8eaed"), "text_light": HexColor("#9ca3af"),
            "bg_light": HexColor("#1e2530"), "bg_medium": HexColor("#252d38"),
            "white": HexColor("#e8eaed"), "black": HexColor("#0d1117"),
            "dark_mode": True, "page_bg": HexColor("#0d1117"),
        }

def score_color(s, t):
    if s >= 80: return t["success"]
    elif s >= 60: return t["info"]
    elif s >= 40: return t["warning"]
    return t["danger"]

def score_label(s):
    if s >= 85: return "Excellent"
    elif s >= 70: return "Good"
    elif s >= 55: return "Moderate"
    elif s >= 40: return "Below Average"
    return "Needs Attention"


# ════════════════════════════════════════════════════════════════
# CHARTS
# ════════════════════════════════════════════════════════════════
def make_gauge(score, t, w=130, h=130):
    d = Drawing(w, h); cx, cy = w/2, h/2
    dark = t.get("dark_mode", False)
    ring_bg = HexColor("#1e2530") if dark else t["bg_light"]
    inner_bg = t.get("page_bg", t["white"]) if dark else t["white"]
    ring_stroke = HexColor(lighten(t["client"]["primary"], 0.1 if dark else 0.3))
    d.add(Circle(cx, cy, 48, fillColor=ring_bg, strokeColor=ring_stroke, strokeWidth=3))
    d.add(Circle(cx, cy, 42, fillColor=score_color(score, t), strokeColor=None))
    d.add(Circle(cx, cy, 32, fillColor=inner_bg, strokeColor=None))
    d.add(String(cx, cy+5, str(score), fontSize=24, fontName='Helvetica-Bold', fillColor=t["text"], textAnchor='middle'))
    d.add(String(cx, cy-10, "/100", fontSize=9, fontName='Helvetica', fillColor=t["text_light"], textAnchor='middle'))
    return d

def make_bars(data, labels, t, w=460, h=160):
    d = Drawing(w, h); dark = t.get("dark_mode", False)
    c = VerticalBarChart(); c.x=50; c.y=25; c.height=h-50; c.width=w-70
    c.data=[data]; c.categoryAxis.categoryNames=labels
    c.categoryAxis.labels.fontSize=7; c.categoryAxis.labels.fontName='Helvetica'
    c.valueAxis.valueMin=0; c.valueAxis.valueMax=100; c.valueAxis.valueStep=25; c.valueAxis.labels.fontSize=7
    if dark:
        c.categoryAxis.labels.fillColor=t["text_light"]; c.valueAxis.labels.fillColor=t["text_light"]
        c.categoryAxis.strokeColor=HexColor("#2d3748"); c.valueAxis.strokeColor=HexColor("#2d3748")
        c.valueAxis.gridStrokeColor=HexColor("#1e2530")
    for i, s in enumerate(data): c.bars[0].fillColor = score_color(s, t)
    c.bars[0].strokeColor=None; d.add(c); return d

def make_platform_chart(plats, t, w=470, h=150):
    d = Drawing(w, h); bh=18; bmax=220; sy=h-20
    insights = {"Google AI Overviews":"Largest reach (1.5B users/month)","ChatGPT":"900M+ weekly active users",
        "Perplexity":"500M+ monthly queries","Gemini":"Integrated with Google Search","Bing Copilot":"Powers Microsoft ecosystem"}
    for i, (nm, sc) in enumerate(plats.items()):
        y = sy - (i*(bh+8))
        d.add(String(5, y+4, nm, fontSize=8, fontName='Helvetica', fillColor=t["text"], textAnchor='start'))
        bx = 120; bar_bg = HexColor("#1e2530") if t.get("dark_mode") else t["bg_light"]
        d.add(Rect(bx, y, bmax, bh, fillColor=bar_bg, strokeColor=None))
        d.add(Rect(bx, y, (sc/100)*bmax, bh, fillColor=score_color(sc, t), strokeColor=None))
        d.add(String(bx+bmax+5, y+4, f"{sc}", fontSize=8, fontName='Helvetica-Bold', fillColor=t["text"], textAnchor='start'))
        hint = insights.get(nm, "")
        if hint: d.add(String(bx+bmax+25, y+4, hint, fontSize=7, fontName='Helvetica', fillColor=t["text_light"], textAnchor='start'))
    return d


# ════════════════════════════════════════════════════════════════
# STYLES
# ════════════════════════════════════════════════════════════════
def build_styles(t):
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle('RT', fontName='Helvetica-Bold', fontSize=26, textColor=t["header"], spaceAfter=12, leading=32))
    ss.add(ParagraphStyle('RS', fontName='Helvetica', fontSize=12, textColor=t["text_light"], spaceBefore=2, spaceAfter=14, leading=16))
    ss.add(ParagraphStyle('SH', fontName='Helvetica-Bold', fontSize=15, textColor=t["header"], spaceBefore=14, spaceAfter=6))
    ss.add(ParagraphStyle('SUB', fontName='Helvetica-Bold', fontSize=11, textColor=t["accent"], spaceBefore=10, spaceAfter=4))
    ss.add(ParagraphStyle('BD', fontName='Helvetica', fontSize=9.5, textColor=t["text"], spaceBefore=2, spaceAfter=3, leading=13, alignment=TA_JUSTIFY))
    ss.add(ParagraphStyle('SM', fontName='Helvetica', fontSize=7.5, textColor=t["text_light"], spaceBefore=1, spaceAfter=1))
    ss.add(ParagraphStyle('REC', fontName='Helvetica', fontSize=9.5, textColor=t["text"], leftIndent=12, spaceBefore=2, spaceAfter=2, leading=13))
    ss.add(ParagraphStyle('CB', fontName='Helvetica-Bold', fontSize=10, textColor=t["text_light"], alignment=TA_RIGHT))
    ss.add(ParagraphStyle('IMPACT', fontName='Helvetica-Oblique', fontSize=8.5, textColor=t["text_light"], leftIndent=12, spaceBefore=0, spaceAfter=4, leading=11))
    ss.add(ParagraphStyle('HIGHLIGHT', fontName='Helvetica', fontSize=9, textColor=t["text"], spaceBefore=2, spaceAfter=2, leading=12,
        backColor=t["bg_medium"] if t.get("dark_mode") else t["bg_light"], borderPadding=(6,8,6,8)))
    return ss

def make_ts(t):
    dark = t.get("dark_mode", False)
    header_bg = HexColor("#1e2a3a") if dark else t["header"]
    row_alt = HexColor("#151d27") if dark else t["bg_light"]
    row_base = HexColor("#0d1117") if dark else white
    grid_color = HexColor("#2d3748") if dark else lightgrey
    return TableStyle([
        ('BACKGROUND',(0,0),(-1,0),header_bg), ('TEXTCOLOR',(0,0),(-1,0),t["accent"] if dark else t["white"]),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'), ('FONTSIZE',(0,0),(-1,0),8),
        ('FONTNAME',(0,1),(-1,-1),'Helvetica'), ('FONTSIZE',(0,1),(-1,-1),8),
        ('TEXTCOLOR',(0,1),(-1,-1),t["text"]), ('ALIGN',(0,0),(-1,-1),'LEFT'), ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('GRID',(0,0),(-1,-1),0.5,grid_color), ('ROWBACKGROUNDS',(0,1),(-1,-1),[row_base,row_alt]),
        ('TOPPADDING',(0,0),(-1,-1),4), ('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),6), ('RIGHTPADDING',(0,0),(-1,-1),6)])


# ════════════════════════════════════════════════════════════════
# AUTO-GENERATED CONTENT
# ════════════════════════════════════════════════════════════════
FINDING_IMPACTS = {
    "no schema markup": "AI assistants cannot determine your business type, services, or hours. When users ask for recommendations in your category, you are invisible to AI — losing potential customers to competitors with structured data.",
    "ai crawlers blocked": "ChatGPT has 900M+ weekly active users and Google AI Overviews reaches 1.5B users/month. Blocking their crawlers means your content cannot be discovered or cited by these platforms.",
    "missing llms.txt": "The llms.txt standard helps AI systems understand your site structure and prioritize your most important content. Without it, AI crawlers treat all pages equally rather than focusing on your key offerings.",
    "content not ai-citable": "AI platforms prefer citing self-contained passages of 134-167 words that directly answer questions. Content that isn't structured this way gets passed over in favor of competitors whose content is easier to quote.",
    "javascript-only rendering": "AI crawlers typically don't execute JavaScript. If your key content loads via client-side rendering, it's invisible to ChatGPT, Perplexity, and other AI platforms that read raw HTML.",
    "weak brand entity": "AI models rely heavily on entity recognition. Without presence on Wikipedia, Wikidata, or major platforms, AI systems have low confidence in your brand identity and are less likely to recommend you.",
    "missing faq schema": "FAQ markup signals to AI systems that your page directly answers common questions. Without it, competitor pages with FAQ schema will be cited instead when users ask questions in your field.",
    "no author credentials": "E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) signals are critical for AI citation. Without visible author credentials, AI systems cannot verify your expertise.",
}
ACTION_ESTIMATES = {
    "allow ai crawlers": {"time":"10 min","impact":"+5-8","difficulty":"Easy"},
    "allow tier 1 ai crawlers": {"time":"10 min","impact":"+5-8","difficulty":"Easy"},
    "add publication dates": {"time":"30 min","impact":"+3-5","difficulty":"Easy"},
    "create llms.txt": {"time":"20 min","impact":"+3-4","difficulty":"Easy"},
    "add author bylines": {"time":"1 hour","impact":"+4-6","difficulty":"Easy"},
    "fix meta descriptions": {"time":"1-2 hours","impact":"+3-5","difficulty":"Easy"},
    "implement organization schema": {"time":"1-2 hours","impact":"+8-12","difficulty":"Medium"},
    "question-based headings": {"time":"3-4 hours","impact":"+6-10","difficulty":"Medium"},
    "optimize citability blocks": {"time":"4-6 hours","impact":"+8-15","difficulty":"Medium"},
    "server-side rendering": {"time":"1-2 days","impact":"+5-10","difficulty":"Hard"},
    "indexnow protocol": {"time":"30 min","impact":"+2-3","difficulty":"Easy"},
    "wikipedia/wikidata presence": {"time":"2-4 weeks","impact":"+10-15","difficulty":"Hard"},
    "reddit engagement": {"time":"Ongoing","impact":"+5-8","difficulty":"Medium"},
    "youtube content strategy": {"time":"Ongoing","impact":"+5-10","difficulty":"Medium"},
    "original research program": {"time":"Ongoing","impact":"+8-12","difficulty":"Hard"},
    "topical authority clusters": {"time":"2-3 months","impact":"+10-20","difficulty":"Hard"},
}

def _match_impact(title):
    tl = title.lower()
    for k, v in FINDING_IMPACTS.items():
        if k in tl: return v
    return None

def _match_estimate(text):
    tl = text.lower()
    for k, v in ACTION_ESTIMATES.items():
        if k in tl: return v
    return None

def _auto_exec_summary(bn, url, gs, scores, findings, plats):
    sm = [("AI Citability & Visibility", scores.get("ai_citability",0)),
          ("Brand Authority Signals", scores.get("brand_authority",0)),
          ("Content Quality & E-E-A-T", scores.get("content_eeat",0)),
          ("Technical Foundations", scores.get("technical",0)),
          ("Structured Data", scores.get("schema",0)),
          ("Platform Optimization", scores.get("platform_optimization",0))]
    strongest = max(sm, key=lambda x: x[1]); weakest = min(sm, key=lambda x: x[1])
    critical = len([f for f in findings if f.get("severity","").lower() in ("critical","high")])
    boost = min(25, critical*6+5); proj = min(100, gs+boost)
    bp = max(plats.items(), key=lambda x: x[1]) if plats else ("N/A",0)
    wp = min(plats.items(), key=lambda x: x[1]) if plats else ("N/A",0)
    return [
        f"This report presents a comprehensive Generative Engine Optimization (GEO) audit of <b>{bn}</b> ({url}). The analysis evaluated the website's readiness for AI-powered search engines \u2014 Google AI Overviews, ChatGPT, Perplexity, Gemini, and Bing Copilot \u2014 across six dimensions. The overall GEO Readiness Score is <b>{gs}/100</b>, placing the site in the <b>{score_label(gs)}</b> tier.",
        f"The strongest area is <b>{strongest[0]}</b> at {strongest[1]}/100, while <b>{weakest[0]}</b> at {weakest[1]}/100 represents the most significant opportunity for improvement. The audit identified <b>{critical} critical or high-severity findings</b> that are directly impacting AI visibility.",
        f"Among AI platforms, {bn} has the highest readiness for <b>{bp[0]}</b> ({bp[1]}/100) and the lowest for <b>{wp[0]}</b> ({wp[1]}/100). Given that only 23% of businesses are currently investing in GEO, addressing these gaps represents a significant first-mover advantage in AI search visibility.",
        f"By implementing the Quick Win actions outlined in this report, the GEO score could improve to approximately <b>{proj}/100</b> within 30 days. The full action plan provides a prioritized roadmap with estimated effort and score impact for each recommendation.",
    ]


# ════════════════════════════════════════════════════════════════
# HEADER / FOOTER
# ════════════════════════════════════════════════════════════════
class PremiumDoc(SimpleDocTemplate):
    def __init__(self, *a, **kw):
        self.brand = kw.pop("brand", {}); self.theme = kw.pop("theme", build_theme())
        super().__init__(*a, **kw)

def hf(canvas, doc):
    canvas.saveState(); t=doc.theme; b=doc.brand; pw,ph=letter
    if t.get("dark_mode") and t.get("page_bg"):
        canvas.setFillColor(t["page_bg"]); canvas.rect(0,0,pw,ph,fill=1,stroke=0)
    canvas.setFillColor(t["accent"]); canvas.rect(0,ph-6,pw,6,fill=1,stroke=0)
    canvas.setStrokeColor(t["accent"]); canvas.setLineWidth(1); canvas.line(50,ph-38,pw-50,ph-38)
    canvas.setFont('Helvetica',7); canvas.setFillColor(t["text_light"])
    canvas.drawString(50,ph-34,"GEO Analysis Report \u2014 Premium")
    cn=b.get("consultant_name","")
    if cn: canvas.setFont('Helvetica-Bold',7); canvas.setFillColor(t["accent"]); canvas.drawRightString(pw-50,ph-34,cn)
    canvas.setStrokeColor(t["text_light"] if t.get("dark_mode") else lightgrey); canvas.setLineWidth(0.5); canvas.line(50,38,pw-50,38)
    canvas.setFillColor(t["accent"]); canvas.rect(0,0,pw,3,fill=1,stroke=0)
    canvas.setFont('Helvetica',7); canvas.setFillColor(t["text_light"])
    canvas.drawString(50,26,f"Generated {datetime.now().strftime('%B %d, %Y')}")
    canvas.drawRightString(pw-50,26,f"Page {doc.page}")
    cl=b.get("client_name",""); canvas.drawCentredString(pw/2,26,f"Prepared for {cl}" if cl else "Confidential")
    canvas.restoreState()


# ════════════════════════════════════════════════════════════════
# MAIN REPORT
# ════════════════════════════════════════════════════════════════
def generate(data, out="GEO-PREMIUM-REPORT.pdf", client_url=None, client_color=None,
             consultant_name=None, consultant_color=None, dark_mode=False, **kw):
    url=data.get("url",""); bn=data.get("brand_name",url.replace("https://","").replace("http://","").split("/")[0])
    ext=None; src=client_url or url
    if not client_color and src:
        print(f"Extracting brand colors from {src}...",file=sys.stderr); ext=extract_brand_colors(src)
    fcc=client_color or ext; t=build_theme(fcc,consultant_color,dark_mode=dark_mode)
    brand={"client_name":bn,"consultant_name":consultant_name or "","client_color":fcc,"extracted":ext is not None}
    doc=PremiumDoc(out,pagesize=letter,topMargin=48,bottomMargin=48,leftMargin=50,rightMargin=50,brand=brand,theme=t)
    s=build_styles(t); el=[]
    dt=data.get("date",datetime.now().strftime("%Y-%m-%d")); gs=data.get("geo_score",0); sc=data.get("scores",{})
    plats=data.get("platforms",{"Google AI Overviews":0,"ChatGPT":0,"Perplexity":0,"Gemini":0,"Bing Copilot":0})
    findings=data.get("findings",[]); qw=data.get("quick_wins",[]); mt=data.get("medium_term",[]); st_i=data.get("strategic",[])
    ca=data.get("crawler_access",{}); es=data.get("executive_summary","")
    aic=sc.get("ai_citability",0); ba=sc.get("brand_authority",0); ce=sc.get("content_eeat",0)
    te=sc.get("technical",0); sch=sc.get("schema",0); po=sc.get("platform_optimization",0)
    ah=t["client"]["primary"]; all_scores=[aic,ba,ce,te,sch,po]

    # COVER
    el.append(Spacer(1,20))
    if consultant_name: el.append(Paragraph(consultant_name,s['CB'])); el.append(Spacer(1,10))
    el.append(HRFlowable(width="100%",thickness=3,color=t["accent"],spaceAfter=16))
    el.append(Paragraph("GEO Analysis Report",s['RT']))
    el.append(Paragraph(f'Generative Engine Optimization Audit for <b><font color="{ah}">{bn}</font></b>',s['RS']))
    el.append(HRFlowable(width="100%",thickness=1,color=t["accent"],spaceBefore=4,spaceAfter=18))
    scol=score_color(gs,t)
    gauge_cell=[make_gauge(gs,t,130,130),Paragraph(f'<font color="{scol.hexval()}" size="13"><b>{score_label(gs)}</b></font>',ParagraphStyle('GL',alignment=TA_CENTER,spaceBefore=4))]
    strongest=max(zip(["Citability","Brand","Content","Technical","Schema","Platform"],all_scores),key=lambda x:x[1])
    weakest=min(zip(["Citability","Brand","Content","Technical","Schema","Platform"],all_scores),key=lambda x:x[1])
    cc2=len([f for f in findings if f.get("severity","").lower() in ("critical","high")])
    bc=len([c for c,v in ca.items() if isinstance(v,dict) and "block" in v.get("status","").lower()])
    dd=[["Website",url],["Date",datetime.strptime(dt,"%Y-%m-%d").strftime("%B %d, %Y") if "-" in dt else dt],
        ["GEO Score",f"{gs}/100"],["Strongest",f"{strongest[0]} ({strongest[1]}/100)"],["Weakest",f"{weakest[0]} ({weakest[1]}/100)"],
        ["Critical Issues",f"{cc2} found"],["AI Crawlers Blocked",f"{bc} of {len(ca)}"]]
    if consultant_name: dd.append(["Prepared By",consultant_name])
    dt2=Table(dd,colWidths=[95,210])
    dt2.setStyle(TableStyle([('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTNAME',(1,0),(1,-1),'Helvetica'),
        ('FONTSIZE',(0,0),(-1,-1),9),('TEXTCOLOR',(0,0),(0,-1),t["accent"]),('TEXTCOLOR',(1,0),(1,-1),t["text"]),
        ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
        ('LINEBELOW',(0,0),(-1,-2),0.5,HexColor("#2d3748") if t.get("dark_mode") else lightgrey)]))
    ct=Table([[gauge_cell,dt2]],colWidths=[150,320])
    ct.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),0)]))
    el.append(ct); el.append(Spacer(1,14))
    qwb=min(25,cc2*6+5); proj=min(100,gs+qwb)
    el.append(Paragraph(f'<b>Key Highlights:</b> GEO Score {gs}/100 ({score_label(gs)}) \u2022 {cc2} critical/high issues \u2022 {bc} AI crawlers blocked \u2022 Projected after quick wins: <b>{proj}/100</b>',s['HIGHLIGHT']))
    el.append(PageBreak())

    # EXEC SUMMARY
    el.append(Paragraph("Executive Summary",s['SH']))
    el.append(HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=8))
    if es: el.append(Paragraph(es,s['BD']))
    else:
        for p in _auto_exec_summary(bn,url,gs,sc,findings,plats): el.append(Paragraph(p,s['BD']))
    el.append(Spacer(1,8))

    # SCORE BREAKDOWN
    sd=[["Component","Score","Weight","Weighted"],["AI Citability & Visibility",f"{aic}/100","25%",f"{round(aic*0.25,1)}"],
        ["Brand Authority Signals",f"{ba}/100","20%",f"{round(ba*0.20,1)}"],["Content Quality & E-E-A-T",f"{ce}/100","20%",f"{round(ce*0.20,1)}"],
        ["Technical Foundations",f"{te}/100","15%",f"{round(te*0.15,1)}"],["Structured Data",f"{sch}/100","10%",f"{round(sch*0.10,1)}"],
        ["Platform Optimization",f"{po}/100","10%",f"{round(po*0.10,1)}"],["OVERALL",f"{gs}/100","100%",f"{gs}"]]
    stb=Table(sd,colWidths=[180,70,55,70]); sty=make_ts(t)
    sty.add('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold'); sty.add('BACKGROUND',(0,-1),(-1,-1),t["bg_medium"])
    for i in range(1,len(sd)-1): sv=int(sd[i][1].split("/")[0]); sty.add('TEXTCOLOR',(1,i),(1,i),score_color(sv,t))
    stb.setStyle(sty)
    el.append(KeepTogether([Paragraph("GEO Score Breakdown",s['SH']),HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=6),stb,Spacer(1,6),
        make_bars([aic,ba,ce,te,sch,po],["Citability","Brand","Content","Technical","Schema","Platform"],t)]))

    # PLATFORMS
    ps=[Paragraph("AI Platform Readiness",s['SH']),HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=6),
        Paragraph("Readiness scores per AI platform, based on crawler access, citability, and structured data.",s['BD']),Spacer(1,4)]
    if plats: ps.append(make_platform_chart(plats,t))
    el.append(KeepTogether(ps))

    # CRAWLERS
    cs=[Paragraph("AI Crawler Access Status",s['SH']),HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=6),
        Paragraph("Blocking AI crawlers prevents citation. Tier 1 (GPTBot, ClaudeBot, PerplexityBot) should be allowed.",s['BD']),Spacer(1,4)]
    if ca:
        cd=[["Crawler","Platform","Status","Action Required"]]
        for cn3,info in ca.items():
            cd.append([cn3,info.get("platform",""),info.get("status","?"),info.get("recommendation","")] if isinstance(info,dict) else [cn3,"",str(info),""])
        ctb=Table(cd,colWidths=[95,95,75,200]); cts=make_ts(t)
        for i in range(1,len(cd)):
            st2=cd[i][2].upper()
            if "ALLOW" in st2: cts.add('TEXTCOLOR',(2,i),(2,i),t["success"])
            elif "BLOCK" in st2: cts.add('TEXTCOLOR',(2,i),(2,i),t["danger"])
        ctb.setStyle(cts); cs.append(ctb)
    el.append(KeepTogether(cs))

    # FINDINGS
    fh=[Paragraph("Key Findings",s['SH']),HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=6)]
    if findings:
        f0=findings[0]; sv0=f0.get("severity","info").upper()
        sc0={"CRITICAL":t["danger"],"HIGH":t["warning"],"MEDIUM":t["info"]}.get(sv0,t["text_light"])
        ff=[Paragraph(f'<font color="{sc0.hexval()}">[{sv0}]</font> <b>{f0.get("title","")}</b>',s['BD'])]
        if f0.get("description"): ff.append(Paragraph(f0["description"],s['REC']))
        im0=f0.get("business_impact") or _match_impact(f0.get("title","")); 
        if im0: ff.append(Paragraph(f'<i>Why this matters: {im0}</i>',s['IMPACT']))
        el.append(KeepTogether(fh+ff))
        for f in findings[1:]:
            sv=f.get("severity","info").upper(); svc={"CRITICAL":t["danger"],"HIGH":t["warning"],"MEDIUM":t["info"]}.get(sv,t["text_light"])
            fb=[Paragraph(f'<font color="{svc.hexval()}">[{sv}]</font> <b>{f.get("title","")}</b>',s['BD'])]
            if f.get("description"): fb.append(Paragraph(f["description"],s['REC']))
            im=f.get("business_impact") or _match_impact(f.get("title",""))
            if im: fb.append(Paragraph(f'<i>Why this matters: {im}</i>',s['IMPACT']))
            el.append(KeepTogether(fb))
    else: el.append(KeepTogether(fh+[Paragraph("<i>Run /geo audit to populate.</i>",s['BD'])]))

    # FORECAST
    qwb2=min(20,cc2*5+3); mtb=min(18,len(findings)*3); stb2=15
    pqw=min(100,gs+qwb2); pmt=min(100,pqw+mtb); pst=min(100,pmt+stb2)
    fc=[["Phase","Timeline","Projected Score","Improvement"],["Current","Today",f"{gs}/100","\u2014"],
        ["After Quick Wins","1-2 weeks",f"{pqw}/100",f"+{qwb2}"],["After Medium-Term","1-2 months",f"{pmt}/100",f"+{qwb2+mtb} total"],
        ["After Strategic","3-6 months",f"{pst}/100",f"+{qwb2+mtb+stb2} total"]]
    fct=Table(fc,colWidths=[130,90,100,100]); fcs=make_ts(t); fcs.add('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold')
    for i in range(1,5): v=int(fc[i][2].split("/")[0]); fcs.add('TEXTCOLOR',(2,i),(2,i),score_color(v,t))
    fct.setStyle(fcs)
    el.append(KeepTogether([Paragraph("Score Improvement Forecast",s['SH']),HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=6),
        Paragraph("Estimated improvement from implementing recommendations.",s['BD']),Spacer(1,4),fct]))

    # ACTION PLAN
    el.append(Paragraph("Prioritized Action Plan",s['SH'])); el.append(HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=6))
    def _bas(hdr,desc,acts,defs):
        ib=[Paragraph(hdr,s['SUB']),Paragraph(desc,s['SM'])]
        for i,a in enumerate(acts or defs,1):
            at=a.get('action','') if isinstance(a,dict) else a; est=_match_estimate(at)
            if isinstance(a,dict) and a.get('time'): est={"time":a["time"],"impact":a.get("impact",""),"difficulty":a.get("difficulty","")}
            ib.append(Paragraph(f"<b>{i}.</b> {at}",s['REC']))
            if est:
                et=f"Effort: {est['time']}";
                if est.get('impact'): et+=f" \u2022 Score impact: {est['impact']} pts"
                if est.get('difficulty'): et+=f" \u2022 {est['difficulty']}"
                ib.append(Paragraph(et,s['IMPACT']))
        return KeepTogether(ib)
    el.append(_bas("Quick Wins (This Week)","High impact, low effort \u2014 implement immediately.",qw,
        ["Allow Tier 1 AI crawlers in robots.txt (GPTBot, ClaudeBot, PerplexityBot)","Add publication and last-updated dates to all content pages",
         "Create an llms.txt file to guide AI crawlers to key content","Add author bylines with credentials to blog posts and articles",
         "Fix meta descriptions on top 10 highest-traffic pages"]))
    el.append(_bas("Medium-Term Improvements (This Month)","Significant impact, moderate effort.",mt,
        ["Implement Organization + Article + Person JSON-LD schema markup","Restructure top pages with question-based H2 headings",
         "Optimize content blocks for AI citability (134-167 word passages)","Ensure server-side rendering for all public content pages",
         "Set up IndexNow protocol for instant Bing/Copilot indexing"]))
    el.append(_bas("Strategic Initiatives (This Quarter)","Long-term competitive advantage.",st_i,
        ["Build Wikipedia/Wikidata entity presence through press coverage","Develop active Reddit community engagement in relevant subreddits",
         "Create YouTube content strategy aligned with AI-searched queries","Establish original research and data publication program",
         "Build comprehensive topical authority content clusters"]))

    # NEXT STEPS
    cta=consultant_name or "your GEO consultant"
    el.append(KeepTogether([Spacer(1,6),Paragraph("Next Steps",s['SH']),HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=6),
        Paragraph(f"This report identifies actionable improvements that can significantly increase {bn}'s AI search visibility. Quick Wins alone could improve the score by {qwb2}+ points within two weeks.",s['BD']),
        Paragraph(f"<b>To discuss these findings and begin implementation, contact {cta}.</b> We recommend starting with Quick Wins and scheduling a follow-up in 30 days.",s['BD'])]))

    # METHODOLOGY
    gl=[["Term","Definition"],["GEO","Generative Engine Optimization"],["AIO","AI Overviews \u2014 Google's AI answer feature"],
        ["E-E-A-T","Experience, Expertise, Authoritativeness, Trustworthiness"],["JSON-LD","Preferred structured data format"],
        ["llms.txt","AI guidance file standard"],["IndexNow","Instant search engine notification protocol"]]
    gt=Table(gl,colWidths=[65,400]); gt.setStyle(make_ts(t))
    ftx=f"Prepared by {consultant_name} using GEO-SEO Premium Analysis." if consultant_name else "Generated using GEO-SEO Premium Analysis."
    el.append(KeepTogether([Spacer(1,10),Paragraph("Appendix: Methodology",s['SH']),HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=6),
        Paragraph(f"Audit on {dt} for {url}. Six dimensions: AI Citability (25%), Brand Authority (20%), Content E-E-A-T (20%), Technical (15%), Structured Data (10%), Platform Optimization (10%).",s['BD']),
        Spacer(1,6),Paragraph("Glossary",s['SUB']),gt,Spacer(1,12),
        HRFlowable(width="100%",thickness=0.5,color=HexColor("#2d3748") if t.get("dark_mode") else lightgrey,spaceAfter=4),Paragraph(ftx,s['SM'])]))

    doc.build(el,onFirstPage=hf,onLaterPages=hf)
    print(f"\n\u2705 Premium report: {out}",file=sys.stderr)
    if fcc: print(f"   Brand color: {fcc} {'(extracted)' if ext else '(provided)'}",file=sys.stderr)
    return out

if __name__=="__main__":
    a=sys.argv[1:]; cu=cc=cn=rcol=None; pos=[]; dark_mode=False; i=0
    while i<len(a):
        if a[i]=="--client-url" and i+1<len(a): cu=a[i+1]; i+=2
        elif a[i]=="--client-color" and i+1<len(a): cc=a[i+1]; i+=2
        elif a[i]=="--consultant-name" and i+1<len(a): cn=a[i+1]; i+=2
        elif a[i]=="--consultant-color" and i+1<len(a): rcol=a[i+1]; i+=2
        elif a[i]=="--dark": dark_mode=True; i+=1
        else: pos.append(a[i]); i+=1
    if not pos:
        sample={"url":"https://nudentistry.com","brand_name":"Nu Dentistry Houston","date":datetime.now().strftime("%Y-%m-%d"),"geo_score":42,
            "scores":{"ai_citability":35,"brand_authority":55,"content_eeat":60,"technical":45,"schema":20,"platform_optimization":30},
            "platforms":{"Google AI Overviews":50,"ChatGPT":35,"Perplexity":30,"Gemini":45,"Bing Copilot":40},
            "findings":[{"severity":"critical","title":"AI Crawlers Blocked","description":"robots.txt blocks GPTBot and ClaudeBot."},
                {"severity":"critical","title":"No Schema Markup","description":"No JSON-LD detected. AI cannot determine business type."},
                {"severity":"high","title":"Missing FAQ Schema","description":"No FAQPage markup for common questions."},
                {"severity":"high","title":"Content Not AI-Citable","description":"Content not structured for AI citation."},
                {"severity":"medium","title":"No Author Credentials","description":"Practitioner credentials not visible to AI."},
                {"severity":"medium","title":"Missing llms.txt","description":"No llms.txt to guide AI crawlers."}],
            "crawler_access":{"GPTBot":{"platform":"ChatGPT","status":"Blocked","recommendation":"Unblock immediately"},
                "ClaudeBot":{"platform":"Claude","status":"Blocked","recommendation":"Unblock immediately"},
                "PerplexityBot":{"platform":"Perplexity","status":"Blocked","recommendation":"Unblock for visibility"},
                "Google-Extended":{"platform":"Gemini","status":"Allowed","recommendation":"Keep allowed"},
                "Bingbot":{"platform":"Bing Copilot","status":"Allowed","recommendation":"Keep allowed"}}}
        generate(sample,"GEO-PREMIUM-REPORT-sample.pdf",consultant_name=cn or "GEO Audit Services",dark_mode=dark_mode)
        print("Sample report generated.")
    else:
        ip=pos[0]; op=pos[1] if len(pos)>1 else "GEO-PREMIUM-REPORT.pdf"
        data=json.loads(sys.stdin.read()) if ip=="-" else json.load(open(ip))
        generate(data,op,client_url=cu,client_color=cc,consultant_name=cn,consultant_color=rcol,dark_mode=dark_mode)
