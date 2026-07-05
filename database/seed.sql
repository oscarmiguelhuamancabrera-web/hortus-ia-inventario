-- Datos de demostración para Hortus IA
-- Ejecutar DESPUÉS de database/schema.sql en Supabase SQL Editor.
-- Es seguro repetirlo: actualiza catálogos y recrea únicamente las ventas DEMO.

BEGIN;

INSERT INTO categorias (nombre, descripcion)
VALUES
  ('Fertilizantes', 'Productos para nutrición y recuperación del suelo'),
  ('Semillas', 'Semillas certificadas para campañas agrícolas'),
  ('Agroquímicos', 'Productos para protección y manejo del cultivo'),
  ('Bioestimulantes', 'Soluciones biológicas para mejorar el desarrollo vegetal')
ON CONFLICT (nombre) DO UPDATE
SET descripcion = EXCLUDED.descripcion, activo = TRUE;

INSERT INTO proveedores (ruc, razon_social, contacto, telefono, email, direccion)
VALUES
  ('20123456781', 'AgroInsumos del Sur S.A.C.', 'Carlos Mendoza', '956123456', 'ventas@agroinsumos.pe', 'Chincha Alta, Ica'),
  ('20456789126', 'Semillas del Norte E.I.R.L.', 'Ana Torres', '944765321', 'contacto@semillasnorte.pe', 'Lambayeque'),
  ('20678912345', 'AgroChem Perú S.A.C.', 'Luis Ramírez', '987654123', 'pedidos@agrochem.pe', 'Lima'),
  ('20543219876', 'BioAgro Solutions S.A.C.', 'María Flores', '932456789', 'comercial@bioagro.pe', 'Ica')
ON CONFLICT (ruc) DO UPDATE
SET razon_social = EXCLUDED.razon_social,
    contacto = EXCLUDED.contacto,
    telefono = EXCLUDED.telefono,
    email = EXCLUDED.email,
    direccion = EXCLUDED.direccion,
    activo = TRUE;

INSERT INTO productos
  (codigo, nombre, descripcion, categoria_id, proveedor_id, unidad,
   precio_compra, precio_venta, stock, stock_minimo)
VALUES
  ('PRD-0001', 'Urea 46%', 'Fertilizante nitrogenado granulado',
   (SELECT id FROM categorias WHERE nombre='Fertilizantes'),
   (SELECT id FROM proveedores WHERE ruc='20123456781'),
   'kg', 1.55, 2.10, 1250, 500),
  ('PRD-0002', 'Maíz Híbrido INIA 619', 'Semilla híbrida de alto rendimiento',
   (SELECT id FROM categorias WHERE nombre='Semillas'),
   (SELECT id FROM proveedores WHERE ruc='20456789126'),
   'kg', 12.00, 18.00, 320, 500),
  ('PRD-0003', 'Fungicida Cobre Plus', 'Fungicida preventivo de amplio espectro',
   (SELECT id FROM categorias WHERE nombre='Agroquímicos'),
   (SELECT id FROM proveedores WHERE ruc='20678912345'),
   'L', 24.00, 35.00, 85, 100),
  ('PRD-0004', 'Abono Foliar VerdeMax', 'Bioestimulante foliar concentrado',
   (SELECT id FROM categorias WHERE nombre='Bioestimulantes'),
   (SELECT id FROM proveedores WHERE ruc='20543219876'),
   'L', 18.00, 26.00, 420, 200),
  ('PRD-0005', 'Semilla de Soya INIA', 'Semilla certificada para costa peruana',
   (SELECT id FROM categorias WHERE nombre='Semillas'),
   (SELECT id FROM proveedores WHERE ruc='20456789126'),
   'kg', 7.20, 11.50, 200, 180),
  ('PRD-0006', 'Nitrato de Calcio', 'Fertilizante soluble para fertirriego',
   (SELECT id FROM categorias WHERE nombre='Fertilizantes'),
   (SELECT id FROM proveedores WHERE ruc='20123456781'),
   'kg', 3.80, 5.60, 95, 250),
  ('PRD-0007', 'Insecticida Total 1L', 'Control de insectos en hortalizas y frutales',
   (SELECT id FROM categorias WHERE nombre='Agroquímicos'),
   (SELECT id FROM proveedores WHERE ruc='20678912345'),
   'L', 31.00, 45.00, 150, 100),
  ('PRD-0008', 'Bioestimulante Raíz Forte', 'Promotor de raíces de origen biológico',
   (SELECT id FROM categorias WHERE nombre='Bioestimulantes'),
   (SELECT id FROM proveedores WHERE ruc='20543219876'),
   'L', 22.00, 32.00, 600, 150)
