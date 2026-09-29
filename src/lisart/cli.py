"""Linea de comandos: `lisart <comando>`.

    lisart init                 crea las carpetas y los CSV vacios
    lisart validate [tabla]     revisa que los datos cumplan el esquema
    lisart describe [tabla]     muestra el esquema de una tabla
    lisart docs                 regenera docs/modelo_de_datos.md
    lisart vault                regenera el vault de Obsidian (grafo)
    lisart ingest jotform       baja las inscripciones nuevas de Jotform
    lisart ingest catalogos     lee el Excel de programas, precios y descuentos
    lisart procesar inscripciones  arma personas, alumnos y relaciones
    lisart ui                   abre la pantalla para ver y editar
    lisart ui --profesores      abre la pantalla de agenda de profesores
    lisart backup               respalda las tablas
    lisart demo [--limpiar]     siembra o borra datos de prueba
    lisart proyeccion           proyeccion de pago mensual
    lisart descuentos           mantiene el archivo de quien tiene descuento
    lisart guia                 regenera los PDF de docs/ desde su markdown
    lisart guia codigo          solo uno de ellos
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lisart import io
from lisart.config import LAYERS, PROJECT_ROOT, data_dir, layer_dir, ruta_corta
from lisart.tables import REGISTRY
from lisart.validate import has_errors, validate_all, validate_table

DOCS_PATH = PROJECT_ROOT / "docs" / "modelo_de_datos.md"


def cmd_init(args: argparse.Namespace) -> int:
    for layer in LAYERS:
        d = layer_dir(layer)
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()
    from lisart.backup import backups_dir

    backups_dir().mkdir(parents=True, exist_ok=True)
    (backups_dir() / ".gitkeep").touch()
    print(f"Carpetas de datos listas en {data_dir()}")

    creadas = 0
    for tbl in REGISTRY.in_dependency_order():
        if tbl.path.exists():
            print(f"  = {tbl.name:26s} ya existia")
            continue
        io.write_table(tbl, io.empty_frame(tbl), validate=False)
        print(f"  + {tbl.name:26s} creada vacia ({tbl.ownership})")
        creadas += 1

    print(f"\n{creadas} tabla(s) nueva(s), {len(REGISTRY)} en total.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    if args.tabla:
        issues = validate_table(args.tabla)
    else:
        issues = validate_all()

    errores = [i for i in issues if i.severity == "error"]
    avisos = [i for i in issues if i.severity == "warning"]

    for issue in errores + avisos:
        print(issue)

    if not issues:
        print(f"Todo en orden: {len(REGISTRY)} tabla(s) sin problemas.")
    else:
        print(f"\n{len(errores)} error(es), {len(avisos)} aviso(s).")
    return 1 if has_errors(issues) else 0


def cmd_describe(args: argparse.Namespace) -> int:
    tablas = [REGISTRY.get(args.tabla)] if args.tabla else list(REGISTRY.in_dependency_order())
    for tbl in tablas:
        existe = "si" if tbl.path.exists() else "NO (correr lisart init)"
        print(f"\n{tbl.name}  [{tbl.layer} / {tbl.ownership}]")
        print(f"  {tbl.description}")
        print(f"  archivo: {tbl.path}  existe: {existe}")
        print(f"  llave primaria: {', '.join(tbl.primary_key)}")
        if not args.tabla:
            continue
        print("  columnas:")
        for col in tbl.columns:
            marcas = []
            if col.name in tbl.primary_key:
                marcas.append("PK")
            if not col.required:
                marcas.append("opcional")
            if col.unique:
                marcas.append("unica")
            if col.choices:
                marcas.append("catalogo: " + "|".join(col.choices))
            sufijo = f"  ({'; '.join(marcas)})" if marcas else ""
            print(f"    {col.name:24s} {col.dtype:9s} {col.description}{sufijo}")
        for fk in tbl.foreign_keys:
            print(f"  referencia: {fk.column} -> {fk.ref_table}.{fk.ref_column}")
    return 0


def _render_docs() -> str:
    lineas = [
        "# Modelo de datos",
        "",
        "> Archivo generado por `lisart docs`. **No editarlo a mano**: se sobrescribe.",
        "> La fuente de verdad es `src/lisart/tables.py`.",
        "",
        "## Tablas",
        "",
        "| Tabla | Capa | Quien la edita | Descripcion |",
        "| --- | --- | --- | --- |",
    ]
    quien = {"managed": "codigo", "hand_edited": "a mano"}
    for tbl in REGISTRY.in_dependency_order():
        desc = " ".join(tbl.description.split())
        lineas.append(
            f"| [`{tbl.name}`](#{tbl.name}) | {tbl.layer} "
            f"| {quien[tbl.ownership]} | {desc} |"
        )

    for tbl in REGISTRY.in_dependency_order():
        lineas += [
            "",
            f"## {tbl.name}",
            "",
            " ".join(tbl.description.split()),
            "",
            f"- Archivo: `data/{tbl.layer}/{tbl.name}.csv`",
            f"- Llave primaria: {', '.join(f'`{c}`' for c in tbl.primary_key)}",
            f"- Quien la edita: {quien[tbl.ownership]}",
            "",
            "| Columna | Tipo | Obligatoria | Reglas | Descripcion |",
            "| --- | --- | --- | --- | --- |",
        ]
        for col in tbl.columns:
            reglas = []
            if col.name in tbl.primary_key:
                reglas.append("PK")
            if col.unique:
                reglas.append("unica")
            if col.choices:
                reglas.append("uno de: " + ", ".join(f"`{c}`" for c in col.choices))
            for fk in tbl.foreign_keys:
                if fk.column == col.name:
                    reglas.append(f"-> `{fk.ref_table}.{fk.ref_column}`")
            desc = " ".join(col.description.split())
            lineas.append(
                f"| `{col.name}` | {col.dtype} | {'si' if col.required else 'no'} | "
                f"{'; '.join(reglas)} | {desc} |"
            )
    return "\n".join(lineas) + "\n"


def cmd_docs(args: argparse.Namespace) -> int:
    contenido = _render_docs()
    path = Path(args.salida) if args.salida else DOCS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if args.check:
        actual = path.read_text(encoding="utf-8") if path.exists() else ""
        if actual != contenido:
            print(f"{path} esta desactualizado. Correr: lisart docs")
            return 1
        print(f"{path} al dia.")
        return 0
    path.write_text(contenido, encoding="utf-8")
    print(f"Escrito {path} ({len(REGISTRY)} tablas).")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    from lisart.fuentes import jotform

    if args.fuente == "catalogos":
        from lisart.fuentes import catalogos

        resultado = catalogos.ingestar()
        if resultado.copia_raw:
            print(f"Copia cruda: {resultado.copia_raw}")
        print(resultado.resumen())
        for aviso in resultado.avisos:
            print(f"\nAVISO: {aviso}")
        return 0

    if args.fuente != "jotform":
        print(f"Fuente no soportada todavia: {args.fuente}")
        return 2

    if args.desde_raw:
        resultado = jotform.reconstruir_desde_raw()
        print("Reconstruido desde data/raw/jotform/ (no se llamo a la API).")
    else:
        resultado = jotform.ingestar(actualizar=args.actualizar)

    if resultado.archivo_raw:
        print(f"Copia cruda: {resultado.archivo_raw}")
    print(resultado.resumen())

    if resultado.cambiados and not args.actualizar:
        print(
            f"\nAviso: {resultado.cambiados} envio(s) que ya estaban cambiaron en Jotform "
            "(una edicion o un borrado). No se tocaron.\n"
            "Para traer esos cambios: lisart ingest jotform --actualizar"
        )

    for aviso in resultado.avisos:
        print(f"\nAVISO: {aviso}")

    return 0


def cmd_procesar(args: argparse.Namespace) -> int:
    from lisart.procesos import alta_inscripciones

    resultado = alta_inscripciones.procesar()
    print(resultado.resumen())

    for aviso in resultado.avisos:
        print(f"\nAVISO: {aviso}")
    for conflicto in resultado.conflictos:
        print(f"\nCONFLICTO: {conflicto}")

    grupos = alta_inscripciones.familias()
    con_hermanos = grupos[grupos["alumnos"] > 1] if len(grupos) else grupos
    print(f"\nFamilias con mas de un alumno inscrito: {len(con_hermanos)}")
    if len(con_hermanos):
        reparto = con_hermanos["alumnos"].value_counts().sort_index()
        for cuantos, familias_n in reparto.items():
            print(f"  {familias_n} familia(s) con {cuantos} alumnos")
    return 0


def cmd_ui(args: argparse.Namespace) -> int:
    """Levanta la pantalla. Solo escucha en esta computadora: los datos traen
    informacion personal de menores y no tienen por que salir a la red."""
    import subprocess

    from lisart.ui import APP

    archivo = "app_profesores.py" if getattr(args, "profesores", False) else "app.py"
    modulo = PROJECT_ROOT / "src" / "lisart" / "ui" / archivo
    orden = [
        sys.executable, "-m", "streamlit", "run", str(modulo),
        "--server.address", args.direccion,
        "--server.port", str(args.puerto),
        "--server.headless", "true" if args.sin_navegador else "false",
        "--browser.gatherUsageStats", "false",
    ]
    try:
        return subprocess.call(orden)
    except FileNotFoundError:
        print(f"No se encontro streamlit ({APP}). Instalalo con:")
        print('  uv pip install -e ".[ui]"')
        return 1


def cmd_backup(args: argparse.Namespace) -> int:
    from lisart import backup

    if args.tabla:
        copia = backup.respaldar(args.tabla, motivo="manual")
        print(f"Respaldo: {copia}" if copia else f"{args.tabla} no tiene archivo todavia.")
        return 0

    copias = backup.respaldar_todo()
    for copia in copias:
        print(f"  {ruta_corta(copia)}")
    print(f"\n{len(copias)} tabla(s) respaldada(s) en {backup.backups_dir()}")
    return 0


def cmd_proyeccion(args: argparse.Namespace) -> int:
    from lisart.procesos import proyeccion as proy

    resultado = proy.calcular()
    print(resultado.resumen())

    reparto = proy.por_programa(resultado)
    if len(reparto):
        print("\nDe donde sale:")
        for _, f in reparto.iterrows():
            rebaja = f" -${f['descuento']:>9,.2f}" if f["descuento"] else " " * 11
            print(f"  {f['programa'][:52]:52s} {int(f['alumnos']):>3} x ${f['precio']:>8,.2f}"
                  f"{rebaja} = ${f['subtotal']:>10,.2f}")

    for aviso in resultado.avisos:
        print(f"\nAVISO: {aviso}")

    if not args.sin_exportar:
        escritos = proy.exportar(resultado)
        if escritos:
            print("\nEscrito en:")
            for ruta in escritos:
                print(f"  {ruta_corta(ruta)}")

    if args.excel:
        from datetime import date

        from lisart.procesos import proyeccion_formato as formato

        mes = None
        if args.mes:
            try:
                anio, numero = (int(parte) for parte in args.mes.split("-"))
                mes = date(anio, numero, 1)
            except ValueError:
                print(f"ERROR: --mes espera AAAA-MM, llego '{args.mes}'.")
                return 2
        ruta = formato.escribir_excel(resultado, mes=mes)
        print(f"\nEn el formato de la escuela: {ruta_corta(ruta)}")
        print("  Columnas que van EN BLANCO, y por que:")
        for columna, razon in formato.SIN_DATO.items():
            print(f"    {columna:16s} {razon}")
    return 0


def cmd_guia(args: argparse.Namespace) -> int:
    from lisart import guia

    elegidos = (
        [guia.DOCUMENTOS[args.documento]] if args.documento
        else list(guia.DOCUMENTOS.values())
    )

    if args.check:
        atrasados = [d for d in elegidos if not guia.esta_al_dia(d)]
        for doc in atrasados:
            print(
                f"{ruta_corta(doc.pdf)} se quedo atras de "
                f"{ruta_corta(doc.md)}. Correr: {doc.comando}"
            )
        if atrasados:
            return 1
        for doc in elegidos:
            print(f"{ruta_corta(doc.pdf)} al dia.")
        return 0

    for doc in elegidos:
        try:
            resultado = guia.generar(doc)
        except guia.FaltaDependencia as error:
            print(f"ERROR: {error}")
            return 2
        print(f"Escrito {ruta_corta(resultado.pdf)} ({resultado.paginas} paginas).")
    return 0


def cmd_descuentos(args: argparse.Namespace) -> int:
    from lisart.procesos import descuentos as desc
    from lisart.tables import ALUMNOS_DESCUENTOS

    reporte = desc.refrescar(escribir=not args.revisar)
    print(reporte.resumen())

    for aviso in reporte.avisos:
        print(f"\nAVISO: {aviso}")
    for problema in reporte.problemas:
        print(f"\nERROR: {problema}")

    if reporte.conservados:
        print(
            f"\n{len(reporte.conservados)} renglón(es) de alumnos que ya no están "
            "inscritos se conservaron porque traen descuento o notas."
        )

    if reporte.escrito:
        print(f"\nArchivo listo para editar: {ALUMNOS_DESCUENTOS.path}")
        print("  Se escribe el nombre del descuento en la columna `descuento`,")
        print("  se guarda, y se vuelve a correr `lisart descuentos`.")
    elif args.revisar:
        print("\n(--revisar: no se escribió nada)")

    return 1 if reporte.problemas else 0


def cmd_demo(args: argparse.Namespace) -> int:
    from lisart.procesos import demo

    if args.limpiar:
        borrado = demo.limpiar()
        if not borrado:
            print("No habia datos de prueba que borrar.")
            return 0
        for tabla, n in borrado.items():
            print(f"  - {n:>3} fila(s) de {tabla}")
        print("\nDatos de prueba borrados. Los reales quedaron intactos.")
        return 0

    try:
        cuenta = demo.sembrar()
    except RuntimeError as error:
        print(error)
        return 1
    for que, n in cuenta.items():
        print(f"  + {n:>3} {que}")
    print(
        "\nTodo lleva fuente='demo' y se borra con: lisart demo --limpiar\n"
        "Los alumnos inscritos son reales; al limpiar solo se quita la inscripcion."
    )
    return 0


def cmd_vault(args: argparse.Namespace) -> int:
    from lisart.vault import VAULT_PATH, build_vault

    destino = Path(args.salida) if args.salida else VAULT_PATH
    generadas, sembradas = build_vault(destino, forzar=args.forzar)
    print(f"Vault en {destino}")
    print(f"  {generadas} nota(s) generadas desde tables.py (carpeta Tablas/ + indices)")
    if sembradas:
        print(f"  {sembradas} nota(s) sembradas (Fuentes/, Documentos/, Proyectos/)")
    else:
        print("  0 notas sembradas: las tuyas se respetaron (--forzar para pisarlas)")
    print("\nAbrir en Obsidian: 'Open folder as vault' y elegir esa carpeta.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lisart", description="Sistema administrativo Lisart")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("init", help="crea carpetas y CSV vacios")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("validate", help="revisa los datos contra el esquema")
    p.add_argument("tabla", nargs="?", help="solo esta tabla (por omision, todas)")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("describe", help="muestra el esquema")
    p.add_argument("tabla", nargs="?", help="detalle de una tabla")
    p.set_defaults(func=cmd_describe)

    p = sub.add_parser("docs", help="regenera docs/modelo_de_datos.md")
    p.add_argument("--check", action="store_true", help="solo avisa si esta desactualizado")
    p.add_argument("--salida", help="ruta alterna de salida")
    p.set_defaults(func=cmd_docs)

    p = sub.add_parser("ingest", help="baja datos de un sistema externo")
    p.add_argument(
        "fuente", choices=["jotform", "catalogos"],
        help="jotform = inscripciones; catalogos = el Excel de precios",
    )
    p.add_argument(
        "--actualizar",
        action="store_true",
        help="tambien reescribe los envios que cambiaron en el origen (por omision solo agrega)",
    )
    p.add_argument(
        "--desde-raw",
        action="store_true",
        help="rehace la tabla desde los JSON ya guardados, sin llamar a la API",
    )
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser(
        "procesar", help="convierte las inscripciones en personas, alumnos y relaciones"
    )
    p.add_argument("que", choices=["inscripciones"], help="que proceso correr")
    p.set_defaults(func=cmd_procesar)

    p = sub.add_parser("ui", help="abre la pantalla para ver y editar las tablas")
    p.add_argument("--puerto", type=int, default=8501)
    p.add_argument(
        "--profesores",
        action="store_true",
        help="abre la pantalla de profesores (clase -> profesor -> su semana)",
    )
    p.add_argument(
        "--direccion",
        default="localhost",
        help="por omision solo esta computadora; cambiarlo expone datos personales",
    )
    p.add_argument("--sin-navegador", action="store_true", help="no abrir el navegador solo")
    p.set_defaults(func=cmd_ui)

    p = sub.add_parser("backup", help="respalda las tablas")
    p.add_argument("tabla", nargs="?", help="solo esta tabla (por omision, toda la capa master)")
    p.set_defaults(func=cmd_backup)

    p = sub.add_parser("proyeccion", help="cuanto deberia entrar al mes y de quien")
    p.add_argument("--sin-exportar", action="store_true", help="solo imprime, no escribe CSV")
    p.add_argument(
        "--excel", action="store_true",
        help="ademas escribe el Excel en el formato mensual de la escuela",
    )
    p.add_argument("--mes", help="mes del reporte, AAAA-MM (por omision, el actual)")
    p.set_defaults(func=cmd_proyeccion)

    from lisart.guia import DOCUMENTOS

    p = sub.add_parser("guia", help="regenera los PDF de docs/ desde su markdown")
    p.add_argument(
        "documento", nargs="?", choices=tuple(DOCUMENTOS),
        help="cual regenerar; sin esto, todos",
    )
    p.add_argument(
        "--check", action="store_true",
        help="no escribe: sale con 1 si algun PDF se quedo atras de su .md",
    )
    p.set_defaults(func=cmd_guia)

    p = sub.add_parser(
        "descuentos", help="mantiene el archivo de que alumno tiene que descuento"
    )
    p.add_argument(
        "--revisar", action="store_true",
        help="solo revisa y reporta, sin escribir el archivo",
    )
    p.set_defaults(func=cmd_descuentos)

    p = sub.add_parser("demo", help="siembra o borra datos de prueba (fuente='demo')")
    p.add_argument("--limpiar", action="store_true", help="borra todo lo sembrado")
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("vault", help="regenera el vault de Obsidian")
    p.add_argument(
        "--forzar",
        action="store_true",
        help="tambien reescribe Fuentes/, Documentos/ y Proyectos/ (pierde tus ediciones)",
    )
    p.add_argument("--salida", help="ruta alterna del vault")
    p.set_defaults(func=cmd_vault)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
