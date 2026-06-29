import shutil
import subprocess
import sys
from pathlib import Path


DATA_DIR = Path("data")
PUBLIC_DIR = Path("public")
ZIP_FILE = Path("public.zip")

STATIC_FILES_REQUIRED = [
    DATA_DIR / "teams.json",
    DATA_DIR / "predictions.json",
]

FILES_TO_DELETE = [
    DATA_DIR / "spain_answers.json",
    DATA_DIR / "results.json",
]

SCRIPTS = [
    "get_data.py",
    "generate_spain_answers.py",
    "calculate_points.py",
    "generate_html.py",
]


def check_static_files():
    print("\nComprobando ficheros estáticos...")

    for file_path in STATIC_FILES_REQUIRED:
        if not file_path.exists():
            raise FileNotFoundError(
                f"No existe {file_path}. "
                f"Debes generarlo antes de ejecutar el orquestador."
            )

        print(f"OK: {file_path}")


def delete_old_files():
    print("\nLimpiando ficheros dinámicos anteriores...")

    for file_path in FILES_TO_DELETE:
        if file_path.exists():
            file_path.unlink()
            print(f"Eliminado: {file_path}")
        else:
            print(f"No existe, se omite: {file_path}")

    if PUBLIC_DIR.exists():
        shutil.rmtree(PUBLIC_DIR)
        print(f"Carpeta eliminada: {PUBLIC_DIR}")
    else:
        print(f"No existe, se omite: {PUBLIC_DIR}")

    if ZIP_FILE.exists():
        ZIP_FILE.unlink()
        print(f"ZIP anterior eliminado: {ZIP_FILE}")
    else:
        print(f"No existe, se omite: {ZIP_FILE}")


def run_script(script_name):
    script_path = Path(script_name)

    if not script_path.exists():
        raise FileNotFoundError(f"No se encuentra el script: {script_name}")

    print(f"\nEjecutando: {script_name}")
    print("-" * 60)

    subprocess.run(
        [sys.executable, script_name],
        check=True,
    )

    print("-" * 60)
    print(f"Finalizado: {script_name}")


def check_final_output():
    html_file = PUBLIC_DIR / "index.html"

    if not html_file.exists():
        raise FileNotFoundError("No se ha generado public/index.html")

    print("\nHTML generado correctamente.")
    print(f"HTML generado: {html_file}")

def create_zip():
    import zipfile

    print("\nCreando ZIP de la carpeta public...")

    html_file = PUBLIC_DIR / "index.html"

    if not html_file.exists():
        raise FileNotFoundError("No existe public/index.html")

    if ZIP_FILE.exists():
        ZIP_FILE.unlink()

    with zipfile.ZipFile(ZIP_FILE, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(PUBLIC_DIR, "public/")

        for file_path in PUBLIC_DIR.rglob("*"):
            if file_path.is_file():
                arcname = Path("public") / file_path.relative_to(PUBLIC_DIR)
                zip_file.write(file_path, arcname)

    with zipfile.ZipFile(ZIP_FILE, "r") as zip_file:
        zip_content = zip_file.namelist()

    print(f"ZIP generado correctamente: {ZIP_FILE}")

    print("\nContenido del ZIP:")
    for item in zip_content:
        print(f"- {item}")

    if "public/index.html" not in zip_content:
        raise FileNotFoundError("El ZIP no contiene public/index.html")


def deploy_zip_to_netlify():
    print("\nEjecutando despliegue en Netlify...")
    run_script("deploy_netlify.py")


def delete_zip():
    print("\nEliminando ZIP temporal...")

    if ZIP_FILE.exists():
        ZIP_FILE.unlink()
        print(f"ZIP eliminado: {ZIP_FILE}")
    else:
        print(f"No existe, se omite: {ZIP_FILE}")

def main():
    print("Iniciando generación completa de la Porra Turiel 2026")

    check_static_files()
    delete_old_files()

    for script in SCRIPTS:
        run_script(script)

    check_final_output()
    create_zip()
    deploy_zip_to_netlify()
    delete_zip()

    print("\nProceso completo finalizado correctamente.")


if __name__ == "__main__":
    main()