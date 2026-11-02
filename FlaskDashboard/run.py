import os
from app import app


# ============================================================
# WATER TANK SYSTEM V5
# FLASK DASHBOARD
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5555))

    print()
    print("=======================================")
    print(" WATER TANK SYSTEM V5")
    print(" FLASK DASHBOARD")
    print(" CONTROL ENABLED")
    print("=======================================")
    print()

    print("Dashboard:")
    print(f"http://0.0.0.0:{port}")
    print()

    print("Dashboard Status:")
    print("GET  /api/dashboard")
    print()

    print("Dashboard Control:")
    print("POST /api/control")
    print()

    print("Master Commands:")
    print("GET  /api/commands")
    print()

    print("Master Data:")
    print("POST /api/master")
    print()

    print("Slave Data:")
    print("POST /api/slave")
    print()

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        threaded=True
    )
