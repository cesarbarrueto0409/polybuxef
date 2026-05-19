# Polybuxef

Polybuxef es una plataforma de apuestas ficticias para la comunidad de Beauchef, inspirada en el funcionamiento de mercados predictivos como Polymarket.

El objetivo del proyecto es permitir que las personas puedan participar en eventos internos, partidos y competencias como la Copa de la Mona, usando una economia ficticia dentro de la aplicacion.

## Idea General

En Polybuxef, los usuarios pueden entrar a distintos mercados de prediccion y apostar por el resultado que creen que ocurrira. Por ejemplo:

- Quien ganara un partido de la Copa de la Mona.
- Que equipo avanzara a la siguiente ronda.
- Que evento ocurrira primero dentro de una competencia.
- Resultados de actividades o desafios de la comunidad Beauchef.

Cada mercado tiene opciones disponibles, y los usuarios pueden usar saldo ficticio para participar. Cuando el evento termina, se resuelve el mercado y se recompensa a quienes eligieron la opcion correcta.

## Funcionalidades Esperadas

- Registro e inicio de sesion de usuarios.
- Perfil de usuario con informacion personal y saldo ficticio.
- Mercados de apuestas para eventos, partidos y actividades.
- Sistema de economia ficticia.
- Compra o participacion en opciones de mercado.
- Resolucion de mercados cuando termina un evento.
- Historial de transacciones y apuestas.
- Sistema de racha diaria o `day streak`.
- Interfaz web para explorar mercados y participar.

## Contexto

Este proyecto nace como una aplicacion web para organizar apuestas ficticias dentro de Beauchef. No utiliza dinero real y esta pensado como una experiencia social, competitiva y entretenida para eventos de la comunidad.

## Tecnologias

El proyecto se desarrollara usando Django para el backend. La base de datos, el frontend y otras herramientas se iran definiendo durante el desarrollo del proyecto.

## Configuracion Local

Para usar MySQL, copia `.env.example` como `.env` y completa los datos de conexion:

```bash
cp .env.example .env
```

Variables esperadas:

```env
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=database_name
DB_USERNAME=database_user
DB_PASSWORD=database_password
```

Si no existe `.env`, Django usa SQLite localmente y crea `db.sqlite3` al ejecutar las migraciones. El archivo `.env` contiene credenciales locales y no debe subirse al repositorio.

## Estructura del Proyecto

### Modelos (`core/models.py`)

El sistema de apuestas está implementado con tres modelos principales:

#### Categoria
Agrupa mercados relacionados por temática (deportes, política universitaria, eventos académicos).

**Campos:**
- `nombre`: Nombre único de la categoría

**Métodos principales:**
- `get_mercados_activos()`: Obtiene mercados con estado 'abierto'
- `contar_mercados()`: Cuenta el total de mercados en la categoría

#### Mercado
Representa un evento sobre el cual los usuarios pueden apostar.

**Campos:**
- `categoria`: Relación con Categoria
- `titulo`: Título del mercado
- `descripcion`: Descripción detallada
- `imagen_url`: URL de la imagen (opcional)
- `estado`: abierto, cerrado, resuelto, cancelado
- `fecha_creacion`: Fecha de creación automática
- `fecha_cierre`: Fecha límite para apuestas

**Métodos principales:**
- `cerrar_mercado()`: Cierra el mercado impidiendo nuevas apuestas
- `cancelar_mercado()`: Cancela el mercado
- `esta_abierto()`: Verifica si está abierto para apuestas
- `calcular_total_tokens()`: Suma total de tokens apostados

#### Opcion
Representa una posible respuesta o resultado dentro de un mercado.

**Campos:**
- `mercado`: Relación con Mercado
- `nombre`: Nombre de la opción
- `tokens`: Total de tokens apostados
- `precio`: Precio actual (probabilidad implícita entre 0 y 1)
- `es_ganadora`: Indica si ganó el mercado

**Métodos principales:**
- `agregar_tokens(cantidad)`: Agrega tokens cuando un usuario compra shares
- `quitar_tokens(cantidad)`: Quita tokens cuando un usuario vende shares
- `actualizar_precio(nuevo_precio)`: Actualiza el precio de la opción
- `marcar_como_ganadora()`: Marca esta opción como ganadora
- `calcular_probabilidad()`: Calcula probabilidad basada en tokens del mercado

### Servicios (`core/services/`)

Capa de lógica de negocio que maneja operaciones sobre los modelos.

#### CategoriaService (`categoria_service.py`)
Gestión completa de categorías (CRUD).

**Métodos:**
- `crear_categoria(nombre)`: Crea una nueva categoría
- `obtener_categoria(id_categoria)`: Obtiene una categoría por ID
- `listar_categorias()`: Lista todas las categorías
- `actualizar_categoria(id_categoria, nombre)`: Actualiza el nombre
- `eliminar_categoria(id_categoria)`: Elimina una categoría (cascada)
- `obtener_categorias_con_mercados_activos()`: Categorías con mercados abiertos

#### MercadoService (`mercado_service.py`)
Gestión de mercados y su ciclo de vida.

**Métodos:**
- `crear_mercado(id_categoria, titulo, descripcion, fecha_cierre, imagen_url)`: Crea un mercado
- `obtener_mercado(id_mercado)`: Obtiene un mercado por ID
- `listar_mercados()`: Lista todos los mercados
- `listar_mercados_abiertos()`: Lista mercados con estado 'abierto'
- `listar_mercados_por_categoria(id_categoria)`: Mercados de una categoría
- `cerrar_mercado(id_mercado)`: Cierra un mercado
- `cancelar_mercado(id_mercado)`: Cancela un mercado
- `actualizar_mercado(id_mercado, ...)`: Actualiza datos del mercado
- `eliminar_mercado(id_mercado)`: Elimina un mercado (cascada)

#### OpcionService (`opcion_service.py`)
Gestión de opciones y tokens.

**Métodos:**
- `crear_opcion(id_mercado, nombre, precio_inicial)`: Crea una opción
- `obtener_opcion(id_opcion)`: Obtiene una opción por ID
- `listar_opciones_por_mercado(id_mercado)`: Lista opciones de un mercado
- `agregar_tokens_a_opcion(id_opcion, cantidad)`: Agrega tokens (compra)
- `quitar_tokens_de_opcion(id_opcion, cantidad)`: Quita tokens (venta)
- `actualizar_precio_opcion(id_opcion, nuevo_precio)`: Actualiza precio
- `marcar_opcion_ganadora(id_opcion)`: Marca ganadora y resuelve mercado
- `actualizar_opcion(id_opcion, nombre)`: Actualiza datos
- `eliminar_opcion(id_opcion)`: Elimina una opción
- `obtener_probabilidades_mercado(id_mercado)`: Calcula probabilidades de todas las opciones

### Características Implementadas

- Validaciones en todos los métodos de servicios
- Transacciones atómicas para operaciones críticas
- Relaciones en cascada entre modelos
- Cálculo dinámico de probabilidades basado en tokens
- Sistema de estados para mercados (abierto → cerrado → resuelto)
- Documentación completa en español para clases, métodos y parámetros
- Interfaz de administración de Django configurada

## Estado Del Proyecto

Sistema de apuestas implementado con modelos y servicios básicos. Pendiente integración con sistema de usuarios, transacciones y wallet.
