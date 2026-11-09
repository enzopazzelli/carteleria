import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { entrar as entrarAlSistema, quienSoy, salir as salirDelSistema, type Yo } from "../api/acceso";
import { alPerderLaSesion, ApiError } from "../api/client";

// Quién entró (1.1). Al abrirse la pantalla se le pregunta al servidor si hay una sesión; si el servidor
// responde 401 en cualquier momento, `client.ts` avisa y la pantalla vuelve a «Entrar».

interface Sesion {
  /** Quién entró; `null` si nadie. */
  yo: Yo | null;
  /** Mientras se le pregunta al servidor si hay una sesión abierta. */
  cargando: boolean;
  /** Si al abrir no se pudo hablar con el servidor, el motivo (para mostrarlo en «Entrar»). */
  errorDeConexion: string | null;
  entrar: (usuario: string, contrasena: string, mantener: boolean) => Promise<void>;
  salir: () => Promise<void>;
  /** Vuelve a preguntar quién soy (después de cambiar la contraseña, por ejemplo). */
  recargar: () => Promise<void>;
}

const Contexto = createContext<Sesion | null>(null);

export function SesionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [yo, setYo] = useState<Yo | null>(null);
  const [cargando, setCargando] = useState(true);
  const [errorDeConexion, setErrorDeConexion] = useState<string | null>(null);

  // Lo que quedó guardado de una persona no se le muestra a la siguiente.
  const olvidarTodo = useCallback(() => queryClient.clear(), [queryClient]);

  useEffect(() => {
    let vigente = true;
    alPerderLaSesion(() => {
      setYo(null);
      olvidarTodo();
    });
    quienSoy()
      .then((quien) => vigente && setYo(quien))
      .catch((e: unknown) => {
        if (!vigente) return;
        setYo(null);
        if (e instanceof ApiError && e.status === 0) setErrorDeConexion(e.message);
      })
      .finally(() => vigente && setCargando(false));
    return () => {
      vigente = false;
      alPerderLaSesion(null);
    };
  }, [olvidarTodo]);

  const entrar = useCallback(
    async (usuario: string, contrasena: string, mantener: boolean) => {
      const quien = await entrarAlSistema(usuario, contrasena, mantener);
      olvidarTodo();
      setErrorDeConexion(null);
      setYo(quien);
    },
    [olvidarTodo],
  );

  const salir = useCallback(async () => {
    try {
      await salirDelSistema();
    } catch {
      // Si no se pudo avisar al servidor, igual se sale de la pantalla: la sesión vence sola.
    }
    olvidarTodo();
    setYo(null);
  }, [olvidarTodo]);

  const recargar = useCallback(async () => {
    setYo(await quienSoy());
  }, []);

  const valor = useMemo(
    () => ({ yo, cargando, errorDeConexion, entrar, salir, recargar }),
    [yo, cargando, errorDeConexion, entrar, salir, recargar],
  );
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSesion(): Sesion {
  const sesion = useContext(Contexto);
  if (!sesion) throw new Error("useSesion tiene que usarse dentro de SesionProvider.");
  return sesion;
}
