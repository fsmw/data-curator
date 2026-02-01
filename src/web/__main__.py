"""Entry point for running the web interface."""

from . import create_app

if __name__ == "__main__":
    app = create_app()
    print("\n" + "=" * 60)
    print("🌐 Mises Data Curator - Web Interface")
    print("=" * 60)
    print("\nStarting server at http://127.0.0.1:5000")
    print("Press CTRL+C to quit\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
