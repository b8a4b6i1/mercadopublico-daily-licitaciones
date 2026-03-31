# Flux Consultores - Licitaciones Bot

Bot automatizado que extrae licitaciones de MercadoPublico.cl y las publica en GitHub Pages.

**Informe disponible en:** `https://[tu-usuario].github.io/mercadopublico-daily-licitaciones/`

## 📁 Archivos para GitHub

```
mercadopublico-daily-licitaciones/
├── main.py                           (script principal)
├── requirements.txt                  (dependencias)
└── .github/
    └── workflows/
        └── daily-licitaciones.yml    (scheduler automático)
```

## ⚙️ Setup (3 pasos)

**Paso 1:** Copiar archivos
- `main.py` → raíz del repo
- `requirements.txt` → raíz del repo
- `github-workflow.yml` → renombrar a `daily-licitaciones.yml` y copiar a `.github/workflows/`

**Paso 2:** Habilitar GitHub Pages
1. Settings → Pages
2. Source: "Deploy from a branch"
3. Branch: `gh-pages` + `/root`

**Paso 3:** Push
```bash
git add .
git commit -m "Setup licitaciones bot"
git push
```

## 🎬 Ejecución

El bot ejecuta automáticamente **lunes, miércoles y viernes a 10:00 UTC** (~06-07:00 CLT).

Para ejecutar manualmente: Actions → Daily Licitaciones Bot → Run workflow

## 📊 ¿Qué hace?

1. **Scraping**: Extrae licitaciones por categoría OCDS (741214, 741110, 803220, 751000)
2. **Filtrado**: Monto 500-5000 UF, plazo ≥15 días
3. **Scoring**: Calcula relevancia 0-10 basado en:
   - Coincidencia OCDS (+2)
   - Keywords (cambio, comunicación, RRHH, etc.) (+1)
   - Monto óptimo 1000-3000 UF (+1)
   - Plazo amplio >20 días (+1)
   - Sector gobierno (+0.5)
4. **HTML**: Genera tabla visual con cards modernas
5. **Publicación**: Publica automáticamente en GitHub Pages

## 🎨 Diseño

- Cards interactivas con hover effects
- Score badges (Excelente/Bueno/Regular/Bajo)
- Estadísticas en header
- Responsive mobile
- Paleta Flux (azul profesional)
- Animaciones suaves

## 🔧 Troubleshooting

**"Página no existe"**
- Espera 2 minutos después de push
- Verifica Settings → Pages que `gh-pages` está seleccionado

**"Sin resultados"**
- MercadoPublico.cl cambió estructura HTML
- Revisar selectores CSS en `main.py` líneas 104-113
- Inspecciona con F12 en MercadoPublico.cl

**"Workflow falla"**
- Revisa Actions → último run
- Verifica logs del error (ej: timeout, cambio de HTML)

## 📝 Customización

**Cambiar horario (cron):**
Editar `.github/workflows/daily-licitaciones.yml`
```yaml
- cron: "0 14 * * 1,3,5"    # 14:00 UTC en lugar de 10:00 UTC
```

**Agregar categorías:**
Editar `main.py` línea 16
```python
CATEGORIAS_OCDS = ["741214", "741110", "803220", "751000", "nueva"]
```

**Cambiar monto:**
Editar `main.py` líneas 18-21
```python
"monto_min": 800,
"monto_max": 8000,
```

## ⚠️ Riesgos & Limitaciones

- **Web scraping**: MercadoPublico.cl prohíbe en TdS. Uso interno no comercial.
- **Fragilidad**: Cambios HTML requieren ajuste de selectores.
- **Bloqueos IP**: Posible si detectan patrón. Mitigación: 3x/semana, delays.

## 📞 Soporte

Si falla persistentemente:
1. Revisar logs en GitHub Actions
2. Inspeccionar estructura actual de MercadoPublico.cl (F12)
3. Ajustar selectores CSS según sea necesario

---

**Versión:** 2.0 (GitHub Pages)  
**Actualizado:** 31 marzo 2026  
**Estado:** Producción
