# B1 — El servidor y el dominio: comparación

> **Estado:** propuesta para decidir (2026-11-18). Lo que se elija acá cierra `T-01` (el servidor) y `T-02` (el dominio y el certificado) en [`REGISTRO.md`](../../REGISTRO.md). Es el paso B1 de [`plan.md`](plan.md).
>
> **Los precios son del 2026-11-18 y cambian:** confirmarlos al contratar. Cada número dice de dónde salió.

## En corto

- **El sistema es interno:** lo usan el dueño y los diseñadores, no es una página pública. Eso no cambia qué servidor hace falta, pero el dominio puede ser cualquiera.
- **Servidor — dos candidatos:**
  - **DonWeb, Argentina:** 4 procesadores, 8 GB de memoria y 30 GB de disco a **ARS 34.830,20 por mes de lista** (ARS 15.673,60 con la promoción de hoy), **en pesos y con IVA incluido**. Es el más barato por lejos, pero hay tres cosas sin confirmar: dónde está el centro de datos, cómo rinden sus procesadores con Sparrow y si alcanza el disco.
  - **Vultr, Santiago de Chile:** 4 procesadores, 8 GB y 160 GB a **US$ 40 por mes**, que pagando con tarjeta argentina quedan en unos **ARS 80.000 a 93.000**. Es lo más cercano que se midió (38 ms) y tiene precio transparente: lo seguro.
