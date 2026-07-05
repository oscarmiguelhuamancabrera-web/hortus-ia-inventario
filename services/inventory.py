from models.database import connection, query


def registrar_venta(cliente, items):
    total = sum(float(i["cantidad"]) * float(i["precio"]) for i in items)
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO ventas(cliente,total) VALUES(%s,%s) RETURNING id", (cliente, total))
            venta_id = cur.fetchone()[0]
            for item in items:
                pid, qty, price = int(item["producto_id"]), int(item["cantidad"]), float(item["precio"])
                cur.execute("SELECT stock,nombre FROM productos WHERE id=%s FOR UPDATE", (pid,))
                product = cur.fetchone()
                if not product or product[0] < qty:
                    raise ValueError(f"Stock insuficiente para {product[1] if product else 'el producto'}")
                cur.execute(
                    "INSERT INTO detalle_ventas(venta_id,producto_id,cantidad,precio_unitario,subtotal) VALUES(%s,%s,%s,%s,%s)",
                    (venta_id, pid, qty, price, qty * price),
                )
                cur.execute("UPDATE productos SET stock=stock-%s WHERE id=%s", (qty, pid))
                cur.execute(
                    "INSERT INTO movimientos_inventario(producto_id,tipo,cantidad,motivo,referencia) VALUES(%s,'SALIDA',%s,'Venta',%s)",
                    (pid, qty, f"VENTA-{venta_id}"),
                )
    return venta_id


def kpis():
    return query("""
        SELECT
          (SELECT COUNT(*) FROM productos WHERE activo) productos,
          (SELECT COALESCE(SUM(stock*precio_compra),0) FROM productos WHERE activo) valor_inventario,
          (SELECT COUNT(*) FROM productos WHERE activo AND stock<=stock_minimo) stock_bajo,
          (SELECT COALESCE(SUM(total),0) FROM ventas WHERE fecha::date=CURRENT_DATE) ventas_hoy
    """, one=True)

