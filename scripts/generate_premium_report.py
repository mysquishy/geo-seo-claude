#!/usr/bin/env python3
"""
generate_premium_report.py - Premium co-branded GEO audit PDF report.

Extracts client brand colors from their website, combines with consultant
brand colors, produces a professional co-branded report.

Usage:
    python3 generate_premium_report.py <json_data> [output.pdf] [options]
    python3 generate_premium_report.py data.json report.pdf --client-url https://example.com
    python3 generate_premium_report.py data.json report.pdf --client-color "#2563eb"
    python3 generate_premium_report.py data.json report.pdf --consultant-name "My Brand"

Options:
    --client-url URL         Extract brand colors from client website
    --client-color HEX       Override client primary color
    --consultant-name NAME   Your brand name for co-branding
    --consultant-color HEX   Override consultant primary color
"""
import sys, json, os, re, urllib.request
from datetime import datetime
from colorsys import rgb_to_hls, hls_to_rgb

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import HexColor, white, lightgrey
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
        TableStyle, PageBreak, HRFlowable)
    from reportlab.graphics.shapes import Drawing, Rect, String, Circle
    from reportlab.graphics.charts.barcharts import VerticalBarChart
except ImportError:
    print("ERROR: pip install reportlab"); sys.exit(1)

# ── BRAND COLOR EXTRACTION ───────────────────────────────────
def extract_brand_colors(url):
    if not url: return None
    if not url.startswith("http"): url = "https://"+url
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (compatible; GEOPremium/1.0)"})
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="ignore")[:100000]
    except Exception as e:
        print(f"  Could not fetch {url}: {e}", file=sys.stderr); return None
    colors = []
    # theme-color meta
    m = re.search(r'<meta[^>]*name=["\']theme-color["\'][^>]*content=["\']([^"\']+)', html, re.I)
    if not m: m = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']theme-color', html, re.I)
    if m: colors.append(("theme", m.group(1).strip()))
    # CSS vars
    for pat in [r'--(?:primary|brand|main)[-_]?color\s*:\s*([^;}\s]+)',
                r'--(?:primary|brand|main)\s*:\s*([^;}\s]+)']:
        m = re.search(pat, html, re.I)
        if m: colors.append(("css-var", m.group(1).strip()))
    # header bg
    m = re.search(r'<(?:header|nav)[^>]*style=["\'][^"\']*background(?:-color)?\s*:\s*([^;"\'\s]+)', html, re.I)
    if m: colors.append(("header-bg", m.group(1).strip()))
    # frequent hex
    all_hex = re.findall(r'#([0-9a-fA-F]{6})\b', html)
    skip = {"000000","ffffff","f5f5f5","e5e5e5","cccccc","333333","666666","999999","eeeeee","f0f0f0","f8f8f8","fafafa"}
    counts = {}
    for h in all_hex:
        hl = h.lower()
        if hl not in skip: counts[hl] = counts.get(hl,0)+1
    if counts:
        top = max(counts, key=counts.get)
        if counts[top]>=3: colors.append(("freq", f"#{top}"))
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

# ── COLOR UTILS ──────────────────────────────────────────────
def hex2rgb(h):
    h=h.lstrip('#'); return tuple(int(h[i:i+2],16)/255.0 for i in (0,2,4))
def rgb2hex(r,g,b): return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
def lighten(h, a=0.3):
    r,g,b=hex2rgb(h); h2,l,s=rgb_to_hls(r,g,b); l=min(1,l+a)
    return rgb2hex(*hls_to_rgb(h2,l,s))
def darken(h, a=0.15):
    r,g,b=hex2rgb(h); h2,l,s=rgb_to_hls(r,g,b); l=max(0,l-a)
    return rgb2hex(*hls_to_rgb(h2,l,s))
def is_light(h): r,g,b=hex2rgb(h); return 0.299*r+0.587*g+0.114*b>0.5

