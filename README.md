# Hortus IA

Sistema inteligente de inventarios agrícolas para **Hortus S.A. – Sucursal Chincha**. Incluye catálogo, proveedores, stock, ventas transaccionales, predicción de demanda con `RandomForestRegressor`, alertas, reportes y asistente OpenAI.

## Requisitos

- Python 3.11 o superior
- Un proyecto de Supabase
- Una clave de OpenAI (opcional para el resto del sistema)

## 1. Crear la base de datos en Supabase

1. Cree un proyecto en [Supabase](https://supabase.com).
2. Abra **SQL Editor**, copie todo el contenido de `database/schema.sql` y ejecútelo.
3. En **Project Settings → Database**, copie la cadena de conexión PostgreSQL. Use preferentemente el pooler compatible con IPv4 para Vercel.
4. La aplicación crea el usuario inicial en el primer acceso correcto:
   - Usuario: `admin`
   - Contraseña: `123456`

Cambie esa contraseña para un entorno real. La clave se almacena mediante hash de Werkzeug, nunca en texto plano.

### Cargar datos de prueba

Después de ejecutar `database/schema.sql`, abra una nueva consulta en **SQL Editor**,
copie `database/seed.sql` y ejecútelo. El script crea 8 productos y 180 ventas
históricas con dos detalles cada una. Puede ejecutarse nuevamente: solo recrea los
datos marcados como `DEMO` y conserva los registros reales.

## 2. Ejecución local

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Edite `.env` y configure:

```env
DATABASE_URL=postgresql://...
SECRET_KEY=una-clave-larga-y-aleatoria
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
```

Abra `http://localhost:5000`. Sin `OPENAI_API_KEY`, todos los módulos funcionan salvo la respuesta generativa del asistente.

## 3. Datos y predicciones

Registre categorías, proveedores y productos; luego cargue ventas con fechas históricas. En **Predicciones IA**, seleccione el horizonte y pulse **Entrenar y predecir**.

Por producto, el sistema:

1. Agrupa unidades vendidas por día.
2. Entrena un `RandomForestRegressor` cuando existen al menos cuatro días con ventas.
3. Proyecta demanda y guarda el modelo en `ia/modelos/` en local.
4. Guarda el resultado en `predicciones` y genera alertas según stock, mínimo y demanda.

En Vercel el filesystem es efímero: el archivo `joblib` puede desaparecer entre invocaciones, pero las predicciones quedan persistidas en PostgreSQL. Para producción intensiva conviene guardar modelos en Supabase Storage o entrenarlos en un job externo.

## 4. Despliegue en Vercel

1. Suba el repositorio a GitHub e impórtelo en Vercel.
2. En **Settings → Environment Variables**, agregue `DATABASE_URL`, `SECRET_KEY`, `OPENAI_API_KEY` y `OPENAI_MODEL`.
3. Despliegue. `vercel.json` dirige todas las rutas a `api/index.py`.

También puede usar la CLI:

```bash
npm i -g vercel
vercel
vercel --prod
```

## Estructura

```text
api/index.py             Entrada serverless de Vercel
controllers/             Rutas, autenticación y módulos
models/database.py       Conexión PostgreSQL y consultas
services/                Ventas, inventario y OpenAI
ia/predictor.py          Entrenamiento, predicción y alertas
templates/               Interfaz Flask/Jinja en español
static/                  CSS y JavaScript
database/schema.sql      Esquema PostgreSQL/Supabase
app.py                   Factory y servidor local
```

## Seguridad y operación

- Configure una `SECRET_KEY` segura y rote la contraseña inicial.
- La conexión fuerza SSL hacia PostgreSQL.
- Las consultas de valores usan parámetros; los nombres dinámicos están limitados a una lista interna.
- La venta y el descuento de stock se ejecutan dentro de una sola transacción con bloqueo de fila.
- Para cargas grandes, mueva el entrenamiento a una tarea programada y añada migraciones, CSRF, roles detallados y respaldo automatizado.
