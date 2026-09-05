#!/usr/bin/env python3
"""Gera docs/assets/ciem-architecture-diagram.{png,jpg} com Navegador HTML5 no Portal."""
from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "assets"

W, H = 1600, 1100
BG = "#0c1118"
TEAL, BLUE, ORANGE, GREEN = "#2ec4b6", "#6cb6ff", "#e6a23c", "#7dcea0"
LINE, SURF, ELEV, TEXT, SOFT = "#314559", "#16202c", "#121a24", "#e8eef6", "#9aabbd"


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    path = f"/usr/share/fonts/truetype/dejavu/{name}"
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    ft, fh, fb, fs = font(26, True), font(15, True), font(13, True), font(12)

    def rr(xy, fill, outline=LINE, w=2, r=12):
        d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=w)

    def box(x, y, w, h, title, lines, accent=TEAL, fill=SURF):
        rr((x, y, x + w, y + h), fill=fill, outline=accent, w=2)
        d.text((x + 12, y + 10), title, fill=accent, font=fb)
        yy = y + 32
        for line in lines:
            d.text((x + 12, yy), line, fill=SOFT, font=fs)
            yy += 17

    def arrow(a, b, color=TEAL):
        d.line((*a, *b), fill=color, width=2)
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        for da in (2.6, -2.6):
            d.line(
                (
                    b[0],
                    b[1],
                    b[0] - 9 * math.cos(ang + da),
                    b[1] - 9 * math.sin(ang + da),
                ),
                fill=color,
                width=2,
            )

    d.text((40, 24), "CIEM — Arquitetura ZTNA", fill=TEXT, font=ft)
    d.text(
        (40, 58),
        "Portal com Navegador HTML5 · módulos isolados · Grafana · Guacamole · LDAP/IA opcionais",
        fill=SOFT,
        font=fs,
    )

    box(40, 100, 200, 95, "Usuários", ["admin / observer", "HTTPS"], BLUE, ELEV)
    box(300, 100, 280, 95, "Proxy Nginx (ZTNA)", ["SSL + rotas", "/  /api  /grafana  /guacamole"], TEAL)
    box(
        640,
        90,
        340,
        115,
        "Portal Web + Navegador HTML5",
        [
            "Visão geral · Alarmes · Análise",
            "Navegador: Grafana / URLs / SSO",
            "Config & Sessões (admin)",
        ],
        TEAL,
        "#0f2a2a",
    )
    box(1040, 90, 240, 95, "LDAP / AD", ["Auth opcional", "via portal admin"], ORANGE, ELEV)
    box(1320, 90, 240, 95, "Provedor IA", ["Insights opcionais", "visível a todos"], ORANGE, ELEV)

    arrow((240, 145), (300, 145))
    arrow((580, 145), (640, 145))
    arrow((980, 130), (1040, 130), ORANGE)
    arrow((980, 170), (1320, 150), ORANGE)

    box(640, 250, 340, 100, "Core API", ["Auth · agregação · auditoria", "SSO Guacamole · insights IA"], BLUE)
    arrow((810, 205), (810, 250))
    box(1040, 250, 240, 100, "Grafana", ["Dashboards NOC", "também no Navegador"], GREEN)
    box(1320, 250, 240, 100, "Guacamole", ["SSH/RDP/VNC + guacd", "SSO no Navegador"], TEAL)
    arrow((980, 300), (1040, 300), GREEN)
    arrow((980, 320), (1320, 300), TEAL)

    d.text(
        (40, 390),
        "Módulos coletores isolados (URLs de console disponíveis no Navegador para admin)",
        fill=SOFT,
        font=fs,
    )
    mods = ["zabbix", "cacti", "nagios", "topdesk", "inventory", "syslog"]
    for i, m in enumerate(mods):
        x = 40 + i * 255
        box(x, 420, 240, 78, f"module-{m}", ["coleta → Core", "console via Navegador"], LINE, ELEV)

    arrow((700, 350), (160, 420), SOFT)
    arrow((810, 350), (810, 420), SOFT)
    arrow((920, 350), (1400, 420), SOFT)

    box(640, 560, 340, 85, "Alvos de manutenção", ["Servidores / rede via Guacamole"], TEAL, ELEV)
    arrow((1440, 350), (810, 560), TEAL)

    rr((40, 680, 1560, 860), fill=ELEV, outline=LINE, w=1)
    d.text((56, 698), "Fluxos com o Navegador HTML5", fill=TEAL, font=fh)
    flows = [
        "1. Observer/Admin → Portal → Navegador → /grafana/ (iframe same-origin)",
        "2. Admin → Navegador ou Sessões → SSO Guacamole (iframe ou nova aba)",
        "3. Admin → Navegador → URL do módulo (options.url); se bloquear iframe → abrir ↗",
        "4. Coletores → Core → Portal (KPIs/Análise) e Grafana (dashboards)",
    ]
    yy = 730
    for line in flows:
        d.text((56, yy), line, fill=SOFT, font=fs)
        yy += 28

    rr((40, 890, 1560, 1050), fill=SURF, outline=LINE, w=1)
    d.text((56, 910), "Isolamento", fill=BLUE, font=fh)
    d.text(
        (56, 938),
        "Proxy, Portal, Core, Grafana, Guacamole e cada módulo em container/pod separado.",
        fill=SOFT,
        font=fs,
    )
    d.text((56, 970), "Navegador HTML5", fill=TEAL, font=fh)
    d.text(
        (56, 998),
        "Disponível a todos desde o login. Embute Grafana e (admin) Guacamole/consoles; "
        "fallback para nova aba se X-Frame-Options/CSP bloquear.",
        fill=SOFT,
        font=fs,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png = OUT_DIR / "ciem-architecture-diagram.png"
    jpg = OUT_DIR / "ciem-architecture-diagram.jpg"
    img.save(png, "PNG", optimize=True)
    img.convert("RGB").save(jpg, "JPEG", quality=90, optimize=True)
    print(f"Wrote {png} and {jpg}")


if __name__ == "__main__":
    main()
