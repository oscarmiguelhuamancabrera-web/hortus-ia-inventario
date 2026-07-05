from time import monotonic
from flask import Blueprint, flash, redirect, render_template, request, url_for
from controllers.auth import login_required
from models.database import execute, query
from services.assistant import responder
from services.inventory import kpis, registrar_venta

main_bp = Blueprint("main", __name__)
_dashboard_cache = {"expires": 0, "data": None}


@main_bp.get("/buscar")
@login_required
def buscar():
    term = request.args.get("q", "").strip()
    products, categories, suppliers = [], [], []
    modules = [
        ("Dashboard", "Resumen e indicadores del negocio", "main.dashboard", {}),
        ("Categorías", "Administración de categorías", "main.crud", {"entity": "categorias"}),
        ("Proveedores", "Administración de proveedores", "main.crud", {"entity": "proveedores"}),
        ("Productos", "Catálogo y niveles de stock", "main.productos", {}),
        ("Inventario", "Entradas y salidas de existencias", "main.inventario", {}),
        ("Ventas", "Registro de ventas", "main.ventas", {}),
        ("Predicciones IA", "Pronóstico de demanda", "main.predicciones", {}),
        ("Alertas", "Riesgos y reposición", "main.alertas", {}),
        ("Reportes", "Ventas e inventario valorizado", "main.reportes", {}),
        ("Asistente IA", "Consultas en lenguaje natural", "main.asistente", {}),
    ]
    matching_modules = []
    if term:
        pattern = f"%{term}%"
        products = query("""
          SELECT id,codigo,nombre,stock,unidad FROM productos
          WHERE activo AND (nombre ILIKE %s OR codigo ILIKE %s OR COALESCE(descripcion,'') ILIKE %s)
          ORDER BY nombre LIMIT 20
        """, (pattern, pattern, pattern))
        categories = query("""
          SELECT id,nombre,descripcion FROM categorias
          WHERE activo AND (nombre ILIKE %s OR COALESCE(descripcion,'') ILIKE %s)
          ORDER BY nombre LIMIT 10
        """, (pattern, pattern))
        suppliers = query("""
          SELECT id,ruc,razon_social,contacto FROM proveedores
          WHERE activo AND (razon_social ILIKE %s OR COALESCE(ruc,'') ILIKE %s OR COALESCE(contacto,'') ILIKE %s)
          ORDER BY razon_social LIMIT 10
        """, (pattern, pattern, pattern))
        normalized = term.casefold()
        matching_modules = [m for m in modules if normalized in f"{m[0]} {m[1]}".casefold()]
    return render_template("busqueda.html", term=term, productos=products,
                           categorias=categories, proveedores=suppliers,
                           modulos=matching_modules)


@main_bp.get("/")
@login_required
def dashboard():
    cached = _dashboard_cache["data"] if monotonic() < _dashboard_cache["expires"] else None
    if cached is None:
        stats = kpis()
        monthly = query("""
          SELECT TO_CHAR(date_trunc('month',fecha),'Mon') mes,SUM(total) total
          FROM ventas WHERE fecha>=CURRENT_DATE-INTERVAL '6 months'
          GROUP BY date_trunc('month',fecha) ORDER BY date_trunc('month',fecha)
        """)
        top = query("""
          SELECT p.nombre,SUM(d.cantidad) cantidad FROM detalle_ventas d
          JOIN productos p ON p.id=d.producto_id GROUP BY p.id ORDER BY cantidad DESC LIMIT 5
        """)
        for item in monthly:
            item["total"] = float(item["total"])
        for item in top:
            item["cantidad"] = float(item["cantidad"])
        alerts = query("SELECT a.*,p.nombre producto FROM alertas a JOIN productos p ON p.id=a.producto_id WHERE a.activa ORDER BY a.creado_en DESC LIMIT 6")
        cached = {"stats": stats, "monthly": monthly, "top": top, "alerts": alerts}
        _dashboard_cache.update(data=cached, expires=monotonic() + 30)
    stats, monthly, top, alerts = (cached[k] for k in ("stats", "monthly", "top", "alerts"))
    return render_template("dashboard.html", stats=stats, monthly=monthly, top=top, alerts=alerts)