- **Recomendación:** **probar DonWeb un mes** y medir allá las tres dudas. Si alguna falla, pasar a Vultr en Santiago. Contratar recién cuando Vale tenga lista la entrega A3 (el Docker): antes no hay nada que poner adentro.
- **Dominio:** cualquier dominio barato a nombre de la empresa. Por ejemplo, `anibaldumit.com.ar` está libre y cuesta **ARS 8.500 por año**; el sistema quedaría en `presupuestos.anibaldumit.com.ar`. El candado (HTTPS) es gratis.
- **Aparte, para avisarle al dueño:** el dominio `.com` de su web **se venció** y está por liberarse, alrededor del 2026-11-20 (ver [El dominio](#el-dominio)).
- **Las cuentas, a nombre de la empresa:** el servidor y el dominio son de ellos. Enzo y Vale entran como usuarios invitados.

## Qué necesita el servidor

| Qué | Cuánto | Por qué |
|---|---|---|
| Procesadores | **4 o más** | Hasta tres anidados de Sparrow a la vez terminaron bien con 4 núcleos, medido el 2026-10-23 (`SUP-42`) |
| Memoria | **8 GB** (supuesto) | La base, el servidor, Caddy, las copias y hasta tres anidados. Se mide de verdad en la fase B |
| Disco | **unos 50 GB** (estimado) | El sistema operativo, las imágenes de Docker (3 a 6 GB, estimado) y los datos, que son chicos (la base y los DXF subidos). Las copias van a otro lado (`T-06`) |
| Lugar | **Cerca de Argentina** | Cada clic de la pantalla es un pedido al servidor. A 150 ms se nota al mover piezas entre chapas; a 40 ms, no |
| Tipo de procesador | Intel/AMD o ARM | Sparrow (`spyrrow 0.9.0`) publica versiones para Linux en los dos (verificado en PyPI) |

## La latencia, medida desde la conexión de Enzo

La latencia es lo que tarda un paquete en ir al servidor y volver. Se midió con `ping` (5 intentos, promedio) el 2026-11-18:

| Dónde | Proveedor | Latencia |
|---|---|---|
| Santiago de Chile | Vultr | **38 ms** |
| São Paulo | Vultr | **49 ms** |
| Miami | Vultr | 146 ms |
| Ashburn (EE. UU., costa este) | Hetzner | 158 ms |
| Nueva Jersey | Vultr | 165 ms |
| Hillsboro (EE. UU., costa oeste) | Hetzner | 220 ms |
| Falkenstein (Alemania) | Hetzner | 316 ms |
| Nueva York | DigitalOcean | no contesta el `ping`; se estima como Nueva Jersey (unos 160 ms) |
| DonWeb | DonWeb | **sin medir:** no publica direcciones de prueba; se mide con el servidor de prueba |

## La comparación

| | DonWeb — Argentina (?) | Vultr — Santiago | Hostinger — Brasil | DigitalOcean — Nueva York |
|---|---|---|---|---|
| **Plan** | Cloud Server | Regular Cloud Compute (`vc2-4c-8gb`) | KVM 4 | Basic Droplet |
| **Procesadores / memoria / disco** | 4 / 8 GB / **30 GB** NVMe | 4 / 8 GB / 160 GB SSD | 4 / 16 GB / 200 GB NVMe | 4 / 8 GB / 160 GB |
| **Precio por mes** | **ARS 34.830,20** de lista; ARS 15.673,60 con la promoción (55 % menos). En pesos, **IVA incluido** | **US$ 40** | US$ 12,99 en promoción; renueva a **US$ 28,99** | US$ 48 |
| **En pesos, por mes** (aprox.) | ARS 15.674 a 34.830 | ARS 80.000 a 93.000 | ARS 620.000 a 725.000 de una vez por los 2 años; después, unos ARS 58.000 a 67.000 | ARS 96.000 a 112.000 |
| **Compromiso** | Pago mensual (según el resumen de su página; confirmar). También ofrece de 2 a 10 años | Ninguno: por hora, con tope mensual | **24 meses por adelantado** (US$ 311,76) | Ninguno |
| **Latencia** | Sin medir | **38 ms** (medida) | Sin medir (la página no dice la ciudad) | ~160 ms (estimada) |
| **A favor** | El más barato. En pesos: sin percepción del 30 % ni IVA del exterior. Empresa argentina, soporte en castellano. La empresa ya es cliente (su `.com` estaba registrado ahí). El configurador deja elegir procesadores, memoria y disco por separado | Lo más cerca entre lo medido. Precio de su lista oficial. IP pública incluida. Si el anidado anda lento, se pasa en minutos al plan de alto rendimiento (`vhp-4c-8gb-amd`, US$ 48) | El más barato en dólares, con el doble de memoria | Muy usado y con buena documentación |
| **En contra** | **Sin confirmar:** dónde está el centro de datos (la página dice «cuatro centros de datos» sin nombrar el país), cómo rinden los procesadores con Sparrow, si factura A o B, y cuánto sale después de la promoción. El disco de 30 GB queda justo: subirlo a unos 50 GB en el configurador | Se paga en dólares con tarjeta (ver impuestos); sin factura argentina | Dos años pagados de entrada. Es una promoción de Black Friday. Los procesadores son compartidos, y no está medido cómo rinde con Sparrow usando los 4 durante minutos | No tiene región en Sudamérica, y cuesta más que Vultr en Santiago |

**El mismo plan de Vultr en São Paulo cuesta US$ 60** (Vultr le pone 50 % de recargo a esa región); Santiago no tiene recargo y además está más cerca.

**Descartados:**
- **Hetzner:** subió los precios dos veces en 2026. En EE. UU., el plan de 4 procesadores y 8 GB (CPX31) cuesta € 62,99 por mes más IVA, y está a 158 ms. En Europa el CX33 cuesta € 8,99, pero está a 316 ms y la página lo da por agotado.
- **Akamai (ex Linode), São Paulo:** no publica el precio de esa región (dice que varía); en su lista general, el plan de 8 GB y 4 procesadores cuesta US$ 48.

### Qué medir en el mes de prueba de DonWeb

Antes de pagar el mes, preguntarle a DonWeb **en qué país queda el servidor** y **si factura A o B**. Ya con el servidor:

1. **Latencia:** `ping` desde la PC de la cartelería. Sirve si da menos de unos 60 ms.
2. **Sparrow:** correr tres anidados del Complejo a la vez, como la medición del 2026-10-23, y comparar los tiempos con los de la máquina de Enzo. Sirve si terminan bien y en tiempos parecidos.
3. **Disco y memoria:** con todo levantado, mirar cuánto se usa. Esto además mide la memoria, que el plan deja para la fase B.

Si alguna de las tres falla, Vultr en Santiago: se contrata en minutos y el despliegue es el mismo.

## Lo que cuesta en pesos

**DonWeb** cobra en pesos con el IVA incluido: el precio de la página es lo que se paga.

Pagar en dólares con una tarjeta argentina a un proveedor del exterior (Vultr, Hostinger, DigitalOcean) suma, sobre el precio:

- **Una percepción del 30 % a cuenta de Ganancias.** Se puede recuperar en algunos casos, y no se cobra si el resumen se paga con dólares propios.
- **IVA del 21 % por servicios digitales del exterior,** si el proveedor está en la lista de ARCA (RG 4240).

Las cuentas en pesos de la tabla usan el **dólar tarjeta en unos ARS 2.000** (iProfesional, 2026-11-09), que ya trae la percepción, y suman el IVA donde podría aplicar. Como lo paga la empresa, **conviene que su contador diga cómo pagarlo**: con qué tarjeta, si usa dólares propios y cómo lo registra.

## El dominio

### Para el sistema

Como el sistema es interno, el dominio es solo la dirección para entrar: no tiene que ser el de la marca. Pero **hace falta uno**, porque el certificado gratuito que pone el candado (HTTPS, de Let's Encrypt, que Caddy saca y renueva solo) se emite para un nombre. Sin candado, la contraseña y la sesión viajarían sin cifrar, y en producción el sistema exige HTTPS para la cookie de sesión.

**Propuesta:**
1. Registrar **`anibaldumit.com.ar`** en NIC Argentina: **ARS 8.500 por año**, a nombre del dueño, con su CUIT y su clave fiscal de ARCA. Estaba libre el 2026-11-18, igual que `megacarteles.com.ar` y `megacarteles.com`.
2. Delegarlo a un servicio de DNS gratuito (el de Cloudflare, o el del proveedor del servidor si lo ofrece) y crear un registro `presupuestos` que apunte a la IP del servidor. El sistema queda en **`presupuestos.anibaldumit.com.ar`**.
3. **Renovación automática** del dominio, con una tarjeta que no venza (ver lo que pasó con el `.com`).

El certificado no cuesta nada. El dominio, unos ARS 8.500 por año.

### Aparte, para el dueño: su `.com` se venció

No es parte de este proyecto, pero conviene avisarle hoy. Según el registro oficial del `.com` (RDAP de Verisign, consultado el 2026-11-18):

| | |
|---|---|
| Dominio | `anibaldumit.com` (la web que imprime el PDF de los presupuestos) |
| Registrado | 2015-09-28, con Dattatec (DonWeb) |
| Venció | **2026-09-28** |
| Estado | **«pending delete»** desde el 2026-11-15; los servidores DNS dicen «dominio suspendido» |

**Qué significa «pending delete»:** ya no se puede renovar ni rescatar. Dura 5 días; después el dominio se libera y lo registra el primero que llegue, **alrededor del 2026-11-20** (estimado). Si el dueño lo quiere de vuelta, tiene que registrarlo apenas se libere: a mano, en un registrador barato (Cloudflare lo vende a costo, unos US$ 10 por año), o con un servicio de *backorder*, que lo pide solo en el momento en que se libera.

Mientras tanto, la web impresa en el PDF no anda. Si no lo recupera, hay que cambiar o sacar la web en `backend/local/empresa/datos.json`.

## Próximos pasos

| Quién | Qué |
|---|---|
| **Enzo, con el dueño** | Elegir el servidor y crear la cuenta **a nombre de la empresa** (con un mail de la empresa), invitando a Enzo y a Vale. Si es DonWeb, preguntarles antes el país del centro de datos y el tipo de factura. Recién al contratar: pasar la IP y el acceso por clave (nunca la contraseña por chat) |
| **El dueño** | Registrar el `.com.ar` con su clave fiscal. Decidir si recupera el `.com` (alrededor del 2026-11-20) |
| **Enzo** | Si el `.com` no vuelve, cambiar la web en `datos.json` (la de su máquina y la de la demo) |
| **Vale** | Cuando la entrega A3 esté lista: B2 en adelante (preparar la máquina, el dominio y el certificado, el primer despliegue) y las mediciones del mes de prueba |

## De dónde salió cada dato

- **DonWeb:** [donweb.com/es-ar/hosting-cloud-servers-vps](https://donweb.com/es-ar/hosting-cloud-servers-vps), leída el 2026-11-18. Los precios y «Precios en Pesos Argentinos (IVA incluido)» se leyeron textuales. El pago mensual y que los servidores estén en Argentina vienen de un resumen de la página, no del texto: confirmar.
- **Vultr:** lista pública de planes (`https://api.vultr.com/v2/plans`), con el recargo por región (`location_cost`), consultada el 2026-11-18.
- **Hetzner:** [hetzner.com/cloud](https://www.hetzner.com/cloud) y sus páginas *cost-optimized* y *regular-performance*, leídas el 2026-11-18. Las subas de 2026: [devshot.co](https://devshot.co/blog/hetzner-cloud-pricing) y [trackvps.com](https://trackvps.com/hetzner-cloud-pricing).
- **DigitalOcean:** [digitalocean.com/pricing/droplets](https://www.digitalocean.com/pricing/droplets), leída el 2026-11-18.
- **Hostinger:** [hostinger.com/vps-hosting](https://www.hostinger.com/vps-hosting), leída el 2026-11-18 (promoción de Black Friday).
- **Akamai:** [akamai.com/cloud/pricing/cpu](https://www.akamai.com/cloud/pricing/cpu) y la página de São Paulo, leídas el 2026-11-18.
- **Sparrow en ARM:** [pypi.org/project/spyrrow/0.9.0](https://pypi.org/project/spyrrow/0.9.0/#files).
- **NIC Argentina:** [nic.ar/es/dominios/aranceles](https://nic.ar/es/dominios/aranceles). Disponibilidad: RDAP de NIC Argentina (`rdap.nic.ar`) y de Verisign (`rdap.verisign.com`), consultados el 2026-11-18.
- **Cloudflare (.com):** sin página oficial a mano; los comparadores coinciden en unos US$ 10,46 por año ([domaindetails.com](https://domaindetails.com/kb/getting-started/best-domain-registrars-compared)).
- **Impuestos y dólar tarjeta:** [iProfesional, 2026-11-09](https://www.iprofesional.com/finanzas/468686-dolar-tarjeta-caro-recargo-extra-golpea-consumos-noviembre-2026), [ayuda de Banco Galicia](https://ayuda.bancogalicia.com.ar/n4/como-funcionan-los-impuestos-en-las-compras-de-dolares) y [RG 4240 (blogdelcontador)](https://siap.blogdelcontador.com.ar/rubro_normativa/regimen-de-percepcion-iva-rg-4240/). Para el caso de la empresa, manda su contador.
