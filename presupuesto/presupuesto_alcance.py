# Horas de laboratorio y evidencia que quedan en el modulo
HORAS_DISPONIBLES = 30
# Parte reservada para pruebas, documentacion y defensa
RESERVA_PRUEBAS_DOCS = 0.30
# Parte reservada para imprevistos
MARGEN_IMPREVISTOS = 0.20
# Tareas con tecnologia nueva: usa el mismo factor que en la practica
FACTOR_NOVEDAD = 1.5
CAPAS_OBLIGATORIAS = {"api", "agente", "contenedor"}


funcionalidades = [
    {"id": "RF-01", "horas": 2, "capa": "api",
     "nombre": "Endpoint de consulta con respuesta JSON",
     "tipo": "imprescindible", "novedad": True, "sistema_real": False},
    {"id": "RF-02", "horas": 2.5, "capa": "agente",
     "nombre": "Reporte de calidad post-ETL",
     "tipo": "imprescindible", "novedad": False, "sistema_real": False},
    {"id": "RF-03", "horas": 2.5, "capa": "agente",
     "nombre": "Reporte de resultados de ventas",
     "tipo": "imprescindible", "novedad": False, "sistema_real": False},
    {"id": "RF-04", "horas": 2, "capa": "agente",
     "nombre": "Seleccion del tipo de reporte",
     "tipo": "imprescindible", "novedad": True, "sistema_real": False},
    {"id": "RF-05", "horas": 1.5, "capa": "agente",
     "nombre": "Periodo y datos usados en cada reporte",
     "tipo": "imprescindible", "novedad": False, "sistema_real": False},
    {"id": "RF-06", "horas": 2, "capa": "otra",
     "nombre": "Exportacion de resumen en CSV",
     "tipo": "deseable", "novedad": False, "sistema_real": False},
    {"id": "RF-07", "horas": 3, "capa": "otra",
     "nombre": "Comparacion con periodo anterior",
     "tipo": "deseable", "novedad": False, "sistema_real": False},
    {"id": "RF-08", "horas": 2, "capa": "otra",
     "nombre": "Filtro adicional por categoria",
     "tipo": "deseable", "novedad": False, "sistema_real": False},
    {"id": "RF-09", "horas": 10, "capa": "otra",
     "nombre": "Conexion con sistema real de ventas",
     "tipo": "fuera", "novedad": True, "sistema_real": True},
    {"id": "RF-10", "horas": 8, "capa": "otra",
     "nombre": "Interfaz web con inicio de sesion e historial",
     "tipo": "fuera", "novedad": True, "sistema_real": False},
    {"id": "RF-11", "horas": 6, "capa": "otra",
     "nombre": "Envio automatico por correo o mensajeria",
     "tipo": "fuera", "novedad": True, "sistema_real": True},
    {"id": "RF-12", "horas": 4, "capa": "otra",
     "nombre": "Correccion automatica de datos de origen",
     "tipo": "fuera", "novedad": False, "sistema_real": False},
    {"id": "RNF-04", "horas": 1, "capa": "contenedor",
     "nombre": "Empaquetado y arranque con Docker",
     "tipo": "imprescindible", "novedad": True, "sistema_real": False},
]


def horas_reales(funcionalidad):
    return funcionalidad["horas"] * (
        FACTOR_NOVEDAD if funcionalidad["novedad"] else 1
    )


def presupuesto():
    neto = 1 - RESERVA_PRUEBAS_DOCS - MARGEN_IMPREVISTOS
    return round(HORAS_DISPONIBLES * neto, 2)


def recortar(lista):
    limite = presupuesto()
    usado = 0.0
    dentro, fuera = [], []
    orden = sorted(
        lista,
        key=lambda item: (
            item["tipo"] != "imprescindible",
            horas_reales(item),
        ),
    )
    for funcionalidad in orden:
        horas = horas_reales(funcionalidad)
        if funcionalidad["sistema_real"]:
            fuera.append(
                (funcionalidad, "requiere datos o sistemas reales")
            )
        elif usado + horas <= limite:
            dentro.append(funcionalidad)
            usado += horas
        else:
            fuera.append(
                (funcionalidad, "no cabe en el presupuesto")
            )
    return dentro, fuera, round(usado, 2)


if __name__ == "__main__":
    dentro, fuera, usado = recortar(funcionalidades)
    print(f"Presupuesto neto: {presupuesto():.2f} horas")
    print(f"Horas usadas por el recorte: {usado:.2f}")
    print("\nDentro del presupuesto:")
    for item in dentro:
        print(f"- {item['id']}: {item['nombre']} "
              f"({horas_reales(item):.2f} h)")
    print("\nFuera del presupuesto:")
    for item, motivo in fuera:
        print(f"- {item['id']}: {item['nombre']} [{motivo}]")
