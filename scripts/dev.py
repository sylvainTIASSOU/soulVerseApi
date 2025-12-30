import subprocess
import sys


def dev():
    try:
        result = subprocess.run([
            sys.executable, "-m", "fastapi", "dev", "src/soul_verse_api/main.py", "--port", "8088"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de 'fastapi dev': {e}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\nArrêt du serveur...")
        sys.exit(0)


if __name__ == "__main__":
    dev()
