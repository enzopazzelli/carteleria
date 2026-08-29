# **Especificación Técnica de Desarrollo: Sistema de Nesting, Cotización e IA para Cartelería**

**Resumen del Proyecto:** Desarrollo Pro-Code a medida orientado a optimizar la gestión de cotizaciones de cartelería. El sistema automatiza la ingesta de vectores (SVG/DXF), calcula el anidamiento (nesting) óptimo sobre chapas/planchas, estima costos de insumos, genera un fotomontaje contextualizado con Inteligencia Artificial (cartel en la fachada del local) y permite un flujo de aprobación interno antes del envío final al cliente.

## **1\. Resumen de Arquitectura y Stack Tecnológico**

El sistema se diseña bajo una arquitectura desacoplada basada en microservicios o monolito modular, utilizando FastAPI como backend principal, React/Next.js para la interfaz visual sin código, y workers en segundo plano para tareas intensivas (nesting y renderizado de IA).

| Componente | Tecnología / Librería | Propósito y Función   |
| :---- | :---- | :---- |
| **Frontend (GUI)** | React.js / Next.js \+ TailwindCSS | Interfaz de usuario simple y moderna para diseñadores y dueños (sin uso de código). |
| **Backend API** | Python 3.11 \+ FastAPI | API RESTful asíncrona de alto rendimiento para lógica de negocio y endpoints. |
| **Algoritmo de Nesting** | Shapely \+ svgpathtools \+ rectpack / C++ Wrapper | Procesamiento geométrico de vectores 2D y empaquetamiento óptimo en planchas. |
| **Gestión de Tareas** | Celery \+ Redis | Cola de procesamiento asíncrono para cálculos pesados de geometría e IA. |
| **Base de Datos** | PostgreSQL \+ SQLAlchemy / Alembic | Almacenamiento relacional de inventario, clientes, presupuestos y usuarios. |
| **Módulo de IA** | Replicate API / ControlNet (Stable Diffusion) | Generación de fotomontajes de carteles integrados en la fachada del local. |
| **Generador de PDF** | WeasyPrint (HTML a PDF) | Compilación gráfica y formateada del presupuesto con desglose y fotomontaje. |
| **Notificaciones & Mensajería** | Twilio API (WhatsApp) / SendGrid (Email) | Envío automatizado del presupuesto aprobado al cliente final. |
| **Infraestructura / Hosting** | Docker \+ Docker Compose en Hetzner / AWS | Contenerización e infraestructura de servidores aislada y escalable. |

## **2\. Esquema de Base de Datos (PostgreSQL)**

A continuación se detalla la estructura relacional de la base de datos para gestionar materiales, formatos de plancha, cotizaciones y estados del flujo de aprobación.

`-- 1. Tabla de Usuarios`  
`CREATE TABLE usuarios (`  
    `id SERIAL PRIMARY KEY,`  
    `nombre VARCHAR(100) NOT NULL,`  
    `email VARCHAR(150) UNIQUE NOT NULL,`  
    `rol VARCHAR(20) NOT NULL CHECK (rol IN ('ADMIN', 'DISENADOR', 'DISENADOR_DUEÑO')),`  
    `creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP`  
`);`

`-- 2. Tabla de Clientes`  
`CREATE TABLE clientes (`  
    `id SERIAL PRIMARY KEY,`  
    `nombre VARCHAR(150) NOT NULL,`  
    `empresa VARCHAR(150),`  
    `telefono VARCHAR(50) NOT NULL,`  
    `email VARCHAR(150),`  
    `direccion TEXT`  
`);`

`-- 3. Tabla de Materiales e Insumos`  
`CREATE TABLE materiales (`  
    `id SERIAL PRIMARY KEY,`  
    `nombre VARCHAR(100) NOT NULL, -- Ej: Chapa Galvanizada 18, Chapa Alucobond`  
    `unidad_medida VARCHAR(20) DEFAULT 'm2', -- m2, metro, unidad`  
    `precio_costo_unitario NUMERIC(10, 2) NOT NULL,`  
    `precio_venta_unitario NUMERIC(10, 2) NOT NULL,`  
    `actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP`  