ENTITY_CONFIG = {
    "categorias": {
        "title": "Categorías", "table": "categorias", "fields": ["nombre", "descripcion"],
        "columns": [("nombre", "Nombre"), ("descripcion", "Descripción")],
    },
    "proveedores": {
        "title": "Proveedores", "table": "proveedores",
        "fields": ["ruc", "razon_social", "contacto", "telefono", "email", "direccion"],
        "columns": [("ruc", "RUC"), ("razon_social", "Razón social"), ("contacto", "Contacto"), ("telefono", "Teléfono"), ("email", "Correo")],
    },
}


@main_bp.route("/gestion/<entity>", methods=["GET", "POST"])
@login_required
def crud(entity):
    cfg = ENTITY_CONFIG.get(entity)
    if not cfg:
        return "Módulo no encontrado", 404
    if request.method == "POST":
        values = [request.form.get(f) or None for f in cfg["fields"]]
        placeholders = ",".join(["%s"] * len(values))
        execute(f"INSERT INTO {cfg['table']} ({','.join(cfg['fields'])}) VALUES ({placeholders})", values)
        flash("Registro guardado correctamente.", "success")
        return redirect(url_for("main.crud", entity=entity))
    if request.args.get("delete"):
        execute(f"UPDATE {cfg['table']} SET activo=FALSE WHERE id=%s", (request.args["delete"],))
        flash("Registro desactivado.", "success")
        return redirect(url_for("main.crud", entity=entity))
    rows = query(f"SELECT * FROM {cfg['table']} WHERE activo ORDER BY id DESC")
    return render_template("crud.html", cfg=cfg, rows=rows, entity=entity)


