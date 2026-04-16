import sys

from app import create_app

app = create_app()

if __name__ == "__main__":
    if sys.prefix == getattr(sys, "base_prefix", sys.prefix):
        print(
            "[warn] Backend is running outside virtualenv. "
            "Use .venv Python to avoid missing dependency issues."
        )
    print(f"[info] Python executable: {sys.executable}")
    app.run(host="0.0.0.0", port=5000, debug=True)
