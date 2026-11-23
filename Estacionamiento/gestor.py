"""Lógica principal del estacionamiento protegida con candado para hilos."""

from datetime import datetime, timedelta
from pathlib import Path
import threading

from .excepciones import (
    ArchivoDatosError,
    BoletoNoEncontradoError,
    CapacidadAgotadaError,
    PensionError,
    VehiculoDuplicadoError,
)

from .modelos import Boleto, Pension, RegistroMovimiento, TipoCajon

from .tarifas import (
    CobroBoletoPerdido,
    CobroPensionadoVigente,
    CobroVisitanteEstandar,
)

class GestorEstacionamiento:
    """Coordina entradas, salidas, pensiones, ocupación, cortes de caja y persistencia."""

    def __init__(self, repositorio, auto_guardar=True):
        """Carga configuración y estado previo e inicializa el candado de sincronización."""
        self._repositorio = repositorio
        self._auto_guardar = auto_guardar
        self._lock = threading.Lock()

        self._niveles, self._tarifas = self._repositorio.cargar_configuracion()
        self._cajones_por_id = {}
        for nivel in self._niveles:
            for cajon in nivel.cajones:
                self._cajones_por_id[cajon.id_cajon] = cajon

        self._consecutivo_folio = 1
        self._boletos_activos = {}
        self._pensiones = {}
        self._historial = []

        self._cargar_datos_guardados()

    def _cargar_datos_guardados(self):
        """Reconstruye pensiones, boletos activos e historial desde el repositorio."""
        estado = self._repositorio.cargar_estado()
        try:
            self._consecutivo_folio = int(estado.get("consecutivo_folio", 1))

            for p_data in estado.get("pensiones", []):
                pension = Pension(
                    placa=p_data["placa"],
                    titular=p_data["titular"],
                    id_cajon=p_data["id_cajon"],
                    fecha_vencimiento=datetime.fromisoformat(p_data["fecha_vencimiento"]),
                )
                self._pensiones[pension.placa] = pension
                if pension.id_cajon in self._cajones_por_id:
                    self._cajones_por_id[pension.id_cajon].reservado_pension = True

            for b_data in estado.get("boletos_activos", []):
                boleto = Boleto(
                    folio=b_data["folio"],
                    placa=b_data["placa"],
                    tipo_vehiculo=b_data["tipo_vehiculo"],
                    id_cajon=b_data["id_cajon"],
                    nivel=int(b_data["nivel"]),
                    tipo_cajon=TipoCajon(b_data["tipo_cajon"]),
                    hora_entrada=datetime.fromisoformat(b_data["hora_entrada"]),
                    es_pensionado=bool(b_data.get("es_pensionado", False)),
                    tiene_tarjeton=bool(b_data.get("tiene_tarjeton", False)),
                    es_electrico=bool(b_data.get("es_electrico", False)),
                )
                self._boletos_activos[boleto.placa] = boleto
                if boleto.id_cajon in self._cajones_por_id:
                    cajon = self._cajones_por_id[boleto.id_cajon]
                    cajon.ocupado = True
                    cajon.placa_actual = boleto.placa

            for h_data in estado.get("historial", []):
                mov = RegistroMovimiento(
                    fecha_hora=datetime.fromisoformat(h_data["fecha_hora"]),
                    tipo_operacion=h_data["tipo_operacion"],
                    placa=h_data["placa"],
                    tipo_vehiculo=h_data["tipo_vehiculo"],
                    monto_estacionamiento=h_data.get("monto_estacionamiento", 0.0),
                    monto_carga_electrica=h_data.get("monto_carga_electrica", 0.0),
                    monto_boleto_perdido=h_data.get("monto_boleto_perdido", 0.0),
                    monto_pension=h_data.get("monto_pension", 0.0),
                )
                self._historial.append(mov)
        except (KeyError, TypeError, ValueError) as exc:
            raise ArchivoDatosError(f"Error al reconstruir el estado guardado: {exc}") from exc

    def _guardar_sin_lock(self):
        """Guarda el estado asumiendo que el hilo ya adquirió el candado."""
        self._repositorio.guardar_estado(
            self._consecutivo_folio,
            list(self._boletos_activos.values()),
            list(self._pensiones.values()),
            self._historial,
        )

    def guardar_estado(self):
        """Persiste el estado actual de forma segura entre hilos."""
        with self._lock:
            self._guardar_sin_lock()

    def registrar_entrada(self, vehiculo, fecha_hora):
        """Asigna un cajón compatible del nivel más bajo y emite un boleto."""
        with self._lock:
            if vehiculo.placa in self._boletos_activos:
                raise VehiculoDuplicadoError(
                    f"El vehículo con placa {vehiculo.placa} ya está dentro del estacionamiento."
                )

            cajon_asignado = None
            es_pensionado_vigente = False

            pension = self._pensiones.get(vehiculo.placa)
            if pension and pension.esta_vigente(fecha_hora):
                cajon_reservado = self._cajones_por_id.get(pension.id_cajon)
                if cajon_reservado and not cajon_reservado.ocupado:
                    cajon_asignado = cajon_reservado
                    es_pensionado_vigente = True

            if cajon_asignado is None:
                for nivel in self._niveles:
                    for tipo_deseado in vehiculo.tipos_cajon_compatibles():
                        for cajon in nivel.cajones:
                            if (
                                not cajon.ocupado
                                and not cajon.reservado_pension
                                and cajon.tipo == tipo_deseado
                            ):
                                cajon_asignado = cajon
                                break
                        if cajon_asignado is not None:
                            break
                    if cajon_asignado is not None:
                        break

            if cajon_asignado is None:
                raise CapacidadAgotadaError(
                    f"No hay cajones compatibles disponibles para {vehiculo.tipo_nombre} ({vehiculo.placa})."
                )

            cajon_asignado.ocupado = True
            cajon_asignado.placa_actual = vehiculo.placa

            folio = f"FOL-{self._consecutivo_folio:06d}"
            self._consecutivo_folio += 1

            boleto = Boleto(
                folio=folio,
                placa=vehiculo.placa,
                tipo_vehiculo=vehiculo.tipo_nombre,
                id_cajon=cajon_asignado.id_cajon,
                nivel=cajon_asignado.nivel,
                tipo_cajon=cajon_asignado.tipo,
                hora_entrada=fecha_hora,
                es_pensionado=es_pensionado_vigente,
                tiene_tarjeton=vehiculo.tiene_tarjeton,
                es_electrico=vehiculo.es_electrico,
            )
            self._boletos_activos[vehiculo.placa] = boleto

            self._historial.append(
                RegistroMovimiento(
                    fecha_hora=fecha_hora,
                    tipo_operacion="ENTRADA",
                    placa=vehiculo.placa,
                    tipo_vehiculo=vehiculo.tipo_nombre,
                )
            )

            if self._auto_guardar:
                self._guardar_sin_lock()
            return boleto

    def registrar_salida(
        self,
        identificador,
        fecha_hora,
        monto_ticket_compra=0.0,
        kwh_cargados=0.0,
        boleto_perdido=False,
    ):
        """Calcula el cobro, libera el cajón y registra la salida."""
        if float(monto_ticket_compra) < 0 or float(kwh_cargados) < 0:
            raise ValueError("El monto de compra y los kWh cargados no pueden ser negativos.")

        with self._lock:
            clave = identificador.strip().upper()
            boleto = self._boletos_activos.get(clave)
            if boleto is None:
                for b in self._boletos_activos.values():
                    if b.folio.upper() == clave:
                        boleto = b
                        break

            if boleto is None:
                raise BoletoNoEncontradoError(
                    f"No se encontró un vehículo activo con placa o folio '{identificador}'."
                )

            pension = self._pensiones.get(boleto.placa)
            if pension and pension.esta_vigente(fecha_hora):
                estrategia = CobroPensionadoVigente()
            elif boleto_perdido:
                estrategia = CobroBoletoPerdido()
            else:
                estrategia = CobroVisitanteEstandar()

            desglose = estrategia.calcular(
                boleto=boleto,
                hora_salida=fecha_hora,
                config=self._tarifas,
                monto_ticket_compra=monto_ticket_compra,
                kwh_cargados=kwh_cargados,
            )

            cajon = self._cajones_por_id[boleto.id_cajon]
            cajon.ocupado = False
            cajon.placa_actual = None
            del self._boletos_activos[boleto.placa]

            self._historial.append(
                RegistroMovimiento(
                    fecha_hora=fecha_hora,
                    tipo_operacion="SALIDA",
                    placa=boleto.placa,
                    tipo_vehiculo=boleto.tipo_vehiculo,
                    monto_estacionamiento=desglose.estacionamiento,
                    monto_carga_electrica=desglose.carga_electrica,
                    monto_boleto_perdido=desglose.boleto_perdido,
                )
            )

            if self._auto_guardar:
                self._guardar_sin_lock()
            return boleto, desglose

    def alta_o_renovar_pension(self, placa, titular, vehiculo, fecha_actual, meses=1):
        """Da de alta una nueva pensión o renueva una existente."""
        meses_num = int(meses)
        if meses_num <= 0:
            raise PensionError("Los meses de pensión deben ser mayores que cero.")

        with self._lock:
            placa_limpia = placa.strip().upper()
            titular_limpio = titular.strip()
            if not placa_limpia or not titular_limpio:
                raise PensionError("Debe indicar la placa y el nombre del titular.")

            monto_pension = self._tarifas.tarifa_pension_mensual * meses_num
            dias = 30 * meses_num

            if placa_limpia in self._pensiones:
                pension = self._pensiones[placa_limpia]
                base = fecha_actual if fecha_actual > pension.fecha_vencimiento else pension.fecha_vencimiento
                pension.fecha_vencimiento = base + timedelta(days=dias)
                pension.titular = titular_limpio
            else:
                cajon_libre = None
                for nivel in self._niveles:
                    for tipo_c in vehiculo.tipos_cajon_compatibles():
                        for cajon in nivel.cajones:
                            if not cajon.ocupado and not cajon.reservado_pension and cajon.tipo == tipo_c:
                                cajon_libre = cajon
                                break
                        if cajon_libre is not None:
                            break
                    if cajon_libre is not None:
                        break

                if cajon_libre is None:
                    raise CapacidadAgotadaError("No hay cajones disponibles para asignar una pensión.")

                cajon_libre.reservado_pension = True
                pension = Pension(
                    placa=placa_limpia,
                    titular=titular_limpio,
                    id_cajon=cajon_libre.id_cajon,
                    fecha_vencimiento=fecha_actual + timedelta(days=dias),
                )
                self._pensiones[placa_limpia] = pension

            self._historial.append(
                RegistroMovimiento(
                    fecha_hora=fecha_actual,
                    tipo_operacion="PENSION",
                    placa=placa_limpia,
                    tipo_vehiculo=vehiculo.tipo_nombre,
                    monto_pension=monto_pension,
                )
            )

            if self._auto_guardar:
                self._guardar_sin_lock()
            return pension

    def consultar_pension(self, placa):
        """Busca y devuelve la pensión registrada para una placa."""
        with self._lock:
            placa_limpia = placa.strip().upper()
            if placa_limpia not in self._pensiones:
                raise PensionError(f"No existe una pensión registrada para la placa {placa_limpia}.")
            return self._pensiones[placa_limpia]

    def obtener_ocupacion(self):
        """Devuelve la ocupación por nivel y por tipo de cajón."""
        with self._lock:
            resumen = []
            for nivel in self._niveles:
                por_tipo = {}
                for tipo in TipoCajon:
                    cajones_tipo = [c for c in nivel.cajones if c.tipo == tipo]
                    ocupados = sum(1 for c in cajones_tipo if c.ocupado)
                    reservados = sum(1 for c in cajones_tipo if c.reservado_pension and not c.ocupado)
                    por_tipo[tipo.value] = {
                        "total": len(cajones_tipo),
                        "ocupados": ocupados,
                        "reservados_libres": reservados,
                        "disponibles": len(cajones_tipo) - ocupados - reservados,
                    }
                resumen.append({"nivel": nivel.numero, "tipos": por_tipo})
            return resumen

    def generar_corte_caja(self, fecha_dia, ruta_salida):
        """Genera y guarda el archivo de corte de caja para una fecha dada."""
        with self._lock:
            dia = fecha_dia.date()
            movimientos = [m for m in self._historial if m.fecha_hora.date() == dia]

            entradas = sum(1 for m in movimientos if m.tipo_operacion == "ENTRADA")
            salidas = sum(1 for m in movimientos if m.tipo_operacion == "SALIDA")

            por_vehiculo = {"moto": 0.0, "auto": 0.0, "camioneta": 0.0}
            por_concepto = {
                "Estacionamiento": 0.0,
                "Carga eléctrica": 0.0,
                "Boleto perdido": 0.0,
                "Pensiones": 0.0,
            }

            for m in movimientos:
                if m.tipo_vehiculo in por_vehiculo:
                    por_vehiculo[m.tipo_vehiculo] += m.total
                por_concepto["Estacionamiento"] += m.monto_estacionamiento
                por_concepto["Carga eléctrica"] += m.monto_carga_electrica
                por_concepto["Boleto perdido"] += m.monto_boleto_perdido
                por_concepto["Pensiones"] += m.monto_pension

            total = sum(por_concepto.values())

            lineas = [
                "==========================================",
                f"CORTE DE CAJA - {dia.isoformat()}",
                "==========================================",
                f"Entradas: {entradas}",
                f"Salidas:  {salidas}",
                "",
                "Ingresos por concepto:",
            ]
            for concepto, monto in por_concepto.items():
                lineas.append(f"  - {concepto}: ${monto:.2f}")

            lineas.append("")
            lineas.append("Ingresos por tipo de vehículo:")
            for tipo_v, monto in por_vehiculo.items():
                lineas.append(f"  - {tipo_v}: ${monto:.2f}")

            lineas.append("------------------------------------------")
            lineas.append(f"Total del día: ${total:.2f}")

            texto = "\n".join(lineas)
            destino = Path(ruta_salida)
            destino.parent.mkdir(parents=True, exist_ok=True)
            with open(destino, "w", encoding="utf-8") as archivo:
                archivo.write(texto)
            return texto

    def obtener_conteos_actuales(self):
        """Devuelve conteos de vehículos dentro y cajones ocupados."""
        with self._lock:
            ocupados = sum(1 for c in self._cajones_por_id.values() if c.ocupado)
            placas = [c.placa_actual for c in self._cajones_por_id.values() if c.placa_actual is not None]
            return {
                "vehiculos_dentro": len(self._boletos_activos),
                "cajones_ocupados": ocupados,
                "placas_unicas": len(set(placas)),
                "capacidad_total": len(self._cajones_por_id),
            }


            