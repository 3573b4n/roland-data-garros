#!/usr/bin/env python3
"""Start ngrok tunnel for Roland Data Garros dashboard."""
import sys
import time

try:
    from pyngrok import ngrok, conf
except ImportError:
    print("❌ pyngrok no instalado. Ejecuta: pip install pyngrok")
    sys.exit(1)

# Config
PORT = 8501

try:
    # Start tunnel
    print(f"🚀 Abriendo túnel ngrok → http://localhost:{PORT} ...", flush=True)
    
    # Use the free plan - random subdomain
    tunnel = ngrok.connect(PORT, "http")
    
    public_url = tunnel.public_url
    print(f"\n✅ TÚNEL ACTIVO: {public_url}", flush=True)
    print(f"📱 Abre esta URL en el móvil:", flush=True)
    print(f"\n   {public_url}\n", flush=True)
    print(f"⚠️  El túnel permanece activo hasta que cierres esta terminal.", flush=True)
    print(f"   Presiona Ctrl+C para cerrarlo.\n", flush=True)
    
    # Keep alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n👋 Cerrando túnel...")
        ngrok.kill()
        print("✅ Túnel cerrado.")
        
except Exception as e:
    print(f"❌ Error al crear túnel ngrok: {e}", file=sys.stderr)
    print("\n💡 Solución: Regístrate en https://ngrok.com (gratis), copia tu token y ejecuta:", file=sys.stderr)
    print("   ngrok config add-authtoken TU_TOKEN", file=sys.stderr)
    sys.exit(1)