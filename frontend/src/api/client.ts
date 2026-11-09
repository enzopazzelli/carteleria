import type { ChapaNombrada } from "./mensajes";

/** Todo pedido va al mismo origen que la pantalla, bajo `/api`: en desarrollo lo reenvía Vite al servidor
 * (sacando el prefijo) y en producción lo hace el proxy. Así la cookie de sesión viaja sola y no hace falta
 * permitir pedidos de otros orígenes (1.1). */
export const API_BASE = "/api";

/** Va en todo pedido: una página ajena no puede agregarlo sin permiso del servidor, y el servidor lo exige
 * en cada pedido que cambia algo (defensa contra pedidos falsificados, 1.1). */
export const ENCABEZADO_DE_PEDIDO = "X-Cartel-Pedido";

let alPerder: (() => void) | null = null;

/** Registra a quién avisar cuando el servidor dice que ya no hay sesión (401), para volver a «Entrar».
 * Con `null` se deja de avisar. */
export function alPerderLaSesion(callback: (() => void) | null): void {
  alPerder = callback;
}

/** El único pedido donde un 401 no significa «se perdió la sesión»: es la contraseña mala. */
const RUTA_DE_ENTRAR = "/acceso/entrar";

/** Lo que se muestra cuando el pedido no llega al servidor (A9). */
export const SIN_CONEXION = "No se pudo conectar con el servidor: revisá que esté prendido.";

export class ApiError extends Error {
  status: number;
  piezasInvalidas: number[];
  /** Lo técnico, para «Ver detalle técnico» (A9). */
  detalle: string | null;
  /** Las piezas y chapas que nombra el mensaje, para sus miniaturas. */
  piezas: number[];
  chapas: ChapaNombrada[];
  constructor(
    status: number,
    message: string,
    piezasInvalidas: number[] = [],
    extra: { detalle?: string | null; piezas?: number[]; chapas?: ChapaNombrada[] } = {},
  ) {
    super(message);
    this.status = status;
    this.piezasInvalidas = piezasInvalidas;
    this.detalle = extra.detalle ?? null;
    this.piezas = extra.piezas ?? [];
    this.chapas = extra.chapas ?? [];
    this.name = "ApiError";
  }
}

function numeros(valor: unknown): number[] {
  return Array.isArray(valor) ? valor.filter((x): x is number => typeof x === "number") : [];
}

function chapas(valor: unknown): ChapaNombrada[] {
  return Array.isArray(valor)
    ? valor.filter((c): c is ChapaNombrada => typeof c?.ejecucion_id === "number" && typeof c?.plancha === "number")
    : [];
}

/** El error de una respuesta que no salió bien, desde su cuerpo: `detail`
 * como texto (antes de A9) o como `{mensaje, detalle, piezas, chapas, piezas_invalidas}`. */
export function errorDesdeCuerpo(status: number, cuerpo: unknown): ApiError {
  const detalle = (cuerpo as { detail?: unknown } | null)?.detail;
  if (typeof detalle === "string") return new ApiError(status, detalle);
  const d = (detalle ?? {}) as Record<string, unknown>;
  const mensaje = typeof d.mensaje === "string" ? d.mensaje : `El servidor respondió con un error (${status}).`;
  return new ApiError(status, mensaje, numeros(d.piezas_invalidas), {
    detalle: typeof d.detalle === "string" ? d.detalle : null,
    piezas: numeros(d.piezas),
    chapas: chapas(d.chapas),
  });
}

/** `fetch`, pero un pedido que no llega es un `ApiError` en castellano, y todo pedido lleva el encabezado propio. */
async function pedir(path: string, init: RequestInit = {}): Promise<Response> {
  let respuesta: Response;
  try {
    respuesta = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { ...(init.headers as Record<string, string> | undefined), [ENCABEZADO_DE_PEDIDO]: "1" },
    });
  } catch {
    throw new ApiError(0, SIN_CONEXION);
  }
  if (respuesta.status === 401 && path !== RUTA_DE_ENTRAR) alPerder?.();
  return respuesta;
}

async function manejarRespuesta<T>(respuesta: Response): Promise<T> {
  if (!respuesta.ok) {
    throw errorDesdeCuerpo(respuesta.status, await respuesta.json().catch(() => null));
  }
  if (respuesta.status === 204) {
    return undefined as T;
  }
  return respuesta.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const respuesta = await pedir(path);
  return manejarRespuesta<T>(respuesta);
}

/** Para bajar un archivo (el PDF del presupuesto). Si la API responde
 * con un error, tira el mismo `ApiError` que el resto. */
export async function apiGetArchivo(path: string): Promise<Blob> {
  const respuesta = await pedir(path);
  if (!respuesta.ok) {
    return manejarRespuesta<never>(respuesta);
  }
  return respuesta.blob();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const respuesta = await pedir(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return manejarRespuesta<T>(respuesta);
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const respuesta = await pedir(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return manejarRespuesta<T>(respuesta);
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const respuesta = await pedir(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return manejarRespuesta<T>(respuesta);
}

export async function apiDelete(path: string): Promise<void> {
  const respuesta = await pedir(path, { method: "DELETE" });
  return manejarRespuesta<void>(respuesta);
}

export async function apiPostForm<T>(path: string, formData: FormData): Promise<T> {
  const respuesta = await pedir(path, { method: "POST", body: formData });
  return manejarRespuesta<T>(respuesta);
}