def build_theme(cp=None, rp=None):
    cp = cp or "#2563eb"; rp = rp or "#1a1a2e"
    return {
        "client": {"primary":cp, "dark":darken(cp,0.2), "light":lighten(cp,0.35),
            "bg":lighten(cp,0.45), "text_on":("#ffffff" if not is_light(cp) else "#1a1a2e")},
        "consultant": {"primary":rp},
        "header":HexColor(rp), "accent":HexColor(cp),
        "accent_light":HexColor(lighten(cp,0.35)), "accent_bg":HexColor(lighten(cp,0.45)),
        "success":HexColor("#00b894"), "warning":HexColor("#fdcb6e"),
        "danger":HexColor("#d63031"), "info":HexColor(cp),
        "text":HexColor("#2d3436"), "text_light":HexColor("#636e72"),
        "bg_light":HexColor("#f8f9fa"), "bg_medium":HexColor("#e9ecef"),
        "white":white, "black":HexColor("#000000"),
    }

def score_color(s, t):
    if s>=80: return t["success"]
    elif s>=60: return t["info"]
    elif s>=40: return t["warning"]
    return t["danger"]

def score_label(s):
    if s>=85: return "Excellent"
    elif s>=70: return "Good"
    elif s>=55: return "Moderate"
    elif s>=40: return "Below Average"
    return "Needs Attention"

# ── CHARTS ───────────────────────────────────────────────────
def make_gauge(score, t, w=180, h=180):
    d=Drawing(w,h)
    d.add(Circle(w/2,h/2,55,fillColor=t["bg_light"],
        strokeColor=HexColor(lighten(t["client"]["primary"],0.3)),strokeWidth=3))
    d.add(Circle(w/2,h/2,48,fillColor=score_color(score,t),strokeColor=None))
    d.add(Circle(w/2,h/2,36,fillColor=t["white"],strokeColor=None))
    d.add(String(w/2,h/2+6,str(score),fontSize=28,fontName='Helvetica-Bold',
        fillColor=t["text"],textAnchor='middle'))
    d.add(String(w/2,h/2-12,"/100",fontSize=10,fontName='Helvetica',
        fillColor=t["text_light"],textAnchor='middle'))
    return d

def make_bars(data, labels, t, w=420, h=200):
    d=Drawing(w,h)
    c=VerticalBarChart(); c.x=60; c.y=30; c.height=h-60; c.width=w-80
    c.data=[data]; c.categoryAxis.categoryNames=labels
    c.categoryAxis.labels.fontSize=8; c.valueAxis.valueMin=0
    c.valueAxis.valueMax=100; c.valueAxis.valueStep=20; c.valueAxis.labels.fontSize=8
    for i,s in enumerate(data): c.bars[0].fillColor=score_color(s,t)
    c.bars[0].strokeColor=None; d.add(c); return d

def make_platform_chart(plats, t, w=450, h=180):
    d=Drawing(w,h); bh=22; bmax=280; sy=h-30
    for i,(nm,sc) in enumerate(plats.items()):
        y=sy-(i*(bh+10))
        d.add(String(10,y+5,nm,fontSize=9,fontName='Helvetica',fillColor=t["text"],textAnchor='start'))
        bx=130
        d.add(Rect(bx,y,bmax,bh,fillColor=t["bg_light"],strokeColor=None))
        d.add(Rect(bx,y,(sc/100)*bmax,bh,fillColor=score_color(sc,t),strokeColor=None))
        d.add(String(bx+bmax+10,y+6,f"{sc}/100",fontSize=9,fontName='Helvetica-Bold',
            fillColor=t["text"],textAnchor='start'))
    return d

