CREATE TABLE IF NOT EXISTS usuarios (
  id BIGSERIAL PRIMARY KEY, nombre VARCHAR(120) NOT NULL, usuario VARCHAR(60) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL, rol VARCHAR(40) NOT NULL DEFAULT 'Operador', activo BOOLEAN DEFAULT TRUE,
  creado_en TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS categorias (
  id BIGSERIAL PRIMARY KEY, nombre VARCHAR(100) UNIQUE NOT NULL, descripcion TEXT,
  activo BOOLEAN DEFAULT TRUE, creado_en TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS proveedores (
  id BIGSERIAL PRIMARY KEY, ruc VARCHAR(20) UNIQUE, razon_social VARCHAR(160) NOT NULL, contacto VARCHAR(120),
  telefono VARCHAR(30), email VARCHAR(120), direccion TEXT, activo BOOLEAN DEFAULT TRUE, creado_en TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS productos (
  id BIGSERIAL PRIMARY KEY, codigo VARCHAR(40) UNIQUE NOT NULL, nombre VARCHAR(160) NOT NULL, descripcion TEXT,
  categoria_id BIGINT REFERENCES categorias(id), proveedor_id BIGINT REFERENCES proveedores(id), unidad VARCHAR(30) DEFAULT 'unidad',
  precio_compra NUMERIC(12,2) DEFAULT 0 CHECK(precio_compra>=0), precio_venta NUMERIC(12,2) DEFAULT 0 CHECK(precio_venta>=0),
  stock NUMERIC(12,2) DEFAULT 0 CHECK(stock>=0), stock_minimo NUMERIC(12,2) DEFAULT 0 CHECK(stock_minimo>=0),
  activo BOOLEAN DEFAULT TRUE, creado_en TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS movimientos_inventario (
  id BIGSERIAL PRIMARY KEY, producto_id BIGINT NOT NULL REFERENCES productos(id), tipo VARCHAR(10) NOT NULL CHECK(tipo IN('ENTRADA','SALIDA')),
  cantidad NUMERIC(12,2) NOT NULL CHECK(cantidad>0), motivo VARCHAR(160), referencia VARCHAR(80), fecha TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS ventas (
  id BIGSERIAL PRIMARY KEY, cliente VARCHAR(160) DEFAULT 'Público general', total NUMERIC(12,2) NOT NULL DEFAULT 0,
  estado VARCHAR(20) DEFAULT 'COMPLETADA', fecha TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS detalle_ventas (
  id BIGSERIAL PRIMARY KEY, venta_id BIGINT NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
  producto_id BIGINT NOT NULL REFERENCES productos(id), cantidad NUMERIC(12,2) NOT NULL CHECK(cantidad>0),
  precio_unitario NUMERIC(12,2) NOT NULL, subtotal NUMERIC(12,2) NOT NULL
);
CREATE TABLE IF NOT EXISTS predicciones (
  id BIGSERIAL PRIMARY KEY, producto_id BIGINT NOT NULL REFERENCES productos(id), fecha_inicio DATE NOT NULL,
  fecha_fin DATE NOT NULL, demanda_estimada NUMERIC(12,2) NOT NULL, stock_proyectado NUMERIC(12,2),
  reposicion_recomendada NUMERIC(12,2) DEFAULT 0, modelo VARCHAR(80), creado_en TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS alertas (
  id BIGSERIAL PRIMARY KEY, producto_id BIGINT NOT NULL REFERENCES productos(id), tipo VARCHAR(80) NOT NULL,
  nivel VARCHAR(20) NOT NULL, mensaje TEXT NOT NULL, activa BOOLEAN DEFAULT TRUE, creado_en TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS asistente_historial (
  id BIGSERIAL PRIMARY KEY, usuario_id BIGINT REFERENCES usuarios(id), pregunta TEXT NOT NULL,
  respuesta TEXT NOT NULL, creado_en TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha);
CREATE INDEX IF NOT EXISTS idx_detalle_producto ON detalle_ventas(producto_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_producto ON movimientos_inventario(producto_id);

