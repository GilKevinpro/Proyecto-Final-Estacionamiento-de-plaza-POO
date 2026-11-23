"""Lectura y escritura de archivos JSON para configuración y estado del sistema."""

import json
from pathlib import Path

from .excepciones import ArchivoDatosError
from .modelos import Boleto, Cajon, Nivel, Pension, RegistroMovimiento, TipoCajon
from .tarifas import ConfiguracionTarifas


class RepositorioJSON:
    """Maneja la carga y guardado de configuración y estado en archivos JSON."""

    def __init__(self, ruta_config, ruta_estado):
        """Inicializa las rutas de los archivos JSON."""
        self.ruta_config = Path(ruta_config)
        self.ruta_estado = Path(ruta_estado)

    def cargar_configuracion(self):
        """Lee y valida niveles, cajones y tarifas desde el archivo de configuración."""
        if not self.ruta_config.exists():
            raise ArchivoDatosError(f"No existe el archivo de configuración: {self.ruta_config}")

        try:
            with open(self.ruta_config, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
        except (OSError, json.JSONDecodeError) as exc:
            raise ArchivoDatosError(f"Error al leer la configuración: {exc}") from exc

        if not isinstance(datos, dict) or "niveles" not in datos or "tarifas" not in datos:
            raise ArchivoDatosError("El archivo de configuración debe incluir 'niveles' y 'tarifas'.")

        try:
            t = datos["tarifas"]
            config = ConfiguracionTarifas(
                minutos_gratis=t.get("minutos_gratis", 15),
                bloque_minutos=t.get("bloque_minutos", 15),
                tarifa_moto=t.get("tarifa_moto", 5.0),
                tarifa_auto=t.get("tarifa_auto", 8.0),
                tarifa_camioneta=t.get("tarifa_camioneta", 10.0),
                tarifa_kwh=t.get("tarifa_kwh", 4.0),
                compra_minima_descuento=t.get("compra_minima_descuento", 500.0),
                minutos_gratis_compra=t.get("minutos_gratis_compra", 120),
                tarifa_boleto_perdido=t.get("tarifa_boleto_perdido", 250.0),
                tarifa_pension_mensual=t.get("tarifa_pension_mensual", 1200.0),
            )

            niveles = []
            for item_nivel in datos["niveles"]:
                num_nivel = int(item_nivel["nivel"])
                cajones = []
                for tipo_str, cantidad in item_nivel["cajones"].items():
                    tipo_cajon = TipoCajon(tipo_str)
                    cantidad_num = int(cantidad)
                    if cantidad_num < 0:
                        raise ValueError("La cantidad de cajones no puede ser negativa.")
                    for indice in range(1, cantidad_num + 1):
                        codigo = f"N{num_nivel}-{tipo_cajon.value[:3].upper()}-{indice:02d}"
                        cajones.append(Cajon(codigo, num_nivel, tipo_cajon))
                niveles.append(Nivel(num_nivel, cajones))

            if not niveles:
                raise ValueError("Debe existir al menos un nivel configurado.")

            niveles.sort(key=lambda n: n.numero)
            return niveles, config
        except (KeyError, TypeError, ValueError) as exc:
            raise ArchivoDatosError(f"Datos inválidos en la configuración: {exc}") from exc

    def cargar_estado(self):
        """Carga boletos activos, pensiones e historial si el archivo de estado existe."""
        if not self.ruta_estado.exists():
            return {
                "consecutivo_folio": 1,
                "boletos_activos": [],
                "pensiones": [],
                "historial": [],
            }

        try:
            with open(self.ruta_estado, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
        except (OSError, json.JSONDecodeError) as exc:
            raise ArchivoDatosError(f"Error al leer el archivo de estado: {exc}") from exc

        if not isinstance(datos, dict):
            raise ArchivoDatosError("El archivo de estado no tiene un objeto JSON válido.")
        return datos

    def guardar_estado(self, consecutivo_folio, boletos_activos, pensiones, historial):
        """Guarda el estado actual del estacionamiento en JSON."""
        self.ruta_estado.parent.mkdir(parents=True, exist_ok=True)
        estructura = {
            "consecutivo_folio": consecutivo_folio,
            "boletos_activos": [
                {
                    "folio": b.folio,
                    "placa": b.placa,
                    "tipo_vehiculo": b.tipo_vehiculo,
                    "id_cajon": b.id_cajon,
                    "nivel": b.nivel,
                    "tipo_cajon": b.tipo_cajon.value,
                    "hora_entrada": b.hora_entrada.isoformat(),
                    "es_pensionado": b.es_pensionado,
                    "tiene_tarjeton": b.tiene_tarjeton,
                    "es_electrico": b.es_electrico,
                }
                for b in boletos_activos
            ],
            "pensiones": [
                {
                    "placa": p.placa,
                    "titular": p.titular,
                    "id_cajon": p.id_cajon,
                    "fecha_vencimiento": p.fecha_vencimiento.isoformat(),
                }
                for p in pensiones
            ],
            "historial": [
                {
                    "fecha_hora": m.fecha_hora.isoformat(),
                    "tipo_operacion": m.tipo_operacion,
                    "placa": m.placa,
                    "tipo_vehiculo": m.tipo_vehiculo,
                    "monto_estacionamiento": m.monto_estacionamiento,
                    "monto_carga_electrica": m.monto_carga_electrica,
                    "monto_boleto_perdido": m.monto_boleto_perdido,
                    "monto_pension": m.monto_pension,
                }
                for m in historial
            ],
        }

        try:
            with open(self.ruta_estado, "w", encoding="utf-8") as archivo:
                json.dump(estructura, archivo, indent=2, ensure_ascii=False)
        except OSError as exc:
            raise ArchivoDatosError(f"No se pudo guardar el estado: {exc}") from exc
