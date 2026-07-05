from datetime import date, timedelta
from pathlib import Path
import os
import tempfile
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from models.database import connection, execute, query

MODEL_DIR = Path(tempfile.gettempdir()) / "hortus-modelos" if os.getenv("VERCEL") else Path(__file__).parent / "modelos"


def entrenar_y_predecir(dias=30):
    rows = query("""
      SELECT d.producto_id, v.fecha::date fecha, SUM(d.cantidad) cantidad
      FROM detalle_ventas d JOIN ventas v ON v.id=d.venta_id
      GROUP BY d.producto_id, v.fecha::date ORDER BY fecha
    """)
    if not rows:
        return 0
    df = pd.DataFrame(rows)
    MODEL_DIR.mkdir(exist_ok=True)
    generated = 0
    for pid, group in df.groupby("producto_id"):
        group["fecha"] = pd.to_datetime(group["fecha"])
        group["dia"] = (group["fecha"] - group["fecha"].min()).dt.days
        if len(group) >= 4:
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(group[["dia"]], group["cantidad"])
            future = np.arange(group["dia"].max() + 1, group["dia"].max() + dias + 1).reshape(-1, 1)
            demand = max(0, round(float(model.predict(future).sum()), 2))
            joblib.dump(model, MODEL_DIR / f"producto_{pid}.joblib")
        else:
            demand = round(float(group["cantidad"].mean() * dias), 2)
        product = query("SELECT stock,stock_minimo FROM productos WHERE id=%s", (int(pid),), one=True)
        recommended = max(0, round(demand + float(product["stock_minimo"]) - float(product["stock"]), 2))
        execute("""
          INSERT INTO predicciones(producto_id,fecha_inicio,fecha_fin,demanda_estimada,stock_proyectado,reposicion_recomendada,modelo)
          VALUES(%s,CURRENT_DATE,%s,%s,%s,%s,'RandomForestRegressor')
        """, (int(pid), date.today()+timedelta(days=dias), demand, float(product["stock"])-demand, recommended))
        generated += 1
    generar_alertas()
    return generated


def generar_alertas():
    execute("UPDATE alertas SET activa=FALSE WHERE activa=TRUE")
    products = query("""
      SELECT p.*, COALESCE(pr.demanda_estimada,0) demanda
      FROM productos p LEFT JOIN LATERAL (
        SELECT demanda_estimada FROM predicciones WHERE producto_id=p.id ORDER BY creado_en DESC LIMIT 1
      ) pr ON TRUE WHERE p.activo
    """)
    for p in products:
        if p["stock"] <= p["stock_minimo"]:
            tipo, nivel, msg = "Stock bajo", "alto", f"{p['nombre']} alcanzó su stock mínimo."
        elif p["stock"] < p["demanda"]:
            tipo, nivel, msg = "Riesgo de desabastecimiento", "critico", f"La demanda estimada supera el stock de {p['nombre']}."
        elif p["stock"] < p["demanda"] + p["stock_minimo"]:
            tipo, nivel, msg = "Reposición recomendada", "medio", f"Conviene reponer {p['nombre']}."
        else:
            tipo, nivel, msg = "Stock suficiente", "bajo", f"{p['nombre']} cuenta con cobertura adecuada."
        execute("INSERT INTO alertas(producto_id,tipo,nivel,mensaje) VALUES(%s,%s,%s,%s)", (p["id"], tipo, nivel, msg))
