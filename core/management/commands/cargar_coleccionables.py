"""
Comando de gestión para cargar coleccionables en el sistema de ruleta.

Crea los coleccionables del catálogo, sus probabilidades y la configuración
de la ruleta si no existen. Es idempotente: se puede correr múltiples veces
sin duplicar datos.

Uso:
    python manage.py cargar_coleccionables
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum
from core.models import Coleccionable, RuletaProbabilidad, ConfiguracionRuleta


# ---------------------------------------------------------------------------
# Catálogo de coleccionables
# Cada entrada define nombre, descripción, rareza y probabilidad individual.
# Las probabilidades por rareza deben sumar:
#   comun=0.60, raro=0.25, epico=0.12, legendario=0.03
# ---------------------------------------------------------------------------
COLECCIONABLES = [
    # ---- COMUNES (60% en total) ----
    {'nombre': 'Mascota Beauchef',     'descripcion': 'La adorable mascota de la Facultad de Ciencias Físicas y Matemáticas', 'rareza': 'comun', 'probabilidad': Decimal('0.10')},
    {'nombre': 'Laptop Vieja',         'descripcion': 'Una laptop con stickers de tecnología vintage',                         'rareza': 'comun', 'probabilidad': Decimal('0.09')},
    {'nombre': 'Café del Casino',      'descripcion': 'Un café recién preparado del casino estudiantil',                       'rareza': 'comun', 'probabilidad': Decimal('0.08')},
    {'nombre': 'Mochila FCFyM',        'descripcion': 'Mochila oficial de la facultad con el logo',                            'rareza': 'comun', 'probabilidad': Decimal('0.07')},
    {'nombre': 'Lápiz Pasta Azul',     'descripcion': 'El clásico lápiz que nunca falta en un parcial',                       'rareza': 'comun', 'probabilidad': Decimal('0.06')},
    {'nombre': 'Calculadora Científica','descripcion': 'Calculadora básica para resolver ecuaciones',                          'rareza': 'comun', 'probabilidad': Decimal('0.06')},
    {'nombre': 'Completo del Casino',  'descripcion': 'El famoso completo italiano del casino',                                'rareza': 'comun', 'probabilidad': Decimal('0.05')},
    {'nombre': 'Botella de Agua',      'descripcion': 'Hidratación esencial para sobrevivir clases',                          'rareza': 'comun', 'probabilidad': Decimal('0.04')},
    {'nombre': 'Polera Blanca',        'descripcion': 'La polera básica de todo mechoneo',                                    'rareza': 'comun', 'probabilidad': Decimal('0.03')},
    {'nombre': 'Borrador',             'descripcion': 'Para corregir todos esos errores de cálculo',                          'rareza': 'comun', 'probabilidad': Decimal('0.02')},

    # ---- RAROS (25% en total) ----
    {'nombre': 'Polera de Mec',        'descripcion': 'Polera exclusiva del Departamento de Ingeniería Mecánica',             'rareza': 'raro', 'probabilidad': Decimal('0.07')},
    {'nombre': 'Cuaderno de Apuntes',  'descripcion': 'Cuaderno lleno de fórmulas y ecuaciones legendarias',                  'rareza': 'raro', 'probabilidad': Decimal('0.06')},
    {'nombre': 'Pase VIP Casino',      'descripcion': 'Acceso prioritario a la fila del casino',                              'rareza': 'raro', 'probabilidad': Decimal('0.05')},
    {'nombre': 'USB con Auxiliares',   'descripcion': 'USB con todos los auxiliares resueltos del semestre',                  'rareza': 'raro', 'probabilidad': Decimal('0.04')},
    {'nombre': 'Gorro de Lana',        'descripcion': 'Para sobrevivir el frío de las salas en invierno',                    'rareza': 'raro', 'probabilidad': Decimal('0.03')},

    # ---- ÉPICOS (12% en total) ----
    {'nombre': 'Trofeo Copa de la Mona',  'descripcion': 'Trofeo del legendario torneo Copa de la Mona',                     'rareza': 'epico', 'probabilidad': Decimal('0.05')},
    {'nombre': 'Diploma de Honor',        'descripcion': 'Diploma al mejor estudiante del semestre',                          'rareza': 'epico', 'probabilidad': Decimal('0.04')},
    {'nombre': 'Chaqueta de Generación',  'descripcion': 'La exclusiva chaqueta oficial de tu generación',                   'rareza': 'epico', 'probabilidad': Decimal('0.03')},

    # ---- LEGENDARIOS (3% en total) ----
    {'nombre': 'Llave de la Torre',       'descripcion': 'La llave secreta de acceso a la torre central de Beauchef',        'rareza': 'legendario', 'probabilidad': Decimal('0.02')},
    {'nombre': 'Medalla Plan Común',      'descripcion': 'Medalla otorgada solo a los que sobrevivieron plan común con honores', 'rareza': 'legendario', 'probabilidad': Decimal('0.01')},
]


class Command(BaseCommand):
    """
    Comando Django para inicializar el catálogo de coleccionables.

    Crea o reutiliza la ConfiguracionRuleta (pk=1), luego itera sobre
    COLECCIONABLES creando cada Coleccionable y su RuletaProbabilidad
    asociada si aún no existen.
    """

    help = 'Carga coleccionables de ejemplo y configura la ruleta'

    def handle(self, *args, **options):
        """
        Punto de entrada del comando.

        Flujo:
        1. Crea/obtiene ConfiguracionRuleta con costo $100.
        2. Itera COLECCIONABLES: crea Coleccionable + RuletaProbabilidad.
        3. Imprime resumen con distribución por rareza.

        Args:
            *args: argumentos posicionales (no usados)
            **options: opciones del comando (no usadas)
        """
        self._configurar_ruleta()
        creados, probs = self._crear_coleccionables()
        self._imprimir_resumen(creados, probs)

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def _configurar_ruleta(self):
        """
        Crea la ConfiguracionRuleta con pk=1 si no existe.

        Usa get_or_create con pk=1 para garantizar que solo
        exista un registro de configuración en el sistema.
        """
        _, created = ConfiguracionRuleta.objects.get_or_create(
            pk=1,
            defaults={'costo_giro': Decimal('100.00'), 'activa': True}
        )
        estado = 'creada' if created else 'ya existía'
        self.stdout.write(f'Configuracion ruleta: {estado} ($100 por giro)')

    def _crear_coleccionables(self):
        """
        Itera sobre COLECCIONABLES y persiste cada uno con su probabilidad.

        Para cada entrada en COLECCIONABLES:
        - Usa get_or_create en Coleccionable (clave: nombre).
        - Usa get_or_create en RuletaProbabilidad (clave: coleccionable).
        Solo crea registros que no existan; los existentes se dejan intactos.

        Returns:
            tuple[int, int]: (coleccionables_creados, probabilidades_creadas)
        """
        creados = 0
        probs = 0

        for data in COLECCIONABLES:
            # Separar probabilidad del resto de campos del modelo
            probabilidad = data['probabilidad']

            coleccionable, nuevo = Coleccionable.objects.get_or_create(
                nombre=data['nombre'],
                defaults={
                    'descripcion': data['descripcion'],
                    'rareza':      data['rareza'],
                }
            )
            if nuevo:
                creados += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  + {coleccionable.nombre} ({coleccionable.get_rareza_display()})')
                )

            # Asociar probabilidad al coleccionable
            _, prob_nueva = RuletaProbabilidad.objects.get_or_create(
                coleccionable=coleccionable,
                defaults={'probabilidad': probabilidad, 'activo': True}
            )
            if prob_nueva:
                probs += 1

        return creados, probs

    def _imprimir_resumen(self, creados: int, probs: int):
        """
        Imprime un resumen de la operación con distribución por rareza.

        Consulta la suma real de probabilidades desde la BD para reflejar
        el estado actual (no los valores hardcodeados), de modo que si
        se agregan o eliminan coleccionables el porcentaje sea correcto.

        Args:
            creados (int): cantidad de Coleccionable creados en esta ejecución
            probs (int): cantidad de RuletaProbabilidad creadas en esta ejecución
        """
        self.stdout.write(f'\nColeccionables creados: {creados}')
        self.stdout.write(f'Probabilidades creadas: {probs}')
        self.stdout.write('\nDistribucion por rareza:')

        for rareza, label in Coleccionable.RAREZA_CHOICES:
            # Suma real desde BD para que refleje cambios futuros
            total = RuletaProbabilidad.objects.filter(
                coleccionable__rareza=rareza,
                activo=True
            ).aggregate(t=Sum('probabilidad'))['t'] or Decimal('0')

            count = RuletaProbabilidad.objects.filter(
                coleccionable__rareza=rareza, activo=True
            ).count()

            self.stdout.write(f'  {label:<12}: {float(total)*100:>5.1f}%  ({count} coleccionables)')

        self.stdout.write(self.style.SUCCESS('\nColeccionables cargados exitosamente'))
