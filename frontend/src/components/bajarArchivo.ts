/** Baja un archivo que llegó del servidor (un PDF) con el nombre que se le da. */
export function bajarArchivo(contenido: Blob, nombre: string) {
  const url = URL.createObjectURL(contenido);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  enlace.click();
  // El navegador ya tomó el archivo: se suelta la dirección temporal.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