# ── STYLES ───────────────────────────────────────────────────
def build_styles(t):
    ss=getSampleStyleSheet()
    ss.add(ParagraphStyle('RT',fontName='Helvetica-Bold',fontSize=28,textColor=t["header"],spaceAfter=6))
    ss.add(ParagraphStyle('RS',fontName='Helvetica',fontSize=14,textColor=t["text_light"],spaceAfter=20))
    ss.add(ParagraphStyle('SH',fontName='Helvetica-Bold',fontSize=18,textColor=t["header"],spaceBefore=20,spaceAfter=10))
    ss.add(ParagraphStyle('SUB',fontName='Helvetica-Bold',fontSize=13,textColor=t["accent"],spaceBefore=14,spaceAfter=6))
    ss.add(ParagraphStyle('BD',fontName='Helvetica',fontSize=10,textColor=t["text"],spaceBefore=4,spaceAfter=4,leading=14,alignment=TA_JUSTIFY))
    ss.add(ParagraphStyle('SM',fontName='Helvetica',fontSize=8,textColor=t["text_light"],spaceBefore=2,spaceAfter=2))
    ss.add(ParagraphStyle('REC',fontName='Helvetica',fontSize=10,textColor=t["text"],leftIndent=15,spaceBefore=3,spaceAfter=3,leading=14))
    ss.add(ParagraphStyle('CB',fontName='Helvetica-Bold',fontSize=11,textColor=t["text_light"],alignment=TA_RIGHT))
    return ss

def make_ts(t):
    return TableStyle([
        ('BACKGROUND',(0,0),(-1,0),t["header"]),('TEXTCOLOR',(0,0),(-1,0),t["white"]),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,0),9),
        ('FONTNAME',(0,1),(-1,-1),'Helvetica'),('FONTSIZE',(0,1),(-1,-1),9),
        ('TEXTCOLOR',(0,1),(-1,-1),t["text"]),('ALIGN',(0,0),(-1,-1),'LEFT'),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('GRID',(0,0),(-1,-1),0.5,lightgrey),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[white,t["bg_light"]]),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8)])

# ── HEADER/FOOTER ────────────────────────────────────────────
class PremiumDoc(SimpleDocTemplate):
    def __init__(self, *a, **kw):
        self.brand=kw.pop("brand",{}); self.theme=kw.pop("theme",build_theme())
        super().__init__(*a, **kw)

def hf(canvas, doc):
    canvas.saveState()
    t=doc.theme; b=doc.brand; pw,ph=letter
    canvas.setFillColor(t["accent"]); canvas.rect(0,ph-8,pw,8,fill=1,stroke=0)
    canvas.setStrokeColor(t["accent"]); canvas.setLineWidth(1.5)
    canvas.line(50,ph-42,pw-50,ph-42)
    canvas.setFont('Helvetica',8); canvas.setFillColor(t["text_light"])
    canvas.drawString(50,ph-37,"GEO Analysis Report \u2014 Premium")
    cn=b.get("consultant_name","")
    if cn:
        canvas.setFont('Helvetica-Bold',8); canvas.setFillColor(t["header"])
        canvas.drawRightString(pw-50,ph-37,cn)
    canvas.setStrokeColor(lightgrey); canvas.setLineWidth(0.5)
    canvas.line(50,42,pw-50,42)
    canvas.setFillColor(t["accent"]); canvas.rect(0,0,pw,4,fill=1,stroke=0)
    canvas.setFont('Helvetica',8); canvas.setFillColor(t["text_light"])
    canvas.drawString(50,28,f"Generated {datetime.now().strftime('%B %d, %Y')}")
    canvas.drawRightString(pw-50,28,f"Page {doc.page}")
    cl=b.get("client_name","")
    canvas.drawCentredString(pw/2,28,f"Prepared for {cl}" if cl else "Confidential")
    canvas.restoreState()