`);`

`-- 4. Formatos de Chapas / Planchas Disponibles`  
`CREATE TABLE formatos_chapa (`  
    `id SERIAL PRIMARY KEY,`  
    `material_id INT REFERENCES materiales(id) ON DELETE CASCADE,`  
    `ancho_mm NUMERIC(10, 2) NOT NULL, -- Ej: 1220 mm`  
    `alto_mm NUMERIC(10, 2) NOT NULL,  -- Ej: 2440 mm`  
    `espesor_mm NUMERIC(5, 2) DEFAULT 0.0`  
`);`

`-- 5. Tabla Principal de Presupuestos`  
`CREATE TABLE presupuestos (`  
    `id SERIAL PRIMARY KEY,`  
    `codigo_presupuesto VARCHAR(20) UNIQUE NOT NULL,`  
    `cliente_id INT REFERENCES clientes(id),`  
    `disenador_id INT REFERENCES usuarios(id),`  
    `estado VARCHAR(30) DEFAULT 'BORRADOR' CHECK (estado IN ('BORRADOR', 'PENDIENTE_APROBACION', 'APROBADO', 'ENVIADO', 'RECHAZADO')),`  
    `costo_materiales NUMERIC(10, 2) DEFAULT 0.0,`  
    `costo_mano_obra NUMERIC(10, 2) DEFAULT 0.0,`  
    `costo_total NUMERIC(10, 2) DEFAULT 0.0,`  
    `porcentaje_desperdicio_total NUMERIC(5, 2) DEFAULT 0.0,`  
    `foto_fachada_url TEXT,`  
    `foto_montaje_ia_url TEXT,`  
    `pdf_url TEXT,`  
    `creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,`  
    `aprobado_en TIMESTAMP`  
`);`

`-- 6. Detalle de Piezas Vectoriales y Nesting por Presupuesto`  
`CREATE TABLE presupuesto_piezas (`  
    `id SERIAL PRIMARY KEY,`  
    `presupuesto_id INT REFERENCES presupuestos(id) ON DELETE CASCADE,`  
    `formato_chapa_id INT REFERENCES formatos_chapa(id),`  
    `cantidad_planchas_usadas INT NOT NULL,`  
    `area_utilizada_mm2 NUMERIC(12, 2) NOT NULL,`  
    `area_desperdicio_mm2 NUMERIC(12, 2) NOT NULL,`  
    `disposicion_svg_resultante TEXT -- Almacena el esquema de corte/anidado vectorial`  
`);`

## **3\. Diagrama de Funcionamiento y Flujo Paso a Paso**

El siguiente flujo describe la interacción entre el usuario y la plataforma automatizada:

1. **Carga de Vectores y Parámetros:** El diseñador entra al panel web, selecciona el cliente, el tipo de material (ej. Chapa 18\) y el formato de plancha. Subo el archivo SVG exportado desde CorelDRAW junto con la foto del frente del local.  
2. **Ejecución del Algoritmo de Nesting (Worker):**  
   * FastAPI valida los archivos y encola la tarea en Celery.  
   * El motor de Python extrae los polígonos vectoriales del SVG usando svgpathtools.  
   * Se aplica el algoritmo de anidamiento (Nesting) para organizar los vectores dentro del formato de la chapa, considerando un margen de corte de seguridad (ej. 5 mm entre piezas).  
   * Se calcula la cantidad exacta de planchas necesarias y el desperdicio de chapa (área sobrante).  
3. **Generación del Fotomontaje IA:**  
   * El servidor envía la foto de la fachada y el vector renderizado del cartel a la API de Inpainting (ControlNet / Stable Diffusion).  
   * La IA devuelve la imagen combinada respetando la iluminación, inclinación y estructura del frente del local.  
4. **Cálculo Automático de Costos y Estado Pendiente:**  
   * El sistema consulta los precios en la tabla materiales, calcula Insumos \+ Mano de Obra y genera el costo sugerido de venta.  
   * El presupuesto pasa al estado PENDIENTE\_APROBACION.  
