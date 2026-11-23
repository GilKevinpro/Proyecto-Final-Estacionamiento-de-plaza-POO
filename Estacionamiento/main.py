"""Punto de entrada por consola para el sistema de estacionamiento."""

import argparse
from datetime import datetime
from pathlib import Path
import sys

from .excepciones import ArchivoDatosError, ErrorEstacionamiento
from .gestor import GestorEstacionamiento
from .modelos import FabricaVehiculos
from .persistencia import RepositorioJSON
from .simulador import simular_hora_pico


def leer_fecha_hora(texto):
    """Convierte 'YYYY-MM-DD HH:MM' en un objeto datetime."""
    try:
        return datetime.strptime(texto.strip(), "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError("Fecha inválida. Use el formato YYYY-MM-DD HH:MM.") from exc


def leer_numero(mensaje, valor_por_defecto=0.0):
    """Lee un número flotante desde consola permitiendo valor por defecto."""
    dato = input(mensaje).strip()
    if not dato:
        return valor_por_defecto
    try:
        return float(dato)
    except ValueError as exc:
        raise ValueError("Debe ingresar un número válido.") from exc


def imprimir_menu():
    """Muestra las opciones del menú principal."""
    print("\n--- SISTEMA DE ESTACIONAMIENTO (FI UNAM - POO) ---")
    print("1. Registrar entrada")
    print("2. Registrar salida")
    print("3. Dar de alta o renovar pensión")
    print("4. Consultar pensión")
    print("5. Mostrar ocupación por nivel y tipo de cajón")
    print("6. Generar corte de caja del día")
    print("7. Simular hora pico (3 entradas y 2 salidas)")
    print("0. Salir")


def main():
    """Ejecuta el programa principal capturando errores controlados."""
    parser = argparse.ArgumentParser(description="Estacionamiento de plaza comercial")
    parser.add_argument(
        "--config",
        default="datos/config_inicial.json",
        help="Ruta del archivo de configuración JSON.",
    )
    parser.add_argument(
        "--estado",
        default="datos/estado_actual.json",
        help="Ruta del archivo de estado JSON.",
    )
    args = parser.parse_args()

    try:
        repo = RepositorioJSON(args.config, args.estado)
        gestor = GestorEstacionamiento(repo)
    except ArchivoDatosError as exc:
        print(f"Error al iniciar el sistema: {exc}")
        sys.exit(1)

    while True:
        imprimir_menu()
        opcion = input("Elige una opción: ").strip()

        try:
            if opcion == "1":
                tipo = input("Tipo (moto / auto / camioneta): ")
                placa = input("Placa: ")
                tarjeton = input("¿Tiene tarjetón de discapacidad? (s/n): ").strip().lower() == "s"
                electrico = input("¿Es auto eléctrico? (s/n): ").strip().lower() == "s"
                fecha = leer_fecha_hora(input("Fecha y hora de entrada (YYYY-MM-DD HH:MM): "))

                vehiculo = FabricaVehiculos.crear(tipo, placa, tarjeton, electrico)
                boleto = gestor.registrar_entrada(vehiculo, fecha)
                print(
                    f"Entrada registrada -> Folio: {boleto.folio}, Placa: {boleto.placa}, "
                    f"Nivel: {boleto.nivel}, Cajón: {boleto.id_cajon} ({boleto.tipo_cajon.value})"
                )

            elif opcion == "2":
                identificador = input("Placa o folio: ")
                fecha = leer_fecha_hora(input("Fecha y hora de salida (YYYY-MM-DD HH:MM): "))
                perdido = input("¿Boleto perdido? (s/n): ").strip().lower() == "s"
                ticket = leer_numero("Monto de ticket de compra (0 si no aplica): ", 0.0)
                kwh = leer_numero("kWh cargados (0 si no aplica): ", 0.0)

                boleto, cobro = gestor.registrar_salida(identificador, fecha, ticket, kwh, perdido)
                print(f"Salida registrada -> Placa: {boleto.placa}, Minutos: {cobro.minutos_totales}")
                print(f"  Estacionamiento: ${cobro.estacionamiento:.2f}")
                print(f"  Carga eléctrica: ${cobro.carga_electrica:.2f}")
                print(f"  Boleto perdido:  ${cobro.boleto_perdido:.2f}")
                print(f"  Total a pagar:   ${cobro.total:.2f}")

            elif opcion == "3":
                placa = input("Placa: ")
                titular = input("Nombre del titular: ")
                tipo = input("Tipo (moto / auto / camioneta): ")
                tarjeton = input("¿Tiene tarjetón de discapacidad? (s/n): ").strip().lower() == "s"
                electrico = input("¿Es auto eléctrico? (s/n): ").strip().lower() == "s"
                meses = int(leer_numero("Meses (por defecto 1): ", 1.0))
                fecha = leer_fecha_hora(input("Fecha de operación (YYYY-MM-DD HH:MM): "))

                vehiculo = FabricaVehiculos.crear(tipo, placa, tarjeton, electrico)
                pension = gestor.alta_o_renovar_pension(placa, titular, vehiculo, fecha, meses)
                print(
                    f"Pensión registrada -> Placa: {pension.placa}, Cajón: {pension.id_cajon}, "
                    f"Vence: {pension.fecha_vencimiento.strftime('%Y-%m-%d %H:%M')}"
                )

            elif opcion == "4":
                placa = input("Placa a consultar: ")
                fecha = leer_fecha_hora(input("Fecha de consulta (YYYY-MM-DD HH:MM): "))
                pension = gestor.consultar_pension(placa)
                estado_pension = "Vigente" if pension.esta_vigente(fecha) else "Vencida"
                print(
                    f"Titular: {pension.titular} | Cajón: {pension.id_cajon} | "
                    f"Vence: {pension.fecha_vencimiento.strftime('%Y-%m-%d %H:%M')} | Estado: {estado_pension}"
                )

            elif opcion == "5":
                ocupacion = gestor.obtener_ocupacion()
                for item in ocupacion:
                    print(f"\nNivel {item['nivel']}:")
                    for nombre_tipo, datos in item["tipos"].items():
                        print(
                            f"  {nombre_tipo}: {datos['ocupados']}/{datos['total']} ocupados "
                            f"(reservados libres: {datos['reservados_libres']}, "
                            f"disponibles: {datos['disponibles']})"
                        )

            elif opcion == "6":
                fecha_str = input("Fecha del corte (YYYY-MM-DD): ").strip()
                fecha_dia = datetime.strptime(fecha_str, "%Y-%m-%d")
                ruta = Path(f"datos/corte_{fecha_str}.txt")
                reporte = gestor.generar_corte_caja(fecha_dia, ruta)
                print(f"\nReporte guardado en {ruta}:\n")
                print(reporte)

            elif opcion == "7":
                fecha = leer_fecha_hora(input("Fecha y hora base (YYYY-MM-DD HH:MM): "))
                cantidad = int(leer_numero("Vehículos por puerta (por defecto 15): ", 15.0))
                antes = gestor.obtener_conteos_actuales()["vehiculos_dentro"]
                res = simular_hora_pico(gestor, fecha, cantidad)
                despues = gestor.obtener_conteos_actuales()

                print("\nResumen de simulación:")
                print(f"  Vehículos dentro antes:  {antes}")
                print(f"  Entradas exitosas:       {res['entradas_exitosas']}")
                print(f"  Entradas rechazadas:     {res['entradas_rechazadas']}")
                print(f"  Salidas exitosas:        {res['salidas_exitosas']}")
                print(f"  Vehículos dentro ahora:  {despues['vehiculos_dentro']}")
                print(f"  Cajones ocupados:        {despues['cajones_ocupados']}")
                balance_ok = (antes + res["entradas_exitosas"] - res["salidas_exitosas"]) == despues["vehiculos_dentro"]
                print(f"  Coincidencia de conteos: {'Sí' if balance_ok else 'No'}")

            elif opcion == "0":
                gestor.guardar_estado()
                print("Estado guardado. Hasta luego.")
                break

            else:
                print("Opción no válida.")

        except (ErrorEstacionamiento, ValueError) as exc:
            print(f"Aviso: {exc}")


if __name__ == "__main__":
    main()

    