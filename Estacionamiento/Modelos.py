"""Clases del dominio: vehículos, cajones, niveles, boletos, pensiones y movimientos."""

from abc import ABC, abstractmethod
from enum import Enum


class TipoCajon(Enum):
    """Tipos de cajones en el estacionamiento."""
    MOTO = "moto"
    COMPACTO = "compacto"
    ESTANDAR = "estandar"
    DISCAPACIDAD = "discapacidad"
    ELECTRICO = "electrico"

class Vehiculo(ABC):
    """Clase abstracta base para los distintos tipos de vehículos."""

    def __init__(self, placa, tiene_tarjeton=False, es_electrico=False):
        """Inicializa los atributos comunes de un vehículo."""
        placa_limpia = placa.strip().upper()
        if not placa_limpia:
            raise ValueError("La placa no puede estar vacía.")
        self._placa = placa_limpia
        self._tiene_tarjeton = bool(tiene_tarjeton)
        self._es_electrico = bool(es_electrico)

    @property
    def placa(self):
        """Obtiene la placa del vehículo."""
        return self._placa

    @property
    def tiene_tarjeton(self):
        """Indica si cuenta con tarjetón de discapacidad."""
        return self._tiene_tarjeton

    @property
    def es_electrico(self):
        """Indica si el vehículo es eléctrico."""
        return self._es_electrico

    @property
    @abstractmethod
    def tipo_nombre(self):
        """Devuelve el nombre del tipo de vehículo."""

    @abstractmethod
    def tipos_cajon_compatibles(self):
        """Devuelve la lista de tipos de cajón compatibles en orden de preferencia."""

class Motocicleta(Vehiculo):
    """Vehículo de dos ruedas; solo ocupa cajón de motocicleta."""

    @property
    def tipo_nombre(self):
        """Retorna 'moto'."""
        return "moto"

    def tipos_cajon_compatibles(self):
        """Retorna únicamente cajones para motocicleta."""
        return [TipoCajon.MOTO]


class Auto(Vehiculo):
    """Automóvil; puede usar cajón compacto o estándar, y especiales si aplica."""

    @property
    def tipo_nombre(self):
        """Retorna 'auto'."""
        return "auto"

    def tipos_cajon_compatibles(self):
        """Retorna los tipos de cajón compatibles según tarjetón o motor eléctrico."""
        compatibles = []
        if self._tiene_tarjeton:
            compatibles.append(TipoCajon.DISCAPACIDAD)
        if self._es_electrico:
            compatibles.append(TipoCajon.ELECTRICO)
        compatibles.append(TipoCajon.COMPACTO)
        compatibles.append(TipoCajon.ESTANDAR)
        return compatibles


class Camioneta(Vehiculo):
    """Camioneta; ocupa cajón estándar (o discapacidad si cuenta con tarjetón)."""

    @property
    def tipo_nombre(self):
        """Retorna 'camioneta'."""
        return "camioneta"

    def tipos_cajon_compatibles(self):
        """Retorna los tipos de cajón compatibles para una camioneta."""
        compatibles = []
        if self._tiene_tarjeton:
            compatibles.append(TipoCajon.DISCAPACIDAD)
        compatibles.append(TipoCajon.ESTANDAR)
        return compatibles


class FabricaVehiculos:
    """Fábrica para crear instancias de vehículos a partir de texto."""

    @staticmethod
    def crear(tipo, placa, tiene_tarjeton=False, es_electrico=False):
        """Crea una subclase de Vehiculo según el tipo indicado."""
        tipo_limpio = tipo.strip().lower()
        if tipo_limpio == "moto":
            return Motocicleta(placa, tiene_tarjeton=False, es_electrico=False)
        if tipo_limpio == "auto":
            return Auto(placa, tiene_tarjeton=tiene_tarjeton, es_electrico=es_electrico)
        if tipo_limpio == "camioneta":
            return Camioneta(placa, tiene_tarjeton=tiene_tarjeton, es_electrico=False)
        raise ValueError(f"Tipo de vehículo inválido: '{tipo}'. Use moto, auto o camioneta.")


class Cajon:
    """Representa un cajón individual dentro de un nivel."""

    def __init__(self, id_cajon, nivel, tipo):
        """Inicializa un cajón libre y sin reserva."""
        self.id_cajon = id_cajon
        self.nivel = nivel
        self.tipo = tipo
        self.ocupado = False
        self.placa_actual = None
        self.reservado_pension = False


class Nivel:
    """Representa un nivel del estacionamiento y contiene sus cajones."""

    def __init__(self, numero, cajones=None):
        """Inicializa el nivel con su número y lista de cajones."""
        self.numero = numero
        self.cajones = list(cajones) if cajones else []


class Boleto:
    """Representa el boleto emitido al entrar un vehículo."""

    def __init__(
        self,
        folio,
        placa,
        tipo_vehiculo,
        id_cajon,
        nivel,
        tipo_cajon,
        hora_entrada,
        es_pensionado=False,
        tiene_tarjeton=False,
        es_electrico=False,
    ):
        """Inicializa los datos del boleto."""
        self.folio = folio
        self.placa = placa
        self.tipo_vehiculo = tipo_vehiculo
        self.id_cajon = id_cajon
        self.nivel = nivel
        self.tipo_cajon = tipo_cajon
        self.hora_entrada = hora_entrada
        self.es_pensionado = es_pensionado
        self.tiene_tarjeton = tiene_tarjeton
        self.es_electrico = es_electrico


class Pension:
    """Representa una pensión mensual asignada a una placa y un cajón."""

    def __init__(self, placa, titular, id_cajon, fecha_vencimiento):
        """Inicializa una pensión."""
        self.placa = placa
        self.titular = titular
        self.id_cajon = id_cajon
        self.fecha_vencimiento = fecha_vencimiento

    def esta_vigente(self, fecha_consulta):
        """Verifica si la pensión sigue vigente en la fecha dada."""
        return fecha_consulta <= self.fecha_vencimiento


class RegistroMovimiento:
    """Guarda un movimiento de entrada, salida o pensión para el corte de caja."""

    def __init__(
        self,
        fecha_hora,
        tipo_operacion,
        placa,
        tipo_vehiculo,
        monto_estacionamiento=0.0,
        monto_carga_electrica=0.0,
        monto_boleto_perdido=0.0,
        monto_pension=0.0,
    ):
        """Inicializa un registro de movimiento."""
        self.fecha_hora = fecha_hora
        self.tipo_operacion = tipo_operacion
        self.placa = placa
        self.tipo_vehiculo = tipo_vehiculo
        self.monto_estacionamiento = float(monto_estacionamiento)
        self.monto_carga_electrica = float(monto_carga_electrica)
        self.monto_boleto_perdido = float(monto_boleto_perdido)
        self.monto_pension = float(monto_pension)

    @property
    def total(self):
        """Calcula el monto total del movimiento."""
        return (
            self.monto_estacionamiento
            + self.monto_carga_electrica
            + self.monto_boleto_perdido
            + self.monto_pension
        )
