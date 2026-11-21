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