5. **Control y Aprobación del Dueño:**  
   * El dueño recibe una alerta o ingresa a su vista del Dashboard.  
   * Revisa la distribución del corte, el desglose económico y el fotomontaje.  
   * Si todo es correcto, presiona el botón **"Aprobar Cotización"**.  
6. **Generación de PDF y Envío Automático:**  
   * WeasyPrint genera el PDF corporativo con el render del fotomontaje y los costos detallados.  
   * El sistema despacha el archivo al número de WhatsApp o correo del cliente vía Twilio/SendGrid y actualiza el estado a ENVIADO.

## **4\. Algoritmo e Ingesta de Vectores (Core de Nesting en Python)**

A continuación se presenta la estructura conceptual en Python para recibir los vectores y ejecutar el proceso geométrico de Nesting:

`# app/services/nesting.py`  
`import svgpathtools`  
`from shapely.geometry import Polygon, MultiPolygon`  
`from rectpack import newPacker`  
`import math`

`class NestingEngine:`  
    `def __init__(self, chapa_ancho_mm: float, chapa_alto_mm: float, margen_corte_mm: float = 5.0):`  
        `self.chapa_ancho = chapa_ancho_mm`  
        `self.chapa_alto = chapa_alto_mm`  
        `self.margen = margen_corte_mm`

    `def parse_svg_to_polygons(self, svg_file_path: str):`  
        `paths, attributes = svgpathtools.svg2paths(svg_file_path)`  
        `polygons = []`  
        `for path in paths:`  
            `# Obtener el Bounding Box de cada figura vectorial`  
            `xmin, xmax, ymin, ymax = path.bbox()`  
            `ancho = (xmax - xmin) + self.margen`  
            `alto = (ymax - ymin) + self.margen`  
            `polygons.append({`  
                `'ancho': ancho,`  
                `'alto': alto,`  
                `'bbox': (xmin, xmax, ymin, ymax)`  
            `})`  
        `return polygons`

    `def calcular_nesting_optimizado(self, piezas: list):`  
        `"""`  
        `Aplica un algoritmo de 2D Bin Packing (rectpack) para empaquetar`  
        `los rectángulos contenedores de las piezas vectoriales en las chapas.`  
        `"""`  
        `packer = newPacker(rotation=True) # Permite rotación de piezas 90 grados`

        `# Agregar piezas al empaquetador`  
        `for idx, pieza in enumerate(piezas):`  
            `packer.add_rect(pieza['ancho'], pieza['alto'], rid=idx)`

        `# Agregar planchas (Chapas) indefinidas para calcular cuántas se consumen`  
        `# Se asume un límite inicial de 100 chapas`  
        `for i in range(100):`  
            `packer.add_bin(self.chapa_ancho, self.chapa_alto)`

        `packer.pack()`

        `chapas_utilizadas = len(packer.bin_list())`  
        `area_chapa_individual = self.chapa_ancho * self.chapa_alto`  
        `area_total_disponible = chapas_utilizadas * area_chapa_individual`  
          
        `area_piezas_total = sum([p['ancho'] * p['alto'] for p in piezas])`  
        `area_desperdicio = area_total_disponible - area_piezas_total`  
        `porcentaje_desperdicio = (area_desperdicio / area_total_disponible) * 100`

        `return {`  
            `"chapas_requeridas": chapas_utilizadas,`  
            `"area_utilizada_mm2": area_piezas_total,`  
            `"area_desperdicio_mm2": area_desperdicio,`  
            `"porcentaje_desperdicio": round(porcentaje_desperdicio, 2),`  
            `"distribucion": packer.rect_list()`  
        `}`

## **5\. Integración con IA para Fotomontaje**

Para la fusión del cartel en la fachada del local sin intervención manual de Photoshop, se utiliza la API de Replicate conectada a un pipeline de ControlNet (Inpainting / Depth-to-Image).

### **Flujo de Llamada a la API de IA:**

`# app/services/ai_montage.py`  
`import replicate`  
`import os`