ON CONFLICT (codigo) DO UPDATE
SET nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    categoria_id = EXCLUDED.categoria_id,
    proveedor_id = EXCLUDED.proveedor_id,
    unidad = EXCLUDED.unidad,
    precio_compra = EXCLUDED.precio_compra,
    precio_venta = EXCLUDED.precio_venta,
    stock = EXCLUDED.stock,
    stock_minimo = EXCLUDED.stock_minimo,
    activo = TRUE;

-- Limpiar únicamente información demo dependiente.
DELETE FROM alertas
WHERE producto_id IN (SELECT id FROM productos WHERE codigo LIKE 'PRD-000%');

DELETE FROM predicciones
WHERE producto_id IN (SELECT id FROM productos WHERE codigo LIKE 'PRD-000%');

DELETE FROM movimientos_inventario
WHERE referencia LIKE 'DEMO-%';

DELETE FROM ventas
WHERE cliente LIKE 'DEMO - %';

-- Movimientos iniciales de muestra.
INSERT INTO movimientos_inventario
  (producto_id, tipo, cantidad, motivo, referencia, fecha)
SELECT p.id, 'ENTRADA', x.cantidad, 'Carga inicial de demostración',
       'DEMO-INICIAL-' || p.codigo, CURRENT_DATE - INTERVAL '190 days'
FROM (
  VALUES
    ('PRD-0001', 3000::numeric), ('PRD-0002', 1600),
    ('PRD-0003', 700), ('PRD-0004', 1100),
    ('PRD-0005', 900), ('PRD-0006', 800),
    ('PRD-0007', 650), ('PRD-0008', 1200)
) AS x(codigo, cantidad)
JOIN productos p ON p.codigo=x.codigo;

-- Seis meses de ventas: una venta diaria con dos productos.
DO $$
DECLARE
  dia integer;
  venta_actual bigint;
  producto_a bigint;
  producto_b bigint;
  cantidad_a integer;
  cantidad_b integer;
  precio_a numeric;
  precio_b numeric;
BEGIN
  FOR dia IN 1..180 LOOP
    SELECT id, precio_venta INTO producto_a, precio_a
    FROM productos
    WHERE codigo = 'PRD-' || LPAD((((dia - 1) % 8) + 1)::text, 4, '0');

    SELECT id, precio_venta INTO producto_b, precio_b
    FROM productos
    WHERE codigo = 'PRD-' || LPAD((((dia + 2) % 8) + 1)::text, 4, '0');

    cantidad_a := 3 + (dia % 12);
    cantidad_b := 2 + ((dia * 3) % 8);

    INSERT INTO ventas (cliente, total, estado, fecha)
    VALUES (
      'DEMO - Cliente ' || (((dia - 1) % 12) + 1),
      (cantidad_a * precio_a) + (cantidad_b * precio_b),
      'COMPLETADA',
      CURRENT_DATE - (181 - dia) * INTERVAL '1 day' + INTERVAL '10 hours'
    )
    RETURNING id INTO venta_actual;

    INSERT INTO detalle_ventas
      (venta_id, producto_id, cantidad, precio_unitario, subtotal)
    VALUES
      (venta_actual, producto_a, cantidad_a, precio_a, cantidad_a * precio_a),
      (venta_actual, producto_b, cantidad_b, precio_b, cantidad_b * precio_b);

    INSERT INTO movimientos_inventario
      (producto_id, tipo, cantidad, motivo, referencia, fecha)
    VALUES
      (producto_a, 'SALIDA', cantidad_a, 'Venta de demostración',
       'DEMO-VENTA-' || venta_actual,
       CURRENT_DATE - (181 - dia) * INTERVAL '1 day' + INTERVAL '10 hours'),
      (producto_b, 'SALIDA', cantidad_b, 'Venta de demostración',
       'DEMO-VENTA-' || venta_actual,
       CURRENT_DATE - (181 - dia) * INTERVAL '1 day' + INTERVAL '10 hours');
  END LOOP;
END $$;

COMMIT;

-- Resumen de comprobación.
SELECT
  (SELECT COUNT(*) FROM categorias WHERE activo) AS categorias,
  (SELECT COUNT(*) FROM proveedores WHERE activo) AS proveedores,
  (SELECT COUNT(*) FROM productos WHERE activo) AS productos,
  (SELECT COUNT(*) FROM ventas WHERE cliente LIKE 'DEMO - %') AS ventas_demo,
  (SELECT COUNT(*) FROM detalle_ventas d JOIN ventas v ON v.id=d.venta_id
   WHERE v.cliente LIKE 'DEMO - %') AS detalles_demo;
