from pathlib import Path

import requests


NETLIFY_TOKEN = "nfp_F3g6cPwQhpnHCEnjH7aW69wh8zqFb94702b6"
SITE_ID = "porra-turiel.netlify.app"
ZIP_FILE = Path("public.zip")

NETLIFY_DEPLOY_URL = (
    f"https://api.netlify.com/api/v1/sites/{SITE_ID}/deploys"
)


def deploy_to_netlify(zip_path: Path = ZIP_FILE):
    if not zip_path.exists():
        raise FileNotFoundError(f"No existe el ZIP para desplegar: {zip_path}")

    headers = {
        "Authorization": f"Bearer {NETLIFY_TOKEN}",
        "Content-Type": "application/zip",
    }

    print("\nSubiendo ZIP a Netlify...")
    print(f"Site: {SITE_ID}")
    print(f"ZIP: {zip_path}")

    with open(zip_path, "rb") as file:
        response = requests.post(
            NETLIFY_DEPLOY_URL,
            headers=headers,
            data=file,
            timeout=120,
        )

    response.raise_for_status()

    deploy_data = response.json()

    print("\nDeploy enviado correctamente a Netlify.")
    print(f"Deploy ID: {deploy_data.get('id')}")
    print(f"Estado: {deploy_data.get('state')}")
    print(f"URL: {deploy_data.get('deploy_url') or deploy_data.get('url')}")

    return deploy_data


def main():
    deploy_to_netlify()


if __name__ == "__main__":
    main()