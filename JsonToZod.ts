import * as fs from 'fs';
import * as path from 'path';

interface JsonSchema {
  type?: string;
  properties?: Record<string, JsonSchema>;
  items?: JsonSchema;
  required?: string[];
  enum?: any[];
  pattern?: string;
  minimum?: number;
  maximum?: number;
  minItems?: number;
  maxItems?: number;
  format?: string;
  description?: string;
  additionalProperties?: boolean | JsonSchema;
  [key: string]: any;
}

interface SubSchema {
  name: string;
  schema: JsonSchema;
  path: string;
}

function toPascalCase(str: string): string {
  return str
    .split(/[_\s-]+/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join('');
}

function generateSchemaName(pathStr: string): string {
  const parts = pathStr.split('.').filter(p => p && p !== 'items' && p !== 'properties');
  if (parts.length === 0) return 'Schema';
  const lastPart = parts[parts.length - 1];
  return toPascalCase(lastPart) + 'Schema';
}

function findSubSchemas(
  schema: JsonSchema,
  subSchemas: Map<string, SubSchema>,
  currentPath: string = '',
  visited: Set<string> = new Set()
): void {
  if (schema.type === 'object' && schema.properties) {
    const schemaStr = JSON.stringify(schema);
    
    if (!visited.has(schemaStr) && currentPath.includes('.')) {
      const name = generateSchemaName(currentPath);
      if (!Array.from(subSchemas.values()).some(s => s.name === name)) {
        subSchemas.set(schemaStr, { name, schema, path: currentPath });
        visited.add(schemaStr);
      }
    }

    Object.entries(schema.properties).forEach(([key, prop]) => {
      findSubSchemas(prop, subSchemas, `${currentPath}.${key}`, visited);
    });
  } else if (schema.type === 'array' && schema.items) {
    findSubSchemas(schema.items, subSchemas, `${currentPath}.items`, visited);
  }
}

function jsonSchemaToZod(
  schema: JsonSchema,
  depth: number = 0,
  subSchemas?: Map<string, SubSchema>,
  fieldName?: string
): string {
  const indent = '  '.repeat(depth);

  // Prüfe ob dieses Schema als Sub-Schema extrahiert wurde
  if (subSchemas) {
    const schemaStr = JSON.stringify(schema);
    for (const [key, subSchema] of subSchemas.entries()) {
      if (key === schemaStr) {
        return subSchema.name;
      }
    }
  }

  if (schema.enum) {
    const enumValues = schema.enum.map(v => JSON.stringify(v)).join(', ');
    let zodEnum = `z.enum([${enumValues}])`;
    if (schema.description) {
      zodEnum += `.describe(${JSON.stringify(schema.description)})`;
    }
    return zodEnum;
  }

  switch (schema.type) {
    case 'string':
      let zodString = 'z.string()';
      
      // UUID-Pattern speziell behandeln
      if (schema.pattern && schema.pattern.includes('[0-9a-fA-F]{8}')) {
        zodString += '.uuid()';
      } else if (schema.pattern) {
        zodString += `.regex(/${schema.pattern}/)`;
      } else if (fieldName && fieldName.toLowerCase() === 'uuid') {
        // Automatisch UUID wenn Feldname "uuid" ist
        zodString += '.uuid()';
      }
      
      if (schema.format === 'date-time') {
        zodString += '.datetime()';
      }
      
      if (schema.description) {
        zodString += `.describe(${JSON.stringify(schema.description)})`;
      }
      return zodString;

    case 'number':
    case 'integer':
      let zodNumber = schema.type === 'integer' ? 'z.number().int()' : 'z.number()';
      if (schema.minimum !== undefined) {
        zodNumber += `.min(${schema.minimum})`;
      }
      if (schema.maximum !== undefined) {
        zodNumber += `.max(${schema.maximum})`;
      }
      if (schema.description) {
        zodNumber += `.describe(${JSON.stringify(schema.description)})`;
      }
      return zodNumber;

    case 'boolean':
      let zodBool = 'z.boolean()';
      if (schema.description) {
        zodBool += `.describe(${JSON.stringify(schema.description)})`;
      }
      return zodBool;

    case 'null':
      return 'z.null()';

    case 'array':
      if (schema.items) {
        let zodArray = `z.array(${jsonSchemaToZod(schema.items, depth, subSchemas, undefined)})`;
        if (schema.minItems !== undefined && schema.maxItems !== undefined && schema.minItems === schema.maxItems) {
          zodArray += `.length(${schema.minItems})`;
        } else {
          if (schema.minItems !== undefined) {
            zodArray += `.min(${schema.minItems})`;
          }
          if (schema.maxItems !== undefined) {
            zodArray += `.max(${schema.maxItems})`;
          }
        }
        if (schema.description) {
          zodArray += `.describe(${JSON.stringify(schema.description)})`;
        }
        return zodArray;
      }
      return 'z.array(z.any())';

    case 'object':
      if (schema.properties) {
        const properties = Object.entries(schema.properties)
          .map(([key, value]) => {
            const zodType = jsonSchemaToZod(value, depth + 1, subSchemas, key);
            const isRequired = schema.required?.includes(key);
            const optional = isRequired ? '' : '.optional()';
            return `${indent}  ${key}: ${zodType}${optional}`;
          })
          .join(',\n');

        let zodObj = `z.object({\n${properties}\n${indent}})`;
        if (schema.description) {
          zodObj += `.describe(${JSON.stringify(schema.description)})`;
        }
        return zodObj;
      }
      if (schema.additionalProperties) {
        if (typeof schema.additionalProperties === 'object') {
          return `z.record(${jsonSchemaToZod(schema.additionalProperties, depth, subSchemas, undefined)})`;
        }
        return 'z.record(z.string())';
      }
      return 'z.object({})';

    default:
      return 'z.any()';
  }
}

function generateZodSchema(jsonSchemaPath: string): void {
  if (!fs.existsSync(jsonSchemaPath)) {
    console.error(`❌ Datei nicht gefunden: ${jsonSchemaPath}`);
    process.exit(1);
  }

  const jsonSchemaContent = fs.readFileSync(jsonSchemaPath, 'utf-8');
  const jsonSchema: JsonSchema = JSON.parse(jsonSchemaContent);

  const subSchemas = new Map<string, SubSchema>();
  findSubSchemas(jsonSchema, subSchemas);

  // Sortiere Sub-Schemas nach Abhängigkeiten (kleinste zuerst)
  const sortedSubSchemas = Array.from(subSchemas.entries())
    .sort((a, b) => {
      const depthA = a[1].path.split('.').length;
      const depthB = b[1].path.split('.').length;
      return depthB - depthA; // Tiefste zuerst
    });

  let subSchemaCode = '';
  const processedSchemas = new Map<string, SubSchema>();
  
  for (const [key, subSchema] of sortedSubSchemas) {
    const zodCode = jsonSchemaToZod(subSchema.schema, 0, processedSchemas, undefined);
    subSchemaCode += `const ${subSchema.name} = ${zodCode};\n\n`;
    processedSchemas.set(key, subSchema);
  }

  const zodSchemaCode = jsonSchemaToZod(jsonSchema, 0, processedSchemas, undefined);

  // Generiere Type-Exports für alle Sub-Schemas
  const typeExports = Array.from(processedSchemas.values())
    .map(s => `export type ${s.name.replace('Schema', '')} = z.infer<typeof ${s.name}>;`)
    .join('\n');

  const outputCode = `import { z } from 'zod';

// Generiert aus: ${path.basename(jsonSchemaPath)}
${subSchemaCode}export const schema = ${zodSchemaCode};

export type SchemaType = z.infer<typeof schema>;
${typeExports ? '\n' + typeExports : ''}
`;

  const dir = path.dirname(jsonSchemaPath);
  const basename = path.basename(jsonSchemaPath, path.extname(jsonSchemaPath));
  const outputPath = path.join(dir, `${basename}.zod.ts`);

  fs.writeFileSync(outputPath, outputCode, 'utf-8');
  console.log(`✅ Zod-Schema gespeichert: ${outputPath}`);
}

// CLI-Argumente verarbeiten
const args = process.argv.slice(2);
if (args.length === 0) {
  console.error('❌ Verwendung: ts-node JsonToZod.ts <pfad-zum-json-schema>');
  process.exit(1);
}

const jsonSchemaPath = args[0];
generateZodSchema(jsonSchemaPath);
