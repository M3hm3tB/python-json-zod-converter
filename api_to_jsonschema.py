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
    """Recursively traverse the structure and determine types."""
    if isinstance(data, dict):
        return {key: determine_types(value) for key, value in data.items()}

    elif isinstance(data, list):
        if data:
            return [determine_types(data[0])]  # Example type of first element
        else:
            return ["empty_list"]

    else:
        return type(data).__name__


def infer_full_json_schema(data, key_descriptions=None):
    """
    Generate a JSON Schema similar to json_schema.json, including type, properties, required, description.
    key_descriptions can be a dict with descriptions (optional).
    """
    if key_descriptions is None:
        key_descriptions = {}
    if isinstance(data, dict):
        props = {}
        required = []
        for k, v in data.items():
            props[k] = infer_full_json_schema(v, key_descriptions.get(k, {}))
            # Placeholder for description
            if "description" not in props[k]:
                props[k]["description"] = key_descriptions.get(k, "") or f"Description for {k}" 
            required.append(k)
        return {
            "type": "object",
            "properties": props,
            "required": required
        }
    elif isinstance(data, list):
        if data:
            return {
                "type": "array",
                "items": infer_full_json_schema(data[0], key_descriptions)
            }
        else:
            return {"type": "array", "items": {}}
    elif isinstance(data, str):
        return {"type": "string", "description": "String value"}
    elif isinstance(data, bool):
        return {"type": "boolean", "description": "Boolean value"}
    elif isinstance(data, int):
        return {"type": "integer", "description": "Integer value"}
    elif isinstance(data, float):
        return {"type": "number", "description": "Number value"}
    elif data is None:
        return {"type": "null", "description": "Null value"}
    else:
        return {"type": "string", "description": "Unknown type"}


def clean_ascii(text):
    """Remove non-ASCII characters from a string."""
    return text.encode("ascii", "ignore").decode()


def main():

    base_url, port, endpoint, params = ask_user_input()

    # Eingaben bereinigen
    base_url = clean_ascii(base_url)
    port = clean_ascii(port)
    endpoint = clean_ascii(endpoint)

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

    # JSON-Schema automatisch generieren
    schema = infer_full_json_schema(data)
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    
    print("\n📋 JSON-Schema (validierbar):")
    print(json.dumps(schema, indent=2, ensure_ascii=False))

    # Schema speichern
    save_schema = input("\nMöchtest du das JSON-Schema speichern? (y/n): ").strip().lower()
    if save_schema == "y":
        import os
        output_dir = "schemas"
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.join(output_dir, "auto_schema.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
        print(f"💾 JSON-Schema gespeichert als {filename}")

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
        import os
        output_dir = "schemas"
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.join(output_dir, "api_type_structure.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(type_structure, f, indent=2, ensure_ascii=False)
        print(f"💾 Gespeichert als {filename}")


if __name__ == "__main__":
    main()