# ── MAIN REPORT ──────────────────────────────────────────────
def generate(data, out="GEO-PREMIUM-REPORT.pdf", client_url=None,
             client_color=None, consultant_name=None, consultant_color=None, **kw):
    url=data.get("url",""); bn=data.get("brand_name",url.replace("https://","").replace("http://","").split("/")[0])
    ext=None
    src=client_url or url
    if not client_color and src:
        print(f"Extracting brand colors from {src}...",file=sys.stderr)
        ext=extract_brand_colors(src)
    fcc=client_color or ext
    t=build_theme(fcc, consultant_color)
    brand={"client_name":bn,"consultant_name":consultant_name or "","client_color":fcc,"extracted":ext is not None}
    doc=PremiumDoc(out,pagesize=letter,topMargin=55,bottomMargin=55,leftMargin=50,rightMargin=50,brand=brand,theme=t)
    s=build_styles(t); el=[]
    dt=data.get("date",datetime.now().strftime("%Y-%m-%d"))
    gs=data.get("geo_score",0); sc=data.get("scores",{})
    plats=data.get("platforms",{"Google AI Overviews":0,"ChatGPT":0,"Perplexity":0,"Gemini":0,"Bing Copilot":0})
    findings=data.get("findings",[]); qw=data.get("quick_wins",[]); mt=data.get("medium_term",[]); st_i=data.get("strategic",[])
    ca=data.get("crawler_access",{}); es=data.get("executive_summary","")
    aic=sc.get("ai_citability",0); ba=sc.get("brand_authority",0); ce=sc.get("content_eeat",0)
    te=sc.get("technical",0); sch=sc.get("schema",0); po=sc.get("platform_optimization",0)
    ah=t["client"]["primary"]
    # COVER
    el.append(Spacer(1,60))
    if consultant_name: el.append(Paragraph(consultant_name,s['CB'])); el.append(Spacer(1,30))
    el.append(HRFlowable(width="100%",thickness=4,color=t["accent"],spaceAfter=15))
    el.append(Paragraph("GEO Analysis Report",s['RT']))
    el.append(Spacer(1,6))
    el.append(Paragraph(f'Audit for <b><font color="{ah}">{bn}</font></b>',s['RS']))
    el.append(HRFlowable(width="100%",thickness=1.5,color=t["accent"],spaceAfter=25))
    det=[["Website",url],["Date",datetime.strptime(dt,"%Y-%m-%d").strftime("%B %d, %Y") if "-" in dt else dt],
         ["GEO Score",f"{gs}/100 \u2014 {score_label(gs)}"]]
    if consultant_name: det.append(["Prepared By",consultant_name])
    if fcc: det.append(["Brand Color",f"{fcc} {'(extracted)' if ext else '(provided)'}"])
    dtb=Table(det,colWidths=[120,350])
    dtb.setStyle(TableStyle([('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTNAME',(1,0),(1,-1),'Helvetica'),
        ('FONTSIZE',(0,0),(-1,-1),11),('TEXTCOLOR',(0,0),(0,-1),t["accent"]),('TEXTCOLOR',(1,0),(1,-1),t["text"]),
        ('BOTTOMPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,0),(-1,-2),0.5,lightgrey)]))
    el.append(dtb); el.append(Spacer(1,30))
    el.append(make_gauge(gs,t,200,200)); el.append(Spacer(1,15))
    scol=score_color(gs,t)
    el.append(Paragraph(f'<font color="{scol.hexval()}">{score_label(gs)}</font>',
        ParagraphStyle('SL',parent=s['SH'],alignment=TA_CENTER,fontSize=20)))
    el.append(PageBreak())
    # EXEC SUMMARY
    el.append(Paragraph("Executive Summary",s['SH']))
    el.append(HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=12))
    el.append(Paragraph(es or f"This GEO audit of <b>{bn}</b> ({url}) scored <b>{gs}/100</b> ({score_label(gs)}).",s['BD']))
    el.append(Spacer(1,16))
    # SCORE BREAKDOWN
    el.append(Paragraph("GEO Score Breakdown",s['SH']))
    el.append(HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=12))
    sd=[["Component","Score","Weight","Weighted"],
        ["AI Citability",f"{aic}/100","25%",f"{round(aic*0.25,1)}"],
        ["Brand Authority",f"{ba}/100","20%",f"{round(ba*0.20,1)}"],
        ["Content & E-E-A-T",f"{ce}/100","20%",f"{round(ce*0.20,1)}"],
        ["Technical",f"{te}/100","15%",f"{round(te*0.15,1)}"],
        ["Structured Data",f"{sch}/100","10%",f"{round(sch*0.10,1)}"],
        ["Platform Optimization",f"{po}/100","10%",f"{round(po*0.10,1)}"],
        ["OVERALL",f"{gs}/100","100%",f"{gs}"]]
    stb=Table(sd,colWidths=[200,80,60,80]); sty=make_ts(t)
    sty.add('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold'); sty.add('BACKGROUND',(0,-1),(-1,-1),t["bg_medium"])
    for i in range(1,len(sd)-1):
        sv=int(sd[i][1].split("/")[0]); sty.add('TEXTCOLOR',(1,i),(1,i),score_color(sv,t))
    stb.setStyle(sty); el.append(stb); el.append(Spacer(1,16))
    el.append(make_bars([aic,ba,ce,te,sch,po],["Citability","Brand","Content","Technical","Schema","Platform"],t))
    el.append(PageBreak())
    # PLATFORMS
    el.append(Paragraph("AI Platform Readiness",s['SH']))
    el.append(HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=12))
    el.append(Paragraph("Citation likelihood per AI platform.",s['BD'])); el.append(Spacer(1,10))
    if plats: el.append(make_platform_chart(plats,t))
    el.append(Spacer(1,10))
    ptd=[["Platform","Score","Status"]]
    for nm,sc2 in plats.items(): ptd.append([nm,f"{sc2}/100",score_label(sc2)])
    ptb=Table(ptd,colWidths=[180,80,150]); pts=make_ts(t)
    for i in range(1,len(ptd)):
        sv=int(ptd[i][1].split("/")[0]); pts.add('TEXTCOLOR',(1,i),(1,i),score_color(sv,t))
    ptb.setStyle(pts); el.append(ptb); el.append(PageBreak())
    # CRAWLERS
    el.append(Paragraph("AI Crawler Access",s['SH']))
    el.append(HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=12))
    if ca:
        cd=[["Crawler","Platform","Status","Recommendation"]]
        for cn2,info in ca.items():
            cd.append([cn2,info.get("platform",""),info.get("status","?"),info.get("recommendation","")] if isinstance(info,dict) else [cn2,"",str(info),""])
        ctb=Table(cd,colWidths=[100,100,80,180]); cts=make_ts(t)
        for i in range(1,len(cd)):
            st2=cd[i][2].upper()
            if "ALLOW" in st2: cts.add('TEXTCOLOR',(2,i),(2,i),t["success"])
            elif "BLOCK" in st2: cts.add('TEXTCOLOR',(2,i),(2,i),t["danger"])
        ctb.setStyle(cts); el.append(ctb)
    el.append(PageBreak())
    # FINDINGS
    el.append(Paragraph("Key Findings",s['SH']))
    el.append(HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=12))
    for f in findings:
        sv2=f.get("severity","info").upper()
        sc3={"CRITICAL":t["danger"],"HIGH":t["warning"],"MEDIUM":t["info"]}.get(sv2,t["text_light"])
        el.append(Paragraph(f'<font color="{sc3.hexval()}">[{sv2}]</font> <b>{f.get("title","")}</b>',s['BD']))
        if f.get("description"): el.append(Paragraph(f["description"],s['REC']))
        el.append(Spacer(1,4))
    el.append(PageBreak())
    # ACTION PLAN
    el.append(Paragraph("Prioritized Action Plan",s['SH']))
    el.append(HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=12))
    def _sec(hdr,desc,acts,defs):
        el.append(Paragraph(hdr,s['SUB'])); el.append(Paragraph(desc,s['SM']))
        for i,a in enumerate(acts or defs,1):
            tx=f"<b>{i}.</b> {a.get('action','') if isinstance(a,dict) else a}"
            el.append(Paragraph(tx,s['REC']))
        el.append(Spacer(1,12))
    _sec("Quick Wins (This Week)","High impact, low effort.",qw,
        ["Allow AI crawlers in robots.txt","Add publication dates","Create llms.txt","Add author bylines","Fix meta descriptions"])
    _sec("Medium-Term (This Month)","Moderate effort, significant impact.",mt,
        ["Implement Organization schema","Question-based headings","Optimize citability blocks","Server-side rendering","IndexNow protocol"])
    _sec("Strategic (This Quarter)","Long-term competitive advantage.",st_i,
        ["Wikipedia/Wikidata presence","Reddit engagement","YouTube content strategy","Original research program","Topical authority clusters"])
    el.append(PageBreak())
    # METHODOLOGY
    el.append(Paragraph("Appendix: Methodology",s['SH']))
    el.append(HRFlowable(width="100%",thickness=1,color=t["accent"],spaceAfter=12))
    el.append(Paragraph(f"Audit on {dt} for {url}. Six dimensions: AI Citability (25%), Brand Authority (20%), Content E-E-A-T (20%), Technical (15%), Structured Data (10%), Platform Optimization (10%).",s['BD']))
    el.append(Spacer(1,16))
    el.append(Paragraph("Glossary",s['SUB']))
    gl=[["Term","Definition"],["GEO","Generative Engine Optimization"],["AIO","AI Overviews"],
        ["E-E-A-T","Experience, Expertise, Authoritativeness, Trustworthiness"],
        ["JSON-LD","Preferred structured data format"],["llms.txt","AI guidance file standard"],
        ["IndexNow","Instant search engine notification protocol"]]
    gt=Table(gl,colWidths=[80,380]); gt.setStyle(make_ts(t)); el.append(gt)
    el.append(Spacer(1,30))
    el.append(HRFlowable(width="100%",thickness=0.5,color=lightgrey,spaceAfter=8))
    ft=f"Prepared by {consultant_name} using GEO-SEO Premium Analysis." if consultant_name else "Generated using GEO-SEO Premium Analysis."
    el.append(Paragraph(ft,s['SM']))
    doc.build(el, onFirstPage=hf, onLaterPages=hf)
    print(f"\n✅ Premium report: {out}",file=sys.stderr)
    if fcc: print(f"   Brand color: {fcc} {'(extracted)' if ext else '(provided)'}",file=sys.stderr)
    return out

