# backend/utils/helpers.py
from datetime import datetime
import os
import platform

def get_current_datetime_str() -> str:
    """
    Retorna la fecha y hora actual formateada de manera legible.
    Ejemplo: 'Miércoles, 01 de Julio de 2026, 17:48'
    """
    # Mapeo manual de días y meses en español para no depender de la configuración regional (locale) del sistema operativo
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    
    ahora = datetime.now()
    dia_semana = dias[ahora.weekday()]
    mes = meses[ahora.month - 1]
    
    return f"{dia_semana}, {ahora.day} de {mes} de {ahora.year}, {ahora.strftime('%H:%M')}"

def get_system_info() -> str:
    """
    Retorna información básica sobre el entorno donde corre Nex.
    """
    return f"Sistema: {platform.system()} {platform.release()} | Usuario: {os.getlogin()}"
