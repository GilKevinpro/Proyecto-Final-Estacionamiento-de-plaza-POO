"""Simulación de hora pico con 3 hilos de entrada y 2 hilos de salida."""

from datetime import timedelta
import random
import threading
import time

from .excepciones import ErrorEstacionamiento
from .modelos import FabricaVehiculos


def simular_hora_pico(gestor, fecha_base, vehiculos_por_puerta=15):
    """Ejecuta 3 entradas y 2 salidas concurrentes usando hilos."""
    resultados = {
        "entradas_exitosas": 0,
        "entradas_rechazadas": 0,
        "salidas_exitosas": 0,
    }
    lock_resultados = threading.Lock()
    placas_activas = []
    lock_placas = threading.Lock()
    entradas_listas = [False]

    def tarea_entrada(num_puerta):
        """Simula una puerta de entrada generando vehículos al azar."""
        rng = random.Random(10 + num_puerta)
        tipos = ["moto", "auto", "camioneta"]
        for i in range(vehiculos_por_puerta):
            tipo = rng.choice(tipos)
            placa = f"HP{num_puerta}-{i:03d}"
            tarjeton = tipo != "moto" and rng.random() < 0.15
            electrico = tipo == "auto" and rng.random() < 0.25
            vehiculo = FabricaVehiculos.crear(tipo, placa, tarjeton, electrico)
            hora_entrada = fecha_base + timedelta(minutes=rng.randint(0, 30))

            try:
                gestor.registrar_entrada(vehiculo, hora_entrada)
                with lock_placas:
                    placas_activas.append(placa)
                with lock_resultados:
                    resultados["entradas_exitosas"] += 1
            except ErrorEstacionamiento:
                with lock_resultados:
                    resultados["entradas_rechazadas"] += 1
            time.sleep(0.005)

    def tarea_salida(num_salida):
        """Simula una puerta de salida retirando vehículos que ya ingresaron."""
        rng = random.Random(50 + num_salida)
        while True:
            with lock_placas:
                quedan_entradas = not entradas_listas[0]
                hay_placas = len(placas_activas) > 0
                placa = None
                if hay_placas and rng.random() < 0.65:
                    indice = rng.randrange(len(placas_activas))
                    placa = placas_activas.pop(indice)

            if not quedan_entradas and not hay_placas and placa is None:
                break

            if placa is not None:
                hora_salida = fecha_base + timedelta(minutes=rng.randint(35, 180))
                ticket = 600.0 if rng.random() < 0.2 else 0.0
                kwh = round(rng.uniform(5.0, 20.0), 1) if rng.random() < 0.2 else 0.0
                try:
                    gestor.registrar_salida(placa, hora_salida, ticket, kwh, False)
                    with lock_resultados:
                        resultados["salidas_exitosas"] += 1
                except ErrorEstacionamiento:
                    pass
            time.sleep(0.006)

    hilos_entrada = [threading.Thread(target=tarea_entrada, args=(p,)) for p in range(1, 4)]
    hilos_salida = [threading.Thread(target=tarea_salida, args=(s,)) for s in range(1, 3)]

    for h in hilos_salida:
        h.start()
    for h in hilos_entrada:
        h.start()

    for h in hilos_entrada:
        h.join()

    with lock_placas:
        entradas_listas[0] = True

    for h in hilos_salida:
        h.join()

    gestor.guardar_estado()
    return resultados