# ── CLI ──────────────────────────────────────────────────────
if __name__=="__main__":
    a=sys.argv[1:]; cu=cc=cn=rcol=None; pos=[]
    i=0
    while i<len(a):
        if a[i]=="--client-url" and i+1<len(a): cu=a[i+1]; i+=2
        elif a[i]=="--client-color" and i+1<len(a): cc=a[i+1]; i+=2
        elif a[i]=="--consultant-name" and i+1<len(a): cn=a[i+1]; i+=2
        elif a[i]=="--consultant-color" and i+1<len(a): rcol=a[i+1]; i+=2
        else: pos.append(a[i]); i+=1
    if not pos:
        sample={"url":"https://example.com","brand_name":"Example Co","date":datetime.now().strftime("%Y-%m-%d"),
            "geo_score":58,"scores":{"ai_citability":45,"brand_authority":62,"content_eeat":70,"technical":55,"schema":30,"platform_optimization":48},
            "platforms":{"Google AI Overviews":65,"ChatGPT":52,"Perplexity":48,"Gemini":60,"Bing Copilot":45},
            "findings":[{"severity":"critical","title":"No Schema Markup","description":"No JSON-LD detected."},
                {"severity":"high","title":"AI Crawlers Blocked","description":"robots.txt blocks GPTBot."}],
            "crawler_access":{"GPTBot":{"platform":"ChatGPT","status":"Blocked","recommendation":"Unblock"},
                "ClaudeBot":{"platform":"Claude","status":"Allowed","recommendation":"Keep"}}}
        generate(sample,"GEO-PREMIUM-REPORT-sample.pdf",consultant_name=cn or "GEO Audit Services")
    else:
        ip=pos[0]; op=pos[1] if len(pos)>1 else "GEO-PREMIUM-REPORT.pdf"
        data=json.loads(sys.stdin.read()) if ip=="-" else json.load(open(ip))
        generate(data,op,client_url=cu,client_color=cc,consultant_name=cn,consultant_color=rcol)
