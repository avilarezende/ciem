#!/usr/bin/env python3
"""Gera mockups do portal destacando Wiki, Calendário e Lembretes."""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets"

W, H = 1440, 900
BG = "#0c1118"
SIDE = "#0a1016"
SURF = "#16202c"
ELEV = "#121a24"
LINE = "#314559"
TEXT = "#e8eef6"
SOFT = "#9aabbd"
FAINT = "#6d7f93"
TEAL = "#2ec4b6"
TEAL_DIM = "#0f2a2a"
BLUE = "#6cb6ff"
ORANGE = "#e6a23c"
RED = "#f07178"
GREEN = "#7dcea0"


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    path = f"/usr/share/fonts/truetype/dejavu/{name}"
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rr(d: ImageDraw.ImageDraw, xy, fill, outline=LINE, radius=10, width=1):
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def save(img: Image.Image, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f"{stem}.png"
    jpg = OUT / f"{stem}.jpg"
    img.save(png, "PNG", optimize=True)
    img.convert("RGB").save(jpg, "JPEG", quality=92, optimize=True)
    print(f"Wrote {png.name} ({png.stat().st_size // 1024}KB) · {jpg.name} ({jpg.stat().st_size // 1024}KB)")


def draw_sidebar(d: ImageDraw.ImageDraw, active: str = "dashboard") -> None:
    d.rectangle((0, 0, 232, H), fill=SIDE)
    d.line((232, 0, 232, H), fill=LINE, width=1)
    ft, fb, fs = font(20, True), font(13, True), font(12)
    d.text((24, 28), "CIEM", fill=TEAL, font=ft)
    d.text((92, 34), "NOC", fill=FAINT, font=fs)
    items = [
        ("dashboard", "Visão geral"),
        ("browser", "Navegador"),
        ("alarms", "Alarmes"),
        ("history", "Histórico"),
        ("analysis", "Análise"),
        ("sessions", "Sessões"),
        ("config", "Configuração"),
    ]
    y = 96
    for key, label in items:
        selected = key == active
        if selected:
            rr(d, (14, y - 10, 218, y + 30), fill=TEAL_DIM, outline=TEAL, radius=8)
            d.text((32, y), label, fill=TEAL, font=fb)
        else:
            d.text((32, y), label, fill=SOFT, font=fs)
        y += 46
    d.text((24, H - 70), "observador (observer)", fill=FAINT, font=fs)
    rr(d, (24, H - 48, 208, H - 18), fill=ELEV, outline=LINE, radius=8)
    d.text((88, H - 40), "Sair", fill=SOFT, font=fs)


def draw_header(d: ImageDraw.ImageDraw, title: str, subtitle: str, wiki: bool = False, cal: bool = False) -> None:
    d.text((260, 28), title, fill=TEXT, font=font(24, True))
    d.text((260, 62), subtitle, fill=FAINT, font=font(13))
    rr(d, (1080, 30, 1160, 64), fill=TEAL_DIM if wiki else ELEV, outline=TEAL if wiki else LINE, radius=8)
    d.text((1100, 40), "Wiki", fill=TEAL if wiki else SOFT, font=font(12, True))
    rr(d, (1172, 30, 1300, 64), fill=TEAL_DIM if cal else ELEV, outline=TEAL if cal else LINE, radius=8)
    d.text((1188, 40), "Calendário", fill=TEAL if cal else SOFT, font=font(12, True))
    rr(d, (1310, 30, 1410, 64), fill="#2a1518", outline=RED, radius=16)
    d.text((1324, 40), "3 alarmes", fill=RED, font=font(11, True))


def draw_edge_tabs(d: ImageDraw.ImageDraw) -> None:
    rr(d, (232, 340, 258, 520), fill=TEAL_DIM, outline=TEAL, radius=6)
    for i, ch in enumerate("Wiki"):
        d.text((238, 380 + i * 22), ch, fill=TEAL, font=font(13, True))
    rr(d, (1412, 320, 1438, 560), fill=TEAL_DIM, outline=TEAL, radius=6)
    for i, ch in enumerate("Calendário"):
        d.text((1418, 340 + i * 18), ch, fill=TEAL, font=font(11, True))


def draw_reminder(d: ImageDraw.ImageDraw, x: int = 1040, y: int = 520) -> None:
    rr(d, (x, y, x + 360, y + 250), fill=SURF, outline=TEAL, radius=12)
    d.rectangle((x, y, x + 360, y + 40), fill=TEAL_DIM)
    d.text((x + 16, y + 12), "Lembretes / Anotações", fill=TEAL, font=font(12, True))
    d.text((x + 300, y + 10), "–  ×", fill=SOFT, font=font(14))
    items = [
        ("☐", "Revisar link SP-RJ", TEXT),
        ("☐", "Atualizar wiki DHCP", TEXT),
        ("☑", "Handoff turno OK", FAINT),
        ("☐", "Checar backup noturno", TEXT),
    ]
    yy = y + 56
    for mark, label, color in items:
        d.text((x + 18, yy), f"{mark}  {label}", fill=color, font=font(13))
        yy += 32
    rr(d, (x + 14, y + 200, x + 280, y + 232), fill=ELEV, outline=LINE, radius=6)
    d.text((x + 24, y + 208), "Nova anotação do turno…", fill=FAINT, font=font(12))
    rr(d, (x + 292, y + 200, x + 346, y + 232), fill=TEAL, outline=TEAL, radius=6)
    d.text((x + 308, y + 208), "+", fill="#06201c", font=font(16, True))


def mock_dashboard() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_sidebar(d, "dashboard")
    draw_header(d, "Visão geral", "Estado operacional · lembretes, wiki e calendário à mão")
    kpis = [("Críticos", "1", RED), ("Warnings", "2", ORANGE), ("Total", "3", BLUE), ("Módulos", "4/5", GREEN)]
    x = 260
    for title, val, color in kpis:
        rr(d, (x, 100, x + 220, 190), fill=SURF, outline=LINE, radius=12)
        d.text((x + 16, 118), title, fill=SOFT, font=font(12))
        d.text((x + 16, 148), val, fill=color, font=font(26, True))
        x += 240
    rr(d, (260, 210, 860, 500), fill=SURF, outline=LINE, radius=12)
    d.text((280, 228), "Distribuição de severidade", fill=TEXT, font=font(14, True))
    bars = [(RED, 110), (ORANGE, 160), (BLUE, 70), (GREEN, 40)]
    bx = 320
    for color, h in bars:
        d.rectangle((bx, 450 - h, bx + 70, 450), fill=color)
        bx += 120
    rr(d, (880, 210, 1410, 500), fill=SURF, outline=LINE, radius=12)
    d.text((900, 228), "Insights", fill=TEXT, font=font(14, True))
    d.text((900, 258), "Atualizado · heurístico", fill=FAINT, font=font(12))
    rr(d, (900, 300, 1390, 380), fill=ELEV, outline=LINE, radius=8)
    d.text((920, 320), "Pico de warning em Zabbix", fill=TEXT, font=font(13, True))
    d.text((920, 348), "Revisar triggers de interface", fill=SOFT, font=font(12))
    rr(d, (900, 420, 1180, 465), fill=ELEV, outline=TEAL, radius=8)
    d.text((930, 434), "Abrir análise completa", fill=TEAL, font=font(12, True))
    rr(d, (260, 520, 1000, 760), fill=SURF, outline=LINE, radius=12)
    d.text((280, 540), "Coletores", fill=TEXT, font=font(14, True))
    d.text((280, 565), "Saúde dos módulos · use Wiki / Calendário nas abas laterais", fill=FAINT, font=font(12))
    rr(d, (780, 540, 980, 575), fill=TEAL_DIM, outline=TEAL, radius=8)
    d.text((800, 550), "Abrir navegador", fill=TEAL, font=font(12, True))
    mods = [("zabbix", GREEN), ("cacti", GREEN), ("nagios", ORANGE), ("topdesk", GREEN)]
    mx = 280
    for name, color in mods:
        rr(d, (mx, 600, mx + 160, 720), fill=ELEV, outline=LINE, radius=8)
        d.text((mx + 14, 630), name, fill=TEXT, font=font(13, True))
        d.text((mx + 14, 665), "● Online" if color == GREEN else "● Atenção", fill=color, font=font(12))
        mx += 175
    draw_edge_tabs(d)
    draw_reminder(d, 1040, 520)
    rr(d, (260, 780, 1410, 860), fill=ELEV, outline=LINE, radius=10)
    d.text(
        (280, 800),
        "Abas laterais: Wiki (esquerda) · Calendário (direita)   ·   Painel flutuante: Lembretes / Anotações (arraste pelo título)",
        fill=SOFT,
        font=font(13),
    )
    save(img, "ciem-portal-dashboard")


def mock_wiki() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_sidebar(d, "dashboard")
    for i in range(3):
        rr(d, (280, 120 + i * 90, 1100, 190 + i * 90), fill="#101820", outline="#243040", radius=10)
    draw_header(d, "Visão geral", "Wiki aberta · documentação colaborativa", wiki=True)
    d.rectangle((232, 0, W, H), fill="#0a1014")
    d.rectangle((232, 0, 900, H), fill=ELEV)
    d.line((900, 0, 900, H), fill=LINE, width=1)
    d.text((256, 28), "Wiki de serviços", fill=TEXT, font=font(22, True))
    d.text((256, 60), "Documentação colaborativa da instituição", fill=FAINT, font=font(13))
    rr(d, (820, 30, 880, 64), fill=SURF, outline=LINE, radius=8)
    d.text((835, 40), "Fechar", fill=SOFT, font=font(11))
    pages = ["Rede", "Monitoramento", "Helpdesk", "Backup", "Acessos"]
    for i, p in enumerate(pages):
        y = 110 + i * 52
        active = i == 0
        rr(d, (256, y, 420, y + 42), fill=TEAL_DIM if active else SURF, outline=TEAL if active else LINE, radius=8)
        d.text((272, y + 12), p, fill=TEAL if active else SOFT, font=font(13, True if active else False))
    rr(d, (256, 390, 420, 430), fill=ELEV, outline=TEAL, radius=8)
    d.text((290, 402), "+ Nova página", fill=TEAL, font=font(12, True))
    rr(d, (440, 110, 880, 820), fill=SURF, outline=LINE, radius=12)
    d.text((460, 130), "Rede e conectividade", fill=TEXT, font=font(18, True))
    d.text((460, 162), "Atualizado por admin · há 2 h", fill=FAINT, font=font(11))
    rr(d, (700, 125, 770, 158), fill=ELEV, outline=LINE, radius=6)
    d.text((718, 134), "Editar", fill=SOFT, font=font(11))
    rr(d, (780, 125, 860, 158), fill=TEAL, outline=TEAL, radius=6)
    d.text((798, 134), "Salvar", fill="#06201c", font=font(11, True))
    d.text((460, 210), "## Rede institucional", fill=TEAL, font=font(15, True))
    lines = [
        "- Gateway padrão: 10.0.0.1",
        "- DNS interno: dns1.instituicao.local",
        "- VPN / ZTNA: acesso via portal CIEM",
        "",
        "### Contatos",
        "- NOC Rede — plantão 24×7",
        "- Mudança: janela acordada",
        "",
        "| Sistema | Uso |",
        "| Firewall | Borda |",
        "| Switch core | LAN |",
    ]
    yy = 250
    for line in lines:
        d.text((460, yy), line, fill=SOFT if line.startswith(("-", "|")) else TEXT, font=font(13))
        yy += 28
    rr(d, (900, 340, 926, 520), fill=TEAL_DIM, outline=TEAL, radius=6)
    for i, ch in enumerate("Wiki"):
        d.text((906, 380 + i * 22), ch, fill=TEAL, font=font(12, True))
    rr(d, (1412, 340, 1438, 540), fill=TEAL_DIM, outline=TEAL, radius=6)
    draw_reminder(d, 980, 560)
    save(img, "ciem-portal-wiki")


def mock_calendar() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_sidebar(d, "dashboard")
    for i in range(3):
        rr(d, (280, 120 + i * 90, 900, 190 + i * 90), fill="#101820", outline="#243040", radius=10)
    draw_header(d, "Visão geral", "Calendário aberto · agenda compartilhada", cal=True)
    d.rectangle((232, 0, W, H), fill="#0a1014")
    d.rectangle((960, 0, W, H), fill=ELEV)
    d.line((960, 0, 960, H), fill=LINE, width=1)
    d.text((984, 28), "Calendário", fill=TEXT, font=font(22, True))
    d.text((984, 60), "Agenda compartilhada · Google ou Microsoft", fill=FAINT, font=font(12))
    rr(d, (1340, 30, 1410, 64), fill=SURF, outline=LINE, radius=8)
    d.text((1355, 40), "Fechar", fill=SOFT, font=font(11))
    for i, (label, active) in enumerate([("Google", True), ("Microsoft", False), ("Configurar", False)]):
        x = 984 + i * 130
        rr(d, (x, 100, x + 120, 136), fill=TEAL_DIM if active else SURF, outline=TEAL if active else LINE, radius=8)
        d.text((x + 22, 110), label, fill=TEAL if active else SOFT, font=font(12, True if active else False))
    rr(d, (984, 160, 1410, 820), fill="#0b1214", outline=LINE, radius=12)
    d.text((1004, 180), "Setembro 2026", fill=TEXT, font=font(16, True))
    days = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
    for i, day in enumerate(days):
        d.text((1010 + i * 56, 220), day, fill=FAINT, font=font(11))
    n = 1
    for row in range(5):
        for col in range(7):
            x0 = 1000 + col * 56
            y0 = 250 + row * 100
            rr(d, (x0, y0, x0 + 50, y0 + 88), fill=SURF, outline=LINE, radius=6)
            if n <= 30:
                d.text((x0 + 8, y0 + 8), str(n), fill=TEXT, font=font(11, True))
                if n in (5, 12, 18, 25):
                    rr(d, (x0 + 6, y0 + 36, x0 + 44, y0 + 56), fill=TEAL_DIM, outline=TEAL, radius=4)
                    d.text((x0 + 10, y0 + 40), "NOC", fill=TEAL, font=font(9))
                if n == 8:
                    rr(d, (x0 + 6, y0 + 60, x0 + 44, y0 + 80), fill="#2a2010", outline=ORANGE, radius=4)
                    d.text((x0 + 10, y0 + 64), "Mud.", fill=ORANGE, font=font(9))
                n += 1
    rr(d, (232, 340, 258, 520), fill=TEAL_DIM, outline=TEAL, radius=6)
    for i, ch in enumerate("Wiki"):
        d.text((238, 380 + i * 22), ch, fill=TEAL, font=font(12, True))
    rr(d, (930, 340, 956, 540), fill=TEAL_DIM, outline=TEAL, radius=6)
    draw_reminder(d, 280, 560)
    save(img, "ciem-portal-calendar")


def mock_reminders() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_sidebar(d, "dashboard")
    draw_header(d, "Visão geral", "Lembretes flutuantes · arraste para qualquer lado")
    for i, (t, v, c) in enumerate(
        [("Críticos", "1", RED), ("Warnings", "2", ORANGE), ("Total", "3", BLUE), ("Módulos", "4/5", GREEN)]
    ):
        x = 260 + i * 240
        rr(d, (x, 100, x + 220, 180), fill=SURF)
        d.text((x + 16, 120), t, fill=SOFT, font=font(12))
        d.text((x + 16, 145), v, fill=c, font=font(22, True))
    rr(d, (260, 200, 900, 480), fill=SURF)
    d.text((280, 220), "Distribuição de severidade", fill=TEXT, font=font(14, True))
    draw_edge_tabs(d)
    draw_reminder(d, 720, 280)
    rr(d, (720, 220, 1080, 265), fill=TEAL_DIM, outline=TEAL, radius=8)
    d.text((740, 234), "↕ Arraste pelo título para reposicionar", fill=TEAL, font=font(13, True))
    rr(d, (260, 520, 680, 760), fill=SURF)
    d.text((280, 540), "Como usar", fill=TEXT, font=font(14, True))
    tips = [
        "1. Arraste o painel para qualquer canto",
        "2. Adicione lembretes ou anotações do turno",
        "3. Marque como concluído ou remova",
        "4. Recolha (–) ou oculte (×); botão Lembretes reabre",
        "5. Dados ficam só neste navegador",
    ]
    yy = 580
    for tip in tips:
        d.text((280, yy), tip, fill=SOFT, font=font(13))
        yy += 28
    save(img, "ciem-portal-reminders")


def main() -> None:
    mock_dashboard()
    mock_wiki()
    mock_calendar()
    mock_reminders()


if __name__ == "__main__":
    main()
