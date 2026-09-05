#!/usr/bin/env python3
"""Gera mockups JPG/PNG do portal destacando o Navegador HTML5 na sidebar."""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets"

W, H = 1280, 800
BG = "#0c1118"
SIDE = "#0a1016"
SURF = "#16202c"
ELEV = "#121a24"
LINE = "#314559"
TEXT = "#e8eef6"
SOFT = "#9aabbd"
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


def rr(d: ImageDraw.ImageDraw, xy, fill, outline=LINE, width=1, radius=10):
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def save(img: Image.Image, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f"{stem}.png"
    jpg = OUT / f"{stem}.jpg"
    img.save(png, "PNG", optimize=True)
    img.convert("RGB").save(jpg, "JPEG", quality=90, optimize=True)
    print(f"Wrote {png.name} and {jpg.name}")


def draw_shell(d: ImageDraw.ImageDraw, active: str) -> None:
    d.rectangle((0, 0, 220, H), fill=SIDE)
    d.rectangle((220, 0, W, H), fill=BG)
    d.line((220, 0, 220, H), fill=LINE, width=1)
    ft, fb, fs = font(18, True), font(13, True), font(12)
    d.text((24, 28), "CIEM", fill=TEAL, font=ft)
    d.text((88, 34), "NOC", fill=SOFT, font=fs)

    items = [
        ("dashboard", "Visão geral"),
        ("browser", "Navegador"),
        ("alarms", "Alarmes"),
        ("history", "Histórico"),
        ("analysis", "Análise"),
        ("sessions", "Sessões"),
        ("config", "Configuração"),
    ]
    y = 90
    for key, label in items:
        selected = key == active
        if selected:
            rr(d, (12, y - 8, 208, y + 28), fill=TEAL_DIM, outline=TEAL, width=1, radius=8)
            d.text((28, y), label, fill=TEAL, font=fb)
        else:
            d.text((28, y), label, fill=SOFT, font=fs)
        y += 44

    d.text((24, H - 70), "admin (admin)", fill=SOFT, font=fs)
    rr(d, (24, H - 48, 196, H - 18), fill=ELEV, outline=LINE, width=1, radius=8)
    d.text((78, H - 40), "Sair", fill=SOFT, font=fs)


def mock_login() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    ft, fh, fs = font(42, True), font(20, True), font(14)
    # brand plane
    d.rectangle((0, 0, int(W * 0.55), H), fill="#0a1418")
    d.ellipse((-80, -40, 420, 360), outline=(46, 196, 182, 40), width=2)
    d.text((72, 220), "CIEM", fill=TEAL, font=ft)
    d.text((72, 290), "Centro Integrado de", fill=TEXT, font=fh)
    d.text((72, 322), "Estatística e Manutenção", fill=TEXT, font=fh)
    d.text(
        (72, 380),
        "NOC unificado: alarmes, Navegador HTML5,",
        fill=SOFT,
        font=fs,
    )
    d.text((72, 404), "coletores, sessões auditadas e insights.", fill=SOFT, font=fs)
    # form
    rr(d, (780, 180, 1180, 620), fill=SURF, outline=LINE, width=1, radius=14)
    d.text((820, 220), "Entrar", fill=TEXT, font=fh)
    d.text((820, 280), "Usuário", fill=SOFT, font=fs)
    rr(d, (820, 305, 1140, 345), fill=ELEV, outline=LINE, width=1, radius=8)
    d.text((835, 315), "admin", fill=TEXT, font=fs)
    d.text((820, 370), "Senha", fill=SOFT, font=fs)
    rr(d, (820, 395, 1140, 435), fill=ELEV, outline=LINE, width=1, radius=8)
    d.text((835, 405), "••••••••", fill=TEXT, font=fs)
    rr(d, (820, 480, 1140, 530), fill=TEAL, outline=TEAL, width=1, radius=8)
    d.text((900, 494), "Acessar portal", fill="#06201c", font=font(15, True))
    save(img, "ciem-portal-login")


def mock_dashboard() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_shell(d, "dashboard")
    ft, fh, fs = font(22, True), font(14, True), font(12)
    d.text((248, 28), "Visão geral", fill=TEXT, font=ft)
    d.text((248, 60), "Estado operacional · atalho para o Navegador", fill=SOFT, font=fs)
    rr(d, (980, 28, 1240, 68), fill="#2a1518", outline=RED, width=1, radius=20)
    d.text((1000, 40), "3 alarmes  Abrir", fill=RED, font=fs)

    # KPIs
    kpis = [("Críticos", "1", RED), ("Warnings", "2", ORANGE), ("Total", "3", BLUE), ("Módulos", "4/5", GREEN)]
    x = 248
    for title, val, color in kpis:
        rr(d, (x, 100, x + 220, 190), fill=SURF, outline=LINE, width=1, radius=12)
        d.text((x + 16, 118), title, fill=SOFT, font=fs)
        d.text((x + 16, 148), val, fill=color, font=ft)
        x += 240

    rr(d, (248, 220, 820, 520), fill=SURF, outline=LINE, width=1, radius=12)
    d.text((268, 240), "Distribuição de severidade", fill=TEXT, font=fh)
    bars = [(RED, 90), (ORANGE, 140), (BLUE, 60), (GREEN, 40)]
    bx = 300
    for color, h in bars:
        d.rectangle((bx, 480 - h, bx + 70, 480), fill=color)
        bx += 110

    rr(d, (840, 220, 1240, 520), fill=SURF, outline=LINE, width=1, radius=12)
    d.text((860, 240), "Insights", fill=TEXT, font=fh)
    d.text((860, 270), "Atualizado · heurístico", fill=SOFT, font=fs)
    rr(d, (860, 310, 1220, 390), fill=ELEV, outline=LINE, width=1, radius=8)
    d.text((875, 330), "Pico de warning em Zabbix", fill=TEXT, font=fs)
    d.text((875, 355), "Revisar triggers de interface", fill=SOFT, font=fs)
    rr(d, (860, 430, 1120, 475), fill=ELEV, outline=TEAL, width=1, radius=8)
    d.text((880, 444), "Abrir análise completa", fill=TEAL, font=fs)

    rr(d, (248, 540, 1240, 760), fill=SURF, outline=LINE, width=1, radius=12)
    d.text((268, 560), "Coletores", fill=TEXT, font=fh)
    d.text((268, 585), "Saúde dos módulos · use o Navegador para consoles", fill=SOFT, font=fs)
    rr(d, (1000, 555, 1210, 595), fill=TEAL_DIM, outline=TEAL, width=1, radius=8)
    d.text((1030, 567), "Abrir navegador", fill=TEAL, font=font(13, True))
    mods = [("zabbix", GREEN), ("cacti", GREEN), ("nagios", ORANGE), ("topdesk", GREEN)]
    mx = 268
    for name, color in mods:
        rr(d, (mx, 630, mx + 200, 720), fill=ELEV, outline=LINE, width=1, radius=8)
        d.text((mx + 16, 655), name, fill=TEXT, font=fh)
        d.text((mx + 16, 685), "● Online" if color == GREEN else "● Atenção", fill=color, font=fs)
        mx += 220

    # reminder chip
    rr(d, (980, 700, 1230, 750), fill="#142018", outline=TEAL, width=1, radius=10)
    d.text((1000, 716), "Lembretes · 2 abertos", fill=TEAL, font=fs)
    save(img, "ciem-portal-dashboard")


def mock_browser() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_shell(d, "browser")
    ft, fh, fs = font(22, True), font(14, True), font(12)
    d.text((248, 24), "Navegador", fill=TEXT, font=ft)
    d.text((248, 54), "Grafana, consoles e URLs embutidos no portal", fill=SOFT, font=fs)

    # chrome
    rr(d, (248, 90, 1240, 150), fill=SURF, outline=LINE, width=1, radius=10)
    for i, sym in enumerate(("←", "→", "↻", "⌂")):
        x0 = 260 + i * 42
        rr(d, (x0, 104, x0 + 34, 136), fill=ELEV, outline=LINE, width=1, radius=6)
        d.text((x0 + 10, 112), sym, fill=TEXT, font=fs)
    rr(d, (440, 104, 1120, 136), fill=ELEV, outline=TEAL, width=1, radius=6)
    d.text((455, 112), "/grafana/", fill=TEXT, font=font(13))
    rr(d, (1130, 104, 1185, 136), fill=TEAL, outline=TEAL, width=1, radius=6)
    d.text((1145, 112), "Ir", fill="#06201c", font=font(13, True))
    rr(d, (1195, 104, 1230, 136), fill=ELEV, outline=LINE, width=1, radius=6)
    d.text((1204, 112), "↗", fill=TEAL, font=fs)

    # presets
    chips = ["Início", "Grafana", "Guacamole", "zabbix", "cacti"]
    cx = 248
    for i, label in enumerate(chips):
        active = label == "Grafana"
        rr(
            d,
            (cx, 162, cx + 110, 192),
            fill=TEAL_DIM if active else ELEV,
            outline=TEAL if active else LINE,
            width=1,
            radius=8,
        )
        d.text((cx + 18, 170), label, fill=TEAL if active else SOFT, font=fs)
        cx += 120

    # stage / iframe content
    rr(d, (248, 210, 1240, 760), fill="#0b1214", outline=LINE, width=1, radius=12)
    d.rectangle((248, 210, 1240, 258), fill="#111a22")
    d.text((268, 224), "Grafana · Visão Geral NOC", fill=SOFT, font=fs)
    # fake panels
    panels = [
        (268, 280, 580, 480, "Alarmes ativos", "12"),
        (600, 280, 920, 480, "Severidade", "crit 2 · warn 5"),
        (940, 280, 1220, 480, "Módulos", "5 online"),
        (268, 500, 740, 730, "Tendência 24h", ""),
        (760, 500, 1220, 730, "Top hosts", ""),
    ]
    for x0, y0, x1, y1, title, val in panels:
        rr(d, (x0, y0, x1, y1), fill=SURF, outline=LINE, width=1, radius=8)
        d.text((x0 + 16, y0 + 16), title, fill=SOFT, font=fs)
        if val:
            d.text((x0 + 16, y0 + 70), val, fill=TEXT, font=ft)
        else:
            d.line((x0 + 30, y1 - 40, x1 - 30, y0 + 90), fill=TEAL, width=2)
    save(img, "ciem-portal-browser")


def mock_alarms() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_shell(d, "alarms")
    ft, fh, fs = font(22, True), font(14, True), font(12)
    d.text((248, 28), "Alarmes", fill=TEXT, font=ft)
    d.text((248, 58), "Priorize critical e high", fill=SOFT, font=fs)
    rr(d, (248, 100, 1240, 740), fill=SURF, outline=LINE, width=1, radius=12)
    d.text((268, 120), "Alarmes ativos", fill=TEXT, font=fh)
    rows = [
        (RED, "CRITICAL", "Interface eth0 down — core-sw-01", "zabbix"),
        (ORANGE, "HIGH", "CPU > 90% — app-02", "zabbix"),
        (ORANGE, "WARNING", "Disco 85% — db-01", "cacti"),
        (BLUE, "INFO", "Backup concluído", "topdesk"),
    ]
    y = 170
    for color, sev, msg, mod in rows:
        rr(d, (268, y, 1220, y + 70), fill=ELEV, outline=LINE, width=1, radius=8)
        d.text((288, y + 16), f"[{sev}]", fill=color, font=font(12, True))
        d.text((400, y + 16), msg, fill=TEXT, font=fs)
        d.text((400, y + 40), mod, fill=SOFT, font=fs)
        y += 90
    save(img, "ciem-portal-alarms")


def mock_analysis() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_shell(d, "analysis")
    ft, fh, fs = font(22, True), font(13, True), font(12)
    d.text((248, 24), "Análise", fill=TEXT, font=ft)
    d.text((248, 54), "Gráficos, insights e detalhe filtrado", fill=SOFT, font=fs)
    tabs = ["Resumo", "Insights IA", "Alarmes", "Módulos", "Histórico"]
    x = 248
    for i, t in enumerate(tabs):
        active = i == 0
        rr(
            d,
            (x, 90, x + 110, 122),
            fill=TEAL_DIM if active else SURF,
            outline=TEAL if active else LINE,
            width=1,
            radius=8,
        )
        d.text((x + 18, 98), t, fill=TEAL if active else SOFT, font=fs)
        x += 118
    rr(d, (980, 90, 1110, 122), fill=TEAL_DIM, outline=TEAL, width=1, radius=8)
    d.text((995, 98), "No navegador", fill=TEAL, font=fs)
    rr(d, (1120, 90, 1240, 122), fill=ELEV, outline=LINE, width=1, radius=8)
    d.text((1140, 98), "Grafana ↗", fill=SOFT, font=fs)

    rr(d, (248, 150, 820, 740), fill=SURF, outline=LINE, width=1, radius=12)
    d.text((268, 170), "Gráfico de análise", fill=TEXT, font=fh)
    d.rectangle((300, 520, 360, 680), fill=RED)
    d.rectangle((400, 480, 460, 680), fill=ORANGE)
    d.rectangle((500, 560, 560, 680), fill=BLUE)
    d.rectangle((600, 600, 660, 680), fill=GREEN)

    rr(d, (840, 150, 1240, 740), fill=SURF, outline=LINE, width=1, radius=12)
    d.text((860, 170), "Detalhe", fill=TEXT, font=fh)
    for i, line in enumerate(
        ("Resumo consolidado do turno", "IA: 2 recomendações", "4 módulos online", "Histórico recente OK")
    ):
        y = 220 + i * 70
        rr(d, (860, y, 1220, y + 55), fill=ELEV, outline=LINE, width=1, radius=8)
        d.text((880, y + 18), line, fill=TEXT, font=fs)
    save(img, "ciem-portal-analysis")


def mock_sessions() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_shell(d, "sessions")
    ft, fh, fs = font(22, True), font(14, True), font(12)
    d.text((248, 28), "Sessões", fill=TEXT, font=ft)
    d.text((248, 58), "SSO Guacamole — no navegador ou nova aba", fill=SOFT, font=fs)
    rr(d, (248, 100, 1240, 740), fill=SURF, outline=LINE, width=1, radius=12)
    d.text((268, 120), "Sessões de manutenção", fill=TEXT, font=fh)
    rr(d, (880, 115, 1040, 150), fill=TEAL_DIM, outline=TEAL, width=1, radius=8)
    d.text((900, 125), "No navegador", fill=TEAL, font=fs)
    rr(d, (1050, 115, 1220, 150), fill=TEAL, outline=TEAL, width=1, radius=8)
    d.text((1065, 125), "Guacamole ↗", fill="#06201c", font=font(12, True))
    d.text((268, 180), "Alvos", fill=SOFT, font=fs)
    for i, (name, proto) in enumerate(
        (("core-sw-01", "SSH"), ("fw-edge", "SSH"), ("jump-win", "RDP"))
    ):
        y = 210 + i * 90
        rr(d, (268, y, 1220, y + 75), fill=ELEV, outline=LINE, width=1, radius=8)
        d.text((288, y + 16), name, fill=TEXT, font=fh)
        d.text((288, y + 42), f"{proto} · manutenção", fill=SOFT, font=fs)
        rr(d, (900, y + 20, 1040, y + 55), fill=TEAL_DIM, outline=TEAL, width=1, radius=8)
        d.text((920, y + 30), "No navegador", fill=TEAL, font=fs)
        rr(d, (1055, y + 20, 1200, y + 55), fill=SURF, outline=LINE, width=1, radius=8)
        d.text((1075, y + 30), "Nova aba ↗", fill=SOFT, font=fs)
    save(img, "ciem-portal-sessions")


def mock_config() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_shell(d, "config")
    ft, fh, fs = font(22, True), font(14, True), font(12)
    d.text((248, 28), "Configuração", fill=TEXT, font=ft)
    d.text((248, 58), "Usuários · LDAP · IA · Módulos", fill=SOFT, font=fs)
    sections = ["Usuários", "LDAP", "IA", "Módulos"]
    y = 110
    for i, s in enumerate(sections):
        active = i == 0
        rr(
            d,
            (248, y, 430, y + 44),
            fill=TEAL_DIM if active else SURF,
            outline=TEAL if active else LINE,
            width=1,
            radius=8,
        )
        d.text((270, y + 12), s, fill=TEAL if active else SOFT, font=fs)
        y += 56
    rr(d, (450, 110, 1240, 740), fill=SURF, outline=LINE, width=1, radius=12)
    d.text((480, 140), "Usuários locais", fill=TEXT, font=fh)
    d.text((480, 170), "Independentes do LDAP. Admin padrão: admin", fill=SOFT, font=fs)
    for i, (u, role) in enumerate((("admin", "admin"), ("observador", "observer"))):
        y = 220 + i * 80
        rr(d, (480, y, 1200, y + 65), fill=ELEV, outline=LINE, width=1, radius=8)
        d.text((500, y + 22), f"{u} · {role}", fill=TEXT, font=fs)
    save(img, "ciem-config-interface")


def main() -> None:
    mock_login()
    mock_dashboard()
    mock_browser()
    mock_alarms()
    mock_analysis()
    mock_sessions()
    mock_config()


if __name__ == "__main__":
    main()
