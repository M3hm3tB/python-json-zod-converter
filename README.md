# Python-JSON-Zod-Converter

A toolkit to extract API responses, generate JSON Schemas, and convert them into Zod validation schemas for TypeScript. Perfect for rapid API prototyping, validation, and type-safe development!

## Features
- Extract API responses and generate JSON Schema (Python)
- Convert JSON Schema to Zod schema (TypeScript)
- Automatic detection of UUID fields
- Modular sub-schema generation
- Type exports for TypeScript

## How to use

### 1. Extract API response and generate JSON Schema (Python)

Run the Python script to call your API and generate a valid JSON Schema from the response:

```bash
python api_to_jsonschema.py
```

You'll be prompted for:
- API URL (e.g. http://localhost)
- Port (e.g. 8080)
- Endpoint (e.g. /api/data)
- Optional query parameters

The tool will:
- Fetch the API response
- Show the original response and its type structure
- Generate a valid JSON Schema (shown in the console)
- Optionally save the schema as `schemas/auto_schema.json`

### 2. Convert JSON Schema to Zod (TypeScript)

Make sure you have Node.js and npm installed. Then install dependencies:

```bash
npm install
```

Now run the converter:

```bash
npx ts-node JsonToZod.ts schemas/auto_schema.json
```

This will:
- Read your JSON Schema
- Generate a Zod schema file in the same folder (e.g. `schemas/auto_schema.zod.ts`)
- Export TypeScript types for all sub-schemas

### 3. Use your Zod schema in TypeScript

Import the generated schema and types in your TypeScript project:

```typescript
import { schema, SchemaType } from './auto_schema.zod';

// Validate data
schema.parse(data);
```

## Tips
- The tool automatically detects UUID fields and uses `.uuid()` in Zod
- Sub-schemas are generated for reusable objects
- Descriptions from JSON Schema are added to Zod with `.describe()`
- Use the Python script for any API that returns JSON
- Use the TypeScript tool for any valid JSON Schema

## License
MIT

---

Happy coding! 🚀
