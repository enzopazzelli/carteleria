@echo off
rem ---------------------------------------------------------------------------
rem  Abre el visor de anidado sin tocar la terminal: doble click y listo.
rem
rem  Se queda abierto a propósito. La ventana ES el servidor: si se cierra,
rem  el visor deja de funcionar. Ahi tambien aparecen los errores.
rem
rem  Para cambiar el DXF, el material o cualquier cosa, NO hace falta tocar
rem  esto: se hace desde la pagina.
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0backend"

set DXF=..\modelos\repisas.dxf
set ESCALA=10
set CATALOGO=local\catalogo_chapa.json

if not exist "%CATALOGO%" (
  echo.
  echo  No existe %CATALOGO%.
  echo  Hay que generarlo una sola vez desde el Excel del cliente:
  echo.
  echo     python scripts\extraer_catalogo_chapa_xlsx.py --xlsx "..\CARTELERIA 2026.xlsx" --out %CATALOGO%
  echo.
  pause
  exit /b 1
)

if not exist "%DXF%" (
  echo.
  echo  No existe %DXF%.
  echo  Editar la linea "set DXF=" de este archivo, o dejar cualquier DXF ahi.
  echo.
  pause
  exit /b 1
)

echo.
echo  Levantando el visor... la pagina se abre sola en el navegador.
echo  DEJAR ESTA VENTANA ABIERTA mientras se usa el visor.
echo  Para cerrarlo: Ctrl+C aca, o cerrar esta ventana.
echo.

python -X utf8 scripts\servidor_visor.py --dxf "%DXF%" --escala-a-mm %ESCALA% --catalogo "%CATALOGO%" --generaciones 1 --poblacion 2

echo.
echo  El visor se cerro.
echo.
echo  Si lo cerraste con un anidado corriendo, puede haber quedado un proceso
echo  'node' dando vueltas. Para chequear y limpiarlo:
echo.
echo     powershell -Command "Get-Process node -ErrorAction SilentlyContinue"
echo     powershell -Command "Get-Process node ^| Stop-Process -Force"
echo.
pause
