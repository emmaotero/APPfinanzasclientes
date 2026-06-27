-- ============================================================
-- Orden.ar · Gestión de Carteras · Schema Supabase
-- Ejecutar en Supabase > SQL Editor
-- ============================================================

-- CLIENTES
create table clientes (
  id uuid default gen_random_uuid() primary key,
  nombre text not null,
  tipo text check (tipo in ('persona', 'empresa')) default 'persona',
  desde date default current_date,
  activo boolean default true,
  notas text,
  created_at timestamptz default now()
);

-- CARTERAS
create table carteras (
  id uuid default gen_random_uuid() primary key,
  cliente_id uuid references clientes(id) on delete cascade,
  nombre text not null,
  moneda_base text check (moneda_base in ('ARS', 'USD', 'mixta')) default 'mixta',
  activa boolean default true,
  created_at timestamptz default now()
);

-- PERFIL DE RIESGO (uno por cartera, actualizable)
create table perfil_riesgo (
  id uuid default gen_random_uuid() primary key,
  cartera_id uuid references carteras(id) on delete cascade,
  horizonte text,
  tolerancia text,
  objetivo text,
  liquidez text,
  restricciones text,
  fecha_actualizacion date default current_date,
  created_at timestamptz default now()
);

-- POSICIONES
create table posiciones (
  id uuid default gen_random_uuid() primary key,
  cartera_id uuid references carteras(id) on delete cascade,
  ticker text not null,
  nombre text,
  tipo text check (tipo in ('accion', 'cedear', 'bono', 'fci', 'pf', 'otro')) default 'accion',
  moneda text check (moneda in ('ARS', 'USD')) default 'ARS',
  cantidad numeric not null default 0,
  precio_compra numeric,
  fecha_compra date,
  activa boolean default true,
  notas text,
  created_at timestamptz default now()
);

-- MOVIMIENTOS
create table movimientos (
  id uuid default gen_random_uuid() primary key,
  cartera_id uuid references carteras(id) on delete cascade,
  posicion_id uuid references posiciones(id) on delete set null,
  tipo text check (tipo in ('compra', 'venta', 'renovacion', 'dividendo', 'otro')) default 'compra',
  fecha date default current_date,
  ticker text,
  cantidad numeric,
  precio numeric,
  moneda text check (moneda in ('ARS', 'USD')) default 'ARS',
  notas text,
  created_at timestamptz default now()
);

-- RADAR DE SEGUIMIENTO
create table radar (
  id uuid default gen_random_uuid() primary key,
  ticker text not null unique,
  agregado_por text,
  created_at timestamptz default now()
);

-- ============================================================
-- DATOS DE EJEMPLO (opcional — borrar en producción)
-- ============================================================
insert into clientes (nombre, tipo, desde) values
  ('Martín Rodríguez', 'persona', '2025-03-01'),
  ('Sofía Pereyra', 'persona', '2025-01-01'),
  ('Ferretería Tonelli SRL', 'empresa', '2025-04-01');

insert into carteras (cliente_id, nombre, moneda_base)
select id, 'Principal', 'mixta' from clientes where nombre = 'Martín Rodríguez';

insert into carteras (cliente_id, nombre, moneda_base)
select id, 'USD', 'USD' from clientes where nombre = 'Martín Rodríguez';

insert into carteras (cliente_id, nombre, moneda_base)
select id, 'Principal', 'ARS' from clientes where nombre = 'Sofía Pereyra';

insert into carteras (cliente_id, nombre, moneda_base)
select id, 'Principal', 'ARS' from clientes where nombre = 'Ferretería Tonelli SRL';

insert into radar (ticker, agregado_por) values
  ('GGAL.BA', 'Emma'),
  ('YPF.BA', 'Emma'),
  ('GD30.BA', 'Manu'),
  ('MSFT', 'Jime');