@main_bp.route("/productos", methods=["GET", "POST"])
@login_required
def productos():
    if request.method == "POST":
        data = tuple(request.form.get(k) or None for k in ("codigo", "nombre", "descripcion", "categoria_id", "proveedor_id", "unidad", "precio_compra", "precio_venta", "stock", "stock_minimo"))
        execute("""INSERT INTO productos(codigo,nombre,descripcion,categoria_id,proveedor_id,unidad,precio_compra,precio_venta,stock,stock_minimo)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", data)
        flash("Producto registrado.", "success")
        return redirect(url_for("main.productos"))
    if request.args.get("delete"):
        execute("UPDATE productos SET activo=FALSE WHERE id=%s", (request.args["delete"],))
        return redirect(url_for("main.productos"))
    rows = query("""SELECT p.*,c.nombre categoria,pr.razon_social proveedor FROM productos p
                    LEFT JOIN categorias c ON c.id=p.categoria_id LEFT JOIN proveedores pr ON pr.id=p.proveedor_id
                    WHERE p.activo ORDER BY p.id DESC""")
    return render_template("productos.html", rows=rows, categorias=query("SELECT * FROM categorias WHERE activo"), proveedores=query("SELECT * FROM proveedores WHERE activo"))


@main_bp.route("/inventario", methods=["GET", "POST"])
@login_required
def inventario():
    if request.method == "POST":
        pid, tipo, cantidad = int(request.form["producto_id"]), request.form["tipo"], int(request.form["cantidad"])
        delta = cantidad if tipo == "ENTRADA" else -cantidad
        from models.database import connection
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE productos SET stock=stock+%s WHERE id=%s AND stock+%s>=0 RETURNING id", (delta, pid, delta))
                if not cur.fetchone():
                    flash("No existe stock suficiente para registrar la salida.", "danger")
                    return redirect(url_for("main.inventario"))
                cur.execute("INSERT INTO movimientos_inventario(producto_id,tipo,cantidad,motivo,referencia) VALUES(%s,%s,%s,%s,%s)",
                            (pid, tipo, cantidad, request.form.get("motivo"), request.form.get("referencia")))
        from ia.predictor import generar_alertas
        generar_alertas()
        flash("Movimiento registrado.", "success")
        return redirect(url_for("main.inventario"))
    movements = query("""SELECT m.*,p.nombre producto FROM movimientos_inventario m JOIN productos p ON p.id=m.producto_id ORDER BY m.fecha DESC LIMIT 100""")
    return render_template("inventario.html", rows=movements, productos=query("SELECT id,nombre,stock FROM productos WHERE activo ORDER BY nombre"))


@main_bp.route("/ventas", methods=["GET", "POST"])
@login_required
def ventas():
    if request.method == "POST":
        item = {"producto_id": request.form["producto_id"], "cantidad": request.form["cantidad"], "precio": request.form["precio"]}
        try:
            registrar_venta(request.form.get("cliente") or "Público general", [item])
            from ia.predictor import generar_alertas
            generar_alertas()
            flash("Venta registrada y stock actualizado.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
        return redirect(url_for("main.ventas"))
    rows = query("SELECT * FROM ventas ORDER BY fecha DESC LIMIT 100")
    products = query("SELECT id,nombre,stock,precio_venta FROM productos WHERE activo AND stock>0 ORDER BY nombre")
    return render_template("ventas.html", rows=rows, productos=products)


@main_bp.route("/predicciones", methods=["GET", "POST"])
@login_required
def predicciones():
    if request.method == "POST":
        from ia.predictor import entrenar_y_predecir
        count = entrenar_y_predecir(int(request.form.get("dias", 30)))
        flash(f"Se generaron {count} predicciones.", "success" if count else "warning")
        return redirect(url_for("main.predicciones"))
    rows = query("""SELECT pr.*,p.nombre producto FROM predicciones pr JOIN productos p ON p.id=pr.producto_id
                    WHERE pr.id IN (SELECT MAX(id) FROM predicciones GROUP BY producto_id) ORDER BY pr.creado_en DESC""")
    return render_template("predicciones.html", rows=rows)


@main_bp.get("/alertas")
@login_required
def alertas():
    return render_template("alertas.html", rows=query("""SELECT a.*,p.nombre producto FROM alertas a JOIN productos p ON p.id=a.producto_id WHERE a.activa ORDER BY CASE nivel WHEN 'critico' THEN 1 WHEN 'alto' THEN 2 WHEN 'medio' THEN 3 ELSE 4 END"""))


@main_bp.get("/reportes")
@login_required
def reportes():
    sales = query("""SELECT v.id,v.fecha,v.cliente,v.total,COUNT(d.id) items FROM ventas v LEFT JOIN detalle_ventas d ON d.venta_id=v.id GROUP BY v.id ORDER BY v.fecha DESC LIMIT 200""")
    stock = query("SELECT nombre,stock,stock_minimo,precio_compra,stock*precio_compra valor FROM productos WHERE activo ORDER BY stock")
    return render_template("reportes.html", sales=sales, stock=stock)


@main_bp.route("/asistente", methods=["GET", "POST"])
@login_required
def asistente():
    answer = None
    if request.method == "POST":
        try:
            answer = responder(request.form["pregunta"])
        except Exception as exc:
            error = str(exc).lower()
            if "insufficient_quota" in error or "exceeded your current quota" in error:
                flash("El Asistente IA no tiene saldo disponible. Revise la facturación y el presupuesto del proyecto en OpenAI Platform.", "warning")
            elif "invalid_api_key" in error or "incorrect api key" in error:
                flash("La clave OPENAI_API_KEY no es válida. Genere una nueva clave y reinicie la aplicación.", "danger")
            elif "rate_limit" in error or "rate limit" in error:
                flash("OpenAI está recibiendo demasiadas solicitudes. Espere unos segundos e inténtelo nuevamente.", "warning")
            else:
                flash("No fue posible consultar al Asistente IA en este momento.", "danger")
    history = query("SELECT * FROM asistente_historial ORDER BY creado_en DESC LIMIT 10")
    return render_template("asistente.html", answer=answer, history=history)
