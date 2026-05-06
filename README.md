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

## Estado Del Proyecto

Proyecto en etapa inicial de configuracion y definicion de funcionalidades.
