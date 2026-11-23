"""Estrategias de cobro para salidas del estacionamiento."""

from abc import ABC, abstractmethod
import math

from .modelos import TipoCajon


class ConfiguracionTarifas:
    """Almacena las tarifas y reglas de cobro configuradas."""

    def __init__(
        self,
        minutos_gratis=15,
        bloque_minutos=15,
        tarifa_moto=5.0,
        tarifa_auto=8.0,
        tarifa_camioneta=10.0,
        tarifa_kwh=4.0,
        compra_minima_descuento=500.0,
        minutos_gratis_compra=120,
        tarifa_boleto_perdido=250.0,
        tarifa_pension_mensual=1200.0,
    ):
        """Inicializa los parámetros tarifarios."""
        self.minutos_gratis = int(minutos_gratis)
        self.bloque_minutos = int(bloque_minutos)
        self.tarifa_moto = float(tarifa_moto)
        self.tarifa_auto = float(tarifa_auto)
        self.tarifa_camioneta = float(tarifa_camioneta)
        self.tarifa_kwh = float(tarifa_kwh)
        self.compra_minima_descuento = float(compra_minima_descuento)
        self.minutos_gratis_compra = int(minutos_gratis_compra)
        self.tarifa_boleto_perdido = float(tarifa_boleto_perdido)
        self.tarifa_pension_mensual = float(tarifa_pension_mensual)

class DesgloseCobro:
    """Contiene los montos desglosados al registrar una salida."""

    def __init__(self, minutos_totales, estacionamiento, carga_electrica, boleto_perdido):
        """Inicializa el desglose de cobro."""
        self.minutos_totales = int(minutos_totales)
        self.estacionamiento = float(estacionamiento)
        self.carga_electrica = float(carga_electrica)
        self.boleto_perdido = float(boleto_perdido)

    @property
    def total(self):
        """Suma total a pagar."""
        return self.estacionamiento + self.carga_electrica + self.boleto_perdido


class EstrategiaCobro(ABC):
    """Interfaz abstracta para las distintas estrategias de cobro."""

    @abstractmethod
    def calcular(self, boleto, hora_salida, config, monto_ticket_compra=0.0, kwh_cargados=0.0):
        """Calcula el desglose de cobro a partir del boleto y la hora de salida."""


class CobroPensionadoVigente(EstrategiaCobro):
    """Estrategia para pensionados con mensualidad vigente."""

    def calcular(self, boleto, hora_salida, config, monto_ticket_compra=0.0, kwh_cargados=0.0):
        """No cobra tiempo de estacionamiento; solo cobra carga eléctrica si usó cargador."""
        minutos = max(0, int((hora_salida - boleto.hora_entrada).total_seconds() // 60))
        costo_carga = 0.0
        if boleto.tipo_cajon == TipoCajon.ELECTRICO and kwh_cargados > 0:
            costo_carga = float(kwh_cargados) * config.tarifa_kwh
        return DesgloseCobro(minutos, 0.0, costo_carga, 0.0)


class CobroBoletoPerdido(EstrategiaCobro):
    """Estrategia cuando el usuario perdió su boleto."""

    def calcular(self, boleto, hora_salida, config, monto_ticket_compra=0.0, kwh_cargados=0.0):
        """Aplica la tarifa fija por boleto perdido más carga eléctrica si corresponde."""
        minutos = max(0, int((hora_salida - boleto.hora_entrada).total_seconds() // 60))
        costo_carga = 0.0
        if boleto.tipo_cajon == TipoCajon.ELECTRICO and kwh_cargados > 0:
            costo_carga = float(kwh_cargados) * config.tarifa_kwh
        return DesgloseCobro(minutos, 0.0, costo_carga, config.tarifa_boleto_perdido)


class CobroVisitanteEstandar(EstrategiaCobro):
    """Estrategia de cobro regular por fracciones de 15 minutos."""

    def calcular(self, boleto, hora_salida, config, monto_ticket_compra=0.0, kwh_cargados=0.0):
        """Calcula el cobro por tiempo, descuento por compra en plaza y carga eléctrica."""
        if hora_salida < boleto.hora_entrada:
            raise ValueError("La hora de salida no puede ser anterior a la hora de entrada.")

        segundos = (hora_salida - boleto.hora_entrada).total_seconds()
        minutos_totales = math.ceil(segundos / 60)

        costo_carga = 0.0
        if boleto.tipo_cajon == TipoCajon.ELECTRICO and kwh_cargados > 0:
            costo_carga = float(kwh_cargados) * config.tarifa_kwh

        if minutos_totales <= config.minutos_gratis:
            return DesgloseCobro(minutos_totales, 0.0, costo_carga, 0.0)

        minutos_a_cobrar = minutos_totales
        if float(monto_ticket_compra) >= config.compra_minima_descuento:
            minutos_a_cobrar = max(0, minutos_totales - config.minutos_gratis_compra)

        if minutos_a_cobrar == 0:
            costo_tiempo = 0.0
        else:
            fracciones = math.ceil(minutos_a_cobrar / config.bloque_minutos)
            if boleto.tipo_vehiculo == "moto":
                tarifa_bloque = config.tarifa_moto
            elif boleto.tipo_vehiculo == "camioneta":
                tarifa_bloque = config.tarifa_camioneta
            else:
                tarifa_bloque = config.tarifa_auto
            costo_tiempo = fracciones * tarifa_bloque

        return DesgloseCobro(minutos_totales, costo_tiempo, costo_carga, 0.0)
