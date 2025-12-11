import json
import requests

def ask_user_input():
    base_url = input("Bitte die API-URL eingeben (z.B. http://localhost): ").strip()
    port = input("Bitte Port eingeben (z.B. 8080): ").strip()
    endpoint = input("Bitte den API-Endpunkt eingeben (z.B. /api/data): ").strip()

    params_raw = input("Optionale Query-Parameter als key=value,key2=value2: ").strip()
    params = {}

    if params_raw:
        for pair in params_raw.split(","):
            key, value = pair.split("=")
            params[key.strip()] = value.strip()

    return base_url, port, endpoint, params


def determine_types(data):
    """Rekursiv die Struktur durchlaufen und Typen bestimmen."""
    if isinstance(data, dict):
        return {key: determine_types(value) for key, value in data.items()}

    elif isinstance(data, list):
        if data:
            return [determine_types(data[0])]  # Beispieltyp des 1. Elements
        else:
            return ["empty_list"]

    else:
        return type(data).__name__


def main():

    base_url, port, endpoint, params = ask_user_input()

    # Protokoll ergänzen, falls nicht vorhanden
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = "http://" + base_url

    full_url = f"{base_url}:{port}{endpoint}"

    print(f"\n➡️  Sende Request an: {full_url}")
    if params:
        print(f"➡️  Mit Parametern: {params}")

    # API Call
    response = requests.get(full_url, params=params)

    try:
        data = response.json()
    except json.JSONDecodeError:
        try:
            data = json.loads(response.text)
            print("⚠️ Content-Type Header oder Format ist nicht korrekt, aber JSON konnte trotzdem geladen werden.")
        except Exception as e:
            print("❌ Die API antwortet nicht mit JSON!")
            print("Raw Response:")
            print(response.text)
            return

    print("\n📥 Original Response:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    # Datentyp-Struktur erzeugen
    type_structure = determine_types(data)

    print("\n📦 Typstruktur der API-Response (JSON mit Typen):")
    print(json.dumps(type_structure, indent=2, ensure_ascii=False))

    # Validierung gegen JSON-Schema
    validate = input("\nMöchtest du die Response gegen ein JSON-Schema validieren? (y/n): ").strip().lower()
    if validate == "y":
        try:
            import jsonschema
        except ImportError:
            print("❌ Das Paket 'jsonschema' ist nicht installiert. Bitte mit 'pip install jsonschema' nachinstallieren.")
        else:
            schema_file = input("Pfad zur Schema-Datei (z.B. oven_layout_schema.json): ").strip()
            import os
            if not os.path.isfile(schema_file):
                print(f"❌ Datei '{schema_file}' nicht gefunden!")
            else:
                with open(schema_file, "r", encoding="utf-8") as f:
                    schema = json.load(f)
                try:
                    jsonschema.validate(instance=data, schema=schema)
                    print("✅ Die API-Response ist gültig nach dem Schema!")
                except jsonschema.ValidationError as ve:
                    print("❌ Die API-Response ist NICHT gültig!")
                    print(f"Fehler: {ve.message}")
                except Exception as e:
                    print(f"❌ Validierungsfehler: {e}")

    # Optional in Datei speichern
    save = input("\nMöchtest du die Typstruktur als JSON speichern? (y/n): ").strip().lower()
    if save == "y":
        filename = "api_type_structure.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(type_structure, f, indent=2, ensure_ascii=False)
        print(f"💾 Gespeichert als {filename}")


if __name__ == "__main__":
    main()
