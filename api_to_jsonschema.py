import json
import requests

def ask_user_input():
    base_url = input("Please enter the API URL (e.g. http://localhost): ").strip()
    port = input("Please enter the port (e.g. 8080): ").strip()
    endpoint = input("Please enter the API endpoint (e.g. /api/data): ").strip()

    params_raw = input("Optional query parameters as key=value,key2=value2: ").strip()
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
            # Analyze all elements and collect types
            all_types = {}
            for item in data:
                item_type = determine_types(item)
                if isinstance(item_type, dict):
                    for k, v in item_type.items():
                        if k not in all_types:
                            all_types[k] = set()
                        if isinstance(v, str):
                            all_types[k].add(v)
                        else:
                            all_types[k].add(str(v))
            if all_types:
                # Return first element as representative
                return [determine_types(data[0])]
            else:
                return [determine_types(data[0])]
        else:
            return ["empty_list"]

    else:
        return type(data).__name__


def merge_schemas(schemas):
    """Merge multiple schemas and determine common required fields, recursively for nested objects."""
    if not schemas:
        return {}
    
    # Collect all properties and their types
    all_props = {}
    prop_counts = {}
    total_count = len(schemas)
    
    for schema in schemas:
        if "properties" in schema:
            for key, value in schema["properties"].items():
                if key not in all_props:
                    all_props[key] = []
                    prop_counts[key] = 0
                all_props[key].append(value)
                prop_counts[key] += 1
    
    # Create merged properties
    merged_props = {}
    for key, schemas_list in all_props.items():
        # If field is not present everywhere, it is nullable
        is_optional = prop_counts[key] < total_count
        
        # Collect types
        types = set()
        nullable = False
        descriptions = set()
        all_objects = []
        
        for s in schemas_list:
            if "type" in s:
                s_type = s["type"]
                if s_type == "null":
                    nullable = True
                elif isinstance(s_type, list):
                    # Multi-type wie ["string", "null"]
                    for t in s_type:
                        if t == "null":
                            nullable = True
                        else:
                            types.add(t)
                else:
                    types.add(s_type)
                
                # If type is "object", collect for recursive merging
                if s_type == "object" and "properties" in s:
                    all_objects.append(s)
            
            if "description" in s:
                descriptions.add(s["description"])
        
        if is_optional:
            nullable = True
        
        # Case 1: All are objects -> merge recursively
        if len(types) == 1 and "object" in types and len(all_objects) > 0:
            # Recursively merge the nested objects
            merged_nested = merge_schemas(all_objects)
            merged_props[key] = merged_nested
            
            if "description" not in merged_props[key]:
                if descriptions:
                    merged_props[key]["description"] = list(descriptions)[0]
                else:
                    merged_props[key]["description"] = f"Description for {key}"
            
            if nullable:
                merged_props[key]["type"] = ["object", "null"]
                if "(optional/nullable)" not in merged_props[key].get("description", ""):
                    merged_props[key]["description"] += " (optional/nullable)"
        
        # Case 2: Single type, not nullable
        elif len(types) == 1 and not nullable:
            merged_props[key] = schemas_list[0].copy()
        
        # Case 3: Single type, nullable
        elif len(types) == 1 and nullable:
            merged_props[key] = schemas_list[0].copy()
            single_type = list(types)[0]
            merged_props[key]["type"] = [single_type, "null"]
            if descriptions:
                merged_props[key]["description"] = list(descriptions)[0] + " (optional/nullable)"
        
        # Case 4: Multiple types
        elif len(types) > 1:
            merged_props[key] = {
                "anyOf": [{"type": t} for t in sorted(types)],
                "description": ", ".join(descriptions) if descriptions else f"Multiple types for {key}"
            }
            if nullable:
                merged_props[key]["anyOf"].append({"type": "null"})
        
        # Case 5: Only null
        else:
            merged_props[key] = schemas_list[0].copy()
    
    # Required are only fields that appear in ALL elements
    required = [key for key, count in prop_counts.items() if count == total_count]
    
    result = {
        "type": "object",
        "properties": merged_props
    }
    if required:
        result["required"] = required
    
    return result


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
            # Analyze ALL array elements, not just the first one
            if all(isinstance(item, dict) for item in data):
                # All elements are objects -> merge schemas
                schemas = [infer_full_json_schema(item, key_descriptions) for item in data]
                merged = merge_schemas(schemas)
                return {
                    "type": "array",
                    "items": merged
                }
            else:
                # Mixed or primitive types
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

    # Selection: API or local file
    print("Choose the data source:")
    print("1. API URL")
    print("2. Local JSON file")
    choice = input("Your choice (1 or 2): ").strip()

    if choice == "2":
        # Load local file
        file_path = input("Please enter the path to the JSON file: ").strip()
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"\n✅ JSON file successfully loaded: {file_path}")
        except FileNotFoundError:
            print(f"❌ File '{file_path}' not found!")
            return
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON file: {e}")
            return
        except Exception as e:
            print(f"❌ Error loading file: {e}")
            return
    else:
        # Use API
        base_url, port, endpoint, params = ask_user_input()

        # Clean inputs
        base_url = clean_ascii(base_url)
        port = clean_ascii(port)
        endpoint = clean_ascii(endpoint)

        # Add protocol if not present
        if not base_url.startswith("http://") and not base_url.startswith("https://"):
            base_url = "http://" + base_url

        full_url = f"{base_url}:{port}{endpoint}"

        print(f"\n➡️  Sending request to: {full_url}")
        if params:
            print(f"➡️  With parameters: {params}")

        # API Call
        response = requests.get(full_url, params=params)

        try:
            data = response.json()
        except json.JSONDecodeError:
            try:
                data = json.loads(response.text)
                print("⚠️ Content-Type header or format is incorrect, but JSON could still be loaded.")
            except Exception as e:
                print("❌ The API does not respond with JSON!")
                print("Raw Response:")
                print(response.text)
                return

    print("\n📥 Original Response:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    # Generate data type structure
    type_structure = determine_types(data)

    print("\n📦 Type structure of API response (JSON with types):")
    print(json.dumps(type_structure, indent=2, ensure_ascii=False))

    # Automatically generate JSON schema
    schema = infer_full_json_schema(data)
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    
    print("\n📋 JSON Schema (validatable):")
    print(json.dumps(schema, indent=2, ensure_ascii=False))

    # Save schema
    save_schema = input("\nDo you want to save the JSON schema? (y/n): ").strip().lower()
    if save_schema == "y":
        import os
        output_dir = "schemas"
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.join(output_dir, "auto_schema.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
        print(f"💾 JSON schema saved as {filename}")

    # Validation against JSON schema
    validate = input("\nDo you want to validate the response against a JSON schema? (y/n): ").strip().lower()
    if validate == "y":
        try:
            import jsonschema
        except ImportError:
            print("❌ The 'jsonschema' package is not installed. Please install it with 'pip install jsonschema'.")
        else:
            schema_file = input("Path to schema file (e.g. oven_layout_schema.json): ").strip()
            import os
            if not os.path.isfile(schema_file):
                print(f"❌ File '{schema_file}' not found!")
            else:
                with open(schema_file, "r", encoding="utf-8") as f:
                    schema = json.load(f)
                try:
                    jsonschema.validate(instance=data, schema=schema)
                    print("✅ The API response is valid according to the schema!")
                except jsonschema.ValidationError as ve:
                    print("❌ The API response is NOT valid!")
                    print(f"Error: {ve.message}")
                except Exception as e:
                    print(f"❌ Validation error: {e}")

    # Optional save to file
    save = input("\nDo you want to save the type structure as JSON? (y/n): ").strip().lower()
    if save == "y":
        import os
        output_dir = "schemas"
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.join(output_dir, "api_type_structure.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(type_structure, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved as {filename}")


if __name__ == "__main__":
    main()
