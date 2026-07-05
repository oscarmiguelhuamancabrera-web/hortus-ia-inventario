from flask import current_app
from openai import OpenAI
from models.database import execute, query


def responder(pregunta):
    context = query("""
      SELECT p.nombre,p.stock,p.stock_minimo,a.tipo,a.mensaje
      FROM productos p LEFT JOIN alertas a ON a.producto_id=p.id AND a.activa
      WHERE p.activo ORDER BY p.nombre LIMIT 40
    """)
    if not current_app.config["OPENAI_API_KEY"]:
        answer = "El asistente requiere configurar OPENAI_API_KEY. Mientras tanto, revise Alertas y Predicciones para decidir la reposición."
    else:
        client = OpenAI(api_key=current_app.config["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model=current_app.config["OPENAI_MODEL"],
            messages=[
                {"role": "system", "content": "Eres el asistente de inventarios de Hortus S.A. Chincha. Explica alertas, resume y recomienda reposición en español. No inventes datos ni sustituyas el modelo predictivo."},
                {"role": "user", "content": f"Datos actuales: {context}\n\nConsulta: {pregunta}"},
            ],
            temperature=0.2,
        )
        answer = response.choices[0].message.content
    execute("INSERT INTO asistente_historial(usuario_id,pregunta,respuesta) VALUES(NULL,%s,%s)", (pregunta, answer))
    return answer

