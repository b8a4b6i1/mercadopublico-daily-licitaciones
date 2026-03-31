#!/usr/bin/env python3
"""
Flux Consultores - Daily Licitaciones Bot
Scraping MercadoPublico.cl → HTML moderno para GitHub Pages
"""

import sys
import logging
import time
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException

# ============ CONFIGURACIÓN ============
MERCADOPUBLICO_BASE = "https://www.mercadopublico.cl"
CATEGORIAS_OCDS = ["741214", "741110", "803220", "751000"]
KEYWORDS_RELEVANCIA = ["cambio", "comunicación", "gestion", "gestión", "rrhh", "capacitación", "transformación", "implementación"]

FILTROS = {
    "monto_min": 500,
    "monto_max": 5000,
    "plazo_min": 15,
}

SCORE_WEIGHTS = {
    "ocds_match": 2,
    "keyword_match": 1,
    "monto_optimo": 1,
    "plazo_amplio": 1,
    "sector": 0.5,
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============ FUNCIONES ============

def obtener_driver_selenium():
    opciones = FirefoxOptions()
    opciones.add_argument("--headless")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    try:
        driver = webdriver.Firefox(options=opciones)
        logger.info("✓ Selenium Firefox iniciado")
        return driver
    except Exception as e:
        logger.error(f"✗ Fallo Selenium: {e}")
        return None

def extraer_licitaciones_categoria(driver, codigo_ocds):
    licitaciones = []
    url = f"{MERCADOPUBLICO_BASE}/Home?catIni={codigo_ocds}&search_type=avanzada"
    try:
        logger.info(f"→ OCDS {codigo_ocds}...")
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table tbody tr")))
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        filas = soup.select("table tbody tr")
        logger.info(f"  → {len(filas)} encontradas")
        for fila in filas:
            try:
                lic = parsear_fila(fila, codigo_ocds)
                if lic:
                    licitaciones.append(lic)
            except:
                continue
        return licitaciones
    except TimeoutException:
        logger.error(f"✗ Timeout {codigo_ocds}")
        return []
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return []

def parsear_fila(fila, codigo_ocds):
    try:
        id_elem = fila.select_one("td:nth-child(1)")
        nombre_elem = fila.select_one("td:nth-child(2) a")
        monto_elem = fila.select_one("td:nth-child(4)")
        fecha_elem = fila.select_one("td:nth-child(5)")
        contratante_elem = fila.select_one("td:nth-child(3)")
        
        if not (id_elem and nombre_elem):
            return None
        
        id_lic = id_elem.get_text(strip=True)
        nombre = nombre_elem.get_text(strip=True)
        enlace = nombre_elem.get("href", "")
        
        try:
            monto = float(monto_elem.get_text(strip=True).replace("UF", "").replace(".", "").replace(",", ".").strip()) if monto_elem else 0
        except:
            monto = 0
        
        fecha = fecha_elem.get_text(strip=True) if fecha_elem else ""
        dias = calcular_dias(fecha)
        contratante = contratante_elem.get_text(strip=True) if contratante_elem else "Desconocido"
        
        return {
            "id": id_lic, "nombre": nombre, "monto_uf": monto, "fecha_cierre": fecha,
            "dias_restantes": dias, "contratante": contratante, "region": extraer_region(contratante),
            "descripcion": nombre, "ocds": codigo_ocds, "enlace": enlace,
        }
    except:
        return None

def calcular_dias(fecha_texto):
    try:
        fecha = datetime.strptime(fecha_texto, "%d/%m/%Y")
        return max(0, (fecha - datetime.now()).days)
    except:
        return 0

def extraer_region(texto):
    regiones = ["Metropolitana", "Valparaíso", "O'Higgins", "Maule", "Ñuble", "Biobío", 
                "La Araucanía", "Los Ríos", "Los Lagos", "Aysén", "Magallanes", "Atacama", 
                "Coquimbo", "Arica", "Antofagasta"]
    for r in regiones:
        if r.lower() in texto.lower():
            return r
    return "Desconocida"

def aplicar_filtros(licitaciones):
    filtradas = [l for l in licitaciones 
                if FILTROS["monto_min"] <= l["monto_uf"] <= FILTROS["monto_max"]
                and l["dias_restantes"] >= FILTROS["plazo_min"]]
    logger.info(f"→ {len(filtradas)} después filtros")
    return filtradas

def calcular_score(lic):
    score = 0
    if lic["ocds"] in CATEGORIAS_OCDS:
        score += SCORE_WEIGHTS["ocds_match"]
    keywords = sum(1 for kw in KEYWORDS_RELEVANCIA if kw in lic["descripcion"].lower())
    score += min(keywords * SCORE_WEIGHTS["keyword_match"], 3)
    if 1000 <= lic["monto_uf"] <= 3000:
        score += SCORE_WEIGHTS["monto_optimo"]
    if lic["dias_restantes"] > 20:
        score += SCORE_WEIGHTS["plazo_amplio"]
    if any(k in lic["contratante"].lower() for k in ["ministerio", "intendencia", "municipio", "seremi"]):
        score += SCORE_WEIGHTS["sector"]
    return min(score, 10)

def generar_html(licitaciones):
    total = len(licitaciones)
    alta_relevancia = len([l for l in licitaciones if l['score'] >= 7])
    monto_min = min([l['monto_uf'] for l in licitaciones], default=0)
    monto_max = max([l['monto_uf'] for l in licitaciones], default=0)
    
    if not licitaciones:
        html_cards = '<div class="empty-state"><p class="empty-icon">📭</p><p>No se encontraron licitaciones que cumplan los filtros hoy.</p></div>'
    else:
        html_cards = ""
        for lic in licitaciones[:30]:
            score = lic["score"]
            if score >= 8:
                badge_class, badge_text = "score-badge score-excellent", "Excelente"
            elif score >= 6:
                badge_class, badge_text = "score-badge score-good", "Bueno"
            elif score >= 4:
                badge_class, badge_text = "score-badge score-fair", "Regular"
            else:
                badge_class, badge_text = "score-badge score-low", "Bajo"
            
            urgencia = "urgente" if lic["dias_restantes"] <= 15 else "normal"
            sector = "🏛️ Gobierno" if any(k in lic["contratante"].lower() 
                                          for k in ["ministerio", "intendencia", "municipio", "seremi"]) else "🏢 Privado"
            
            html_cards += f"""
            <div class="licitacion-card" data-score="{score}">
                <div class="card-header">
                    <div class="card-title-section">
                        <h3 class="card-title">{lic['nombre'][:80]}</h3>
                        <span class="{badge_class}">{badge_text}</span>
                    </div>
                    <a href="{MERCADOPUBLICO_BASE}/Home/EnlacePublico?codigo={lic['id']}" target="_blank" class="card-link">Ver →</a>
                </div>
                <div class="card-content">
                    <p class="contratante">{lic['contratante'][:100]}</p>
                    <div class="card-meta">
                        <div class="meta-item">
                            <span class="meta-label">Monto</span>
                            <span class="meta-value">${lic['monto_uf']:,.0f} UF</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Cierre</span>
                            <span class="meta-value">{lic['fecha_cierre']}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Plazo</span>
                            <span class="meta-value {urgencia}">{lic['dias_restantes']} días</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Región</span>
                            <span class="meta-value">{lic['region']}</span>
                        </div>
                    </div>
                    <div class="card-footer">
                        <span class="sector-badge">{sector}</span>
                        <span class="score-numeric">{score:.1f}/10</span>
                    </div>
                </div>
            </div>
            """
    
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Flux - Licitaciones Públicas</title>
    <style>
        * {{
            margin: 0; padding: 0; box-sizing: border-box;
        }}
        :root {{
            --primary: #1e40af;
            --primary-light: #3b82f6;
            --accent: #f59e0b;
            --success: #10b981;
            --warning: #ef4444;
            --bg-light: #f8fafc;
            --bg-white: #ffffff;
            --text-dark: #1f2937;
            --text-gray: #6b7280;
            --border: #e5e7eb;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
            color: var(--text-dark);
            line-height: 1.6;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        .header {{
            background: var(--bg-white);
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 40px;
            border-left: 6px solid var(--primary);
            animation: slideDown 0.5s ease-out;
        }}
        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .header h1 {{
            font-size: 32px;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 10px;
        }}
        .header p {{
            color: var(--text-gray);
            font-size: 14px;
        }}
        .header-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}
        .stat-card {{
            padding: 20px;
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius: 8px;
            border-left: 4px solid var(--primary);
            animation: fadeInUp 0.6s ease-out forwards;
            opacity: 0;
        }}
        .stat-card:nth-child(1) {{ animation-delay: 0.1s; }}
        .stat-card:nth-child(2) {{ animation-delay: 0.2s; }}
        .stat-card:nth-child(3) {{ animation-delay: 0.3s; }}
        .stat-card:nth-child(4) {{ animation-delay: 0.4s; }}
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: 700;
            color: var(--primary);
            display: block;
        }}
        .stat-label {{
            font-size: 12px;
            color: var(--text-gray);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .filters-info {{
            background: var(--bg-white);
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            border: 1px solid var(--border);
            font-size: 13px;
            color: var(--text-gray);
        }}
        .filters-info strong {{
            color: var(--primary);
        }}
        .licitaciones-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }}
        .licitacion-card {{
            background: var(--bg-white);
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            animation: scaleIn 0.5s ease-out forwards;
            opacity: 0;
            border-left: 4px solid var(--border);
        }}
        @keyframes scaleIn {{
            from {{ opacity: 0; transform: scale(0.95); }}
            to {{ opacity: 1; transform: scale(1); }}
        }}
        .licitacion-card:hover {{
            transform: translateY(-8px);
            box-shadow: 0 10px 15px rgba(0,0,0,0.1);
        }}
        .licitacion-card[data-score="9"],
        .licitacion-card[data-score="10"] {{ border-left-color: var(--success); }}
        .licitacion-card[data-score="7"],
        .licitacion-card[data-score="8"] {{ border-left-color: var(--primary); }}
        .licitacion-card[data-score="5"],
        .licitacion-card[data-score="6"] {{ border-left-color: var(--accent); }}
        .card-header {{
            padding: 24px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
            border-bottom: 1px solid var(--border);
        }}
        .card-title-section {{
            flex: 1;
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }}
        .card-title {{
            font-size: 16px;
            font-weight: 600;
            color: var(--text-dark);
            line-height: 1.4;
            margin: 0;
        }}
        .card-link {{
            color: var(--primary);
            text-decoration: none;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
            padding: 6px 12px;
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius: 4px;
            transition: all 0.2s;
        }}
        .card-link:hover {{
            background: var(--primary);
            color: white;
        }}
        .score-badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }}
        .score-excellent {{ background: #dcfce7; color: #166534; }}
        .score-good {{ background: #dbeafe; color: #1e40af; }}
        .score-fair {{ background: #fef3c7; color: #92400e; }}
        .score-low {{ background: #fee2e2; color: #991b1b; }}
        .card-content {{
            padding: 24px;
        }}
        .contratante {{
            font-size: 13px;
            color: var(--text-gray);
            margin-bottom: 16px;
            font-style: italic;
        }}
        .card-meta {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-bottom: 20px;
        }}
        .meta-item {{
            display: flex;
            flex-direction: column;
        }}
        .meta-label {{
            font-size: 11px;
            color: var(--text-gray);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }}
        .meta-value {{
            font-size: 14px;
            font-weight: 600;
            color: var(--text-dark);
            font-family: 'Courier New', monospace;
        }}
        .meta-value.urgente {{ color: var(--warning); }}
        .meta-value.normal {{ color: var(--success); }}
        .card-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 16px;
            border-top: 1px solid var(--border);
        }}
        .sector-badge {{
            font-size: 12px;
            font-weight: 600;
            color: var(--text-gray);
        }}
        .score-numeric {{
            font-size: 16px;
            font-weight: 700;
            color: var(--primary);
            font-family: 'Courier New', monospace;
        }}
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            background: var(--bg-white);
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .empty-icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        .empty-state p {{
            font-size: 16px;
            color: var(--text-gray);
        }}
        .footer {{
            background: var(--bg-white);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            font-size: 12px;
            color: var(--text-gray);
            line-height: 1.8;
        }}
        .footer h3 {{
            color: var(--primary);
            margin-bottom: 10px;
            font-size: 14px;
        }}
        .footer p {{
            margin-bottom: 10px;
        }}
        .footer strong {{
            color: var(--text-dark);
        }}
        @media (max-width: 768px) {{
            .container {{ padding: 20px 16px; }}
            .header {{ padding: 24px; }}
            .header h1 {{ font-size: 24px; }}
            .header-stats {{ grid-template-columns: repeat(2, 1fr); gap: 16px; }}
            .licitaciones-grid {{ grid-template-columns: 1fr; }}
            .card-meta {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Licitaciones Públicas</h1>
            <p>Flux Consultores | Análisis automatizado de oportunidades en MercadoPublico.cl</p>
            <div class="header-stats">
                <div class="stat-card">
                    <span class="stat-value">{total}</span>
                    <span class="stat-label">Encontradas</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">{alta_relevancia}</span>
                    <span class="stat-label">Alta relevancia</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${monto_min:,.0f}</span>
                    <span class="stat-label">Monto mínimo</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${monto_max:,.0f}</span>
                    <span class="stat-label">Monto máximo</span>
                </div>
            </div>
        </div>
        <div class="filters-info">
            <strong>⚙️ Filtros:</strong> Monto 500-5000 UF | Plazo ≥15 días | OCDS: 741214, 741110, 803220, 751000 | Todas las regiones
        </div>
        <div class="licitaciones-grid">
            {html_cards}
        </div>
        <div class="footer">
            <h3>📊 Metodología del score</h3>
            <p><strong>Coincidencia OCDS (+2):</strong> Categoría alineada con servicios Flux</p>
            <p><strong>Keywords (+1):</strong> Descripción contiene términos de cambio, comunicación, RRHH, etc.</p>
            <p><strong>Monto óptimo (+1):</strong> Rango 1000-3000 UF</p>
            <p><strong>Plazo amplio (+1):</strong> Más de 20 días para postular</p>
            <p><strong>Sector gobierno (+0.5):</strong> Instituciones públicas</p>
            <h3 style="margin-top: 20px;">🔄 Próxima actualización</h3>
            <p><strong>Lunes, miércoles y viernes a 10:00 UTC</strong> (~06-07:00 CLT según estación)</p>
            <h3 style="margin-top: 20px;">⚠️ Nota importante</h3>
            <p>Este reporte es automatizado. Antes de postular, verificar en MercadoPublico.cl que se cumplen todos los requisitos, experiencia previa y certificaciones específicas.</p>
            <p style="margin-top: 15px; font-size: 11px; color: #999;">Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} CLT</p>
        </div>
    </div>
</body>
</html>
"""
    return html

def guardar_html(html_content):
    try:
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("✓ HTML guardado")
        return True
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False

def main():
    logger.info("=" * 60)
    logger.info("FLUX CONSULTORES - LICITACIONES BOT")
    logger.info("=" * 60)
    
    driver = obtener_driver_selenium()
    if not driver:
        return False
    
    try:
        logger.info("\n[1] SCRAPING")
        todas = []
        for codigo in CATEGORIAS_OCDS:
            lics = extraer_licitaciones_categoria(driver, codigo)
            todas.extend(lics)
            time.sleep(3)
        logger.info(f"→ Total: {len(todas)}")
        
        logger.info("\n[2] FILTRADO")
        filtradas = aplicar_filtros(todas)
        
        logger.info("\n[3] SCORING")
        for lic in filtradas:
            lic["score"] = calcular_score(lic)
        ordenadas = sorted(filtradas, key=lambda x: x["score"], reverse=True)
        
        if ordenadas:
            logger.info(f"→ Top 5:")
            for i, lic in enumerate(ordenadas[:5], 1):
                logger.info(f"  {i}. [{lic['score']:.1f}] {lic['nombre'][:50]}...")
        
        logger.info("\n[4] HTML")
        html = generar_html(ordenadas)
        exito = guardar_html(html)
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ ÉXITO" if exito else "✗ ERROR")
        logger.info("=" * 60)
        
        return exito
    finally:
        driver.quit()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
