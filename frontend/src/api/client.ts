const BASE_URL = "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  piezasInvalidas: number[];
  constructor(status: number, message: string, piezasInvalidas: number[] = []) {
    super(message);
    this.status = status;
    this.piezasInvalidas = piezasInvalidas;
    this.name = "ApiError";
  }
}

async function manejarRespuesta<T>(respuesta: Response): Promise<T> {
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => null);
    const detalle = cuerpo?.detail;
    const mensaje = typeof detalle === "string" ? detalle :
      typeof detalle?.mensaje === "string" ? detalle.mensaje : `Error ${respuesta.status}`;
    const ids = Array.isArray(detalle?.piezas_invalidas)
      ? detalle.piezas_invalidas.filter((id: unknown) => typeof id === "number") : [];
    throw new ApiError(respuesta.status, mensaje, ids);
  }
  if (respuesta.status === 204) {
    return undefined as T;
  }
  return respuesta.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const respuesta = await fetch(`${BASE_URL}${path}`);
  return manejarRespuesta<T>(respuesta);
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const respuesta = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return manejarRespuesta<T>(respuesta);
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const respuesta = await fetch(`${BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return manejarRespuesta<T>(respuesta);
}

export async function apiDelete(path: string): Promise<void> {
  const respuesta = await fetch(`${BASE_URL}${path}`, { method: "DELETE" });
  return manejarRespuesta<void>(respuesta);
}

export async function apiPostForm<T>(path: string, formData: FormData): Promise<T> {
  const respuesta = await fetch(`${BASE_URL}${path}`, { method: "POST", body: formData });
  return manejarRespuesta<T>(respuesta);
}
