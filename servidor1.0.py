from flask import Flask, render_template, jsonify, send_from_directory
from datetime import datetime, time
import os
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def cargar_horarios():
    try:
        with open('horarios.json', 'r') as f:
            data = json.load(f)
            parsed_horarios = {}
            for dia, categorias in data.items():
                parsed_dia = int(dia)
                parsed_horarios[parsed_dia] = {}
                for categoria, eventos in categorias.items():
                    if categoria == "pausas_activas":
                        parsed_horarios[parsed_dia][categoria] = {}
                        for pausa_key, lista_pausa in eventos.items():
                            parsed_horarios[parsed_dia][categoria][pausa_key] = [
                                {
                                    "hora_inicio": datetime.strptime(e['hora_inicio'], "%H:%M:%S").time(),
                                    "archivo": e.get('archivo', ''),
                                    "duracion": e.get('duracion', 60)
                                } for e in lista_pausa
                            ]
                    else:
                        parsed_horarios[parsed_dia][categoria] = [
                            {
                                "hora_inicio": datetime.strptime(e['hora_inicio'], "%H:%M:%S").time(),
                                "archivo": e.get('archivo', ''),
                                "duracion": e.get('duracion', 60),
                                "duracion_por_persona": e.get('duracion_por_persona', 60)
                            } for e in eventos
                        ]
            logger.info("Horarios recargados exitosamente desde horarios.json")
            return parsed_horarios
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error al cargar horarios.json: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error inesperado al procesar horarios.json: {e}")
        return {}

@app.route("/")
def base():
    return render_template("base.html")

@app.route("/estado")
def estado():
    try:
        horarios_semanales = cargar_horarios()

        ahora = datetime.now()
        dia_semana = ahora.weekday()
        ahora_time = ahora.time()
        ahora_segundos = ahora_time.hour * 3600 + ahora_time.minute * 60 + ahora_time.second
        
        horarios_hoy = horarios_semanales.get(dia_semana, {})
        
        cumpleaneros_hoy = []
        try:
            with open("cumpleanos.json", "r") as f:
                cumpleanos = json.load(f)
                hoy_str = ahora.strftime("%m-%d")
                cumpleaneros_hoy = [p["nombre"] for p in cumpleanos if p["fecha"] == hoy_str]
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("Archivo cumpleanos.json no encontrado o con formato inválido.")
            
        if "cumpleanos" in horarios_hoy and cumpleaneros_hoy:
            for evento in horarios_hoy["cumpleanos"]:
                inicio = evento["hora_inicio"]
                inicio_segundos = inicio.hour * 3600 + inicio.minute * 60 + inicio.second
                duracion_por_persona = evento.get("duracion_por_persona", 60)
                
                total_duracion = len(cumpleaneros_hoy) * duracion_por_persona
                fin_segundos = inicio_segundos + total_duracion
                
                if ahora_segundos >= inicio_segundos and ahora_segundos <= fin_segundos:
                    segundos_transcurridos = ahora_segundos - inicio_segundos
                    indice_persona = segundos_transcurridos // duracion_por_persona
                    
                    if indice_persona < len(cumpleaneros_hoy):
                        nombre_actual = cumpleaneros_hoy[indice_persona]
                        return jsonify({
                            "activo": True,
                            "tipo": "cumpleanos",
                            "nombre": nombre_actual,
                            "duracion": duracion_por_persona
                        })
        
        if "anuncios_video" in horarios_hoy:
            for evento in horarios_hoy["anuncios_video"]:
                inicio = evento["hora_inicio"]
                inicio_segundos = inicio.hour * 3600 + inicio.minute * 60 + inicio.second
                duracion_evento = evento.get("duracion", 60)
                
                if ahora_segundos >= inicio_segundos and ahora_segundos <= inicio_segundos + duracion_evento:
                    return jsonify({
                        "activo": True,
                        "tipo": "anuncio_video",
                        "archivo": evento["archivo"],
                        "duracion": duracion_evento
                    })
        
        if "pausas_activas" in horarios_hoy:
            for _, lista_pausa in horarios_hoy["pausas_activas"].items():
                for evento in lista_pausa:
                    inicio = evento["hora_inicio"]
                    inicio_segundos = inicio.hour * 3600 + inicio.minute * 60 + inicio.second
                    duracion_evento = evento.get("duracion", 60)
                    
                    if ahora_segundos >= inicio_segundos and ahora_segundos <= inicio_segundos + duracion_evento:
                        return jsonify({
                            "activo": True,
                            "tipo": "pausas_activas",
                            "archivo": evento["archivo"],
                            "duracion": duracion_evento
                        })
        
        logger.info("No hay contenido programado")
        return jsonify({"activo": False})
        
    except Exception as e:
        logger.error(f"Error en /estado: {str(e)}")
        return jsonify({"activo": False, "error": str(e)})

@app.route("/static/<path:filename>")
def serve_static(filename):
    try:
        if ".." in filename or filename.startswith("/"):
            return "Acceso denegado", 403
            
        return send_from_directory("static", filename)
    except FileNotFoundError:
        logger.error(f"Archivo estático no encontrado: {filename}")
        return "Archivo no encontrado", 404
    except Exception as e:
        logger.error(f"Error al servir archivo estático {filename}: {str(e)}")
        return "Error al servir archivo", 500

if __name__ == "__main__":
    os.makedirs("static/js", exist_ok=True)
    os.makedirs("static/avisos", exist_ok=True)
    os.makedirs("static/videos", exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)