`class AIMontageService:`  
    `def __init__(self):`  
        `self.api_token = os.getenv("REPLICATE_API_TOKEN")`

    `def generar_fotomontaje(self, foto_fachada_url: str, imagen_cartel_png_url: str, prompt_contexto: str) -> str:`  
        `"""`  
        `Usa ControlNet Inpainting para superponer de forma fotorrealista`  
        `el cartel vectorial sobre el frente del local.`  
        `"""`  
        `output = replicate.run(`  
            `"stability-ai/stable-diffusion-inpainting:105217983633857e4e1f7",`  
            `input={`  
                `"image": foto_fachada_url,`  
                `"mask": imagen_cartel_png_url,`  
                `"prompt": f"A realistic photo of a commercial building storefront with a modern sign that says '{prompt_contexto}', professional lighting, clean architectural photo, 8k",`  
                `"negative_prompt": "blurry, low quality, distorted text, unnatural shadows",`  
                `"num_inference_steps": 30`  
            `}`  
        `)`  
        `# Retorna la URL de la imagen renderizada por la IA`  
        `return output[0]`

## **6\. Arquitectura de Infraestructura e Implementación en Producción**

Para garantizar confiabilidad, velocidad y mantenimiento aislado, la solución se despliega utilizando contenedores de Docker coordinados con Docker Compose en un servidor privado (VPS).

`# docker-compose.yml`  
`version: '3.8'`

`services:`  
  `db:`  
    `image: postgres:15-alpine`  
    `container_name: carteleria_db`  
    `environment:`  
      `POSTGRES_DB: carteleria_db`  
      `POSTGRES_USER: admin_user`  
      `POSTGRES_PASSWORD: SecretPassword123`  
    `ports:`  
      `- "5432:5432"`  
    `volumes:`  
      `- postgres_data:/var/lib/postgresql/data`

  `redis:`  
    `image: redis:7-alpine`  
    `container_name: carteleria_redis`  
    `ports:`  
      `- "6379:6379"`

  `api:`  
    `build: ./backend`  
    `container_name: carteleria_api`  
    `command: uvicorn app.main:app --host 0.0.0.0 --port 8000`  
    `volumes:`  
      `- ./backend:/app`  
    `ports:`  
      `- "8000:8000"`  
    `environment:`  
      `- DATABASE_URL=postgresql://admin_user:SecretPassword123@db:5432/carteleria_db`  
      `- REDIS_URL=redis://redis:6379/0`  
      `- REPLICATE_API_TOKEN=${REPLICATE_API_TOKEN}`  
    `depends_on:`  
      `- db`  
      `- redis`

  `worker:`  
    `build: ./backend`  
    `container_name: carteleria_celery_worker`  
    `command: celery -A app.tasks worker --loglevel=info`  
    `environment:`  
      `- DATABASE_URL=postgresql://admin_user:SecretPassword123@db:5432/carteleria_db`  
      `- REDIS_URL=redis://redis:6379/0`  
    `depends_on:`  
      `- redis`  
      `- api`

  `frontend:`  
    `build: ./frontend`  
    `container_name: carteleria_web`  
    `ports:`  
      `- "3000:3000"`  
    `depends_on:`  
      `- api`

`volumes:`  
  `postgres_data:`

## **7\. Plan de Entregables e Hitos de Desarrollo**

| Fase | Entregable / Hito | Descripción de la Tarea | Tiempo Estimado   |
| :---- | :---- | :---- | :---- |
| **Fase 1** | Backend Base & Nesting Engine | Configuración de FastAPI, PostgreSQL y desarrollo del algoritmo de ingestión vectorial y cálculo de chapa. | Semana 1 \- 2 |
| **Fase 2** | Integración de IA & PDF | Conexión con la API de Replicate para el fotomontaje y plantilla WeasyPrint para presupuestos en PDF. | Semana 3 |
| **Fase 3** | Panel Frontend (No-Code UX) | Desarrollo de la interfaz visual limpia en React (vistas para Diseñador y vista para Aprobación del Dueño). | Semana 4 |
| **Fase 4** | Notificaciones & Despliegue | Integración de Twilio (WhatsApp), Dockerización del sistema y puesta en producción en servidor VPS. | Semana 5 |

