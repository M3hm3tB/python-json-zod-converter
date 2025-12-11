import { z } from 'zod';

// Generiert aus: auto_schema.json
const LeftSchema = z.object({
  heater: z.boolean().describe("Boolescher Wert"),
  fan: z.boolean().describe("Boolescher Wert"),
  infrared: z.boolean().describe("Boolescher Wert")
}).describe("Beschreibung für left");

const RightSchema = z.object({
  heater: z.boolean().describe("Boolescher Wert"),
  fan: z.boolean().describe("Boolescher Wert"),
  infrared: z.boolean().describe("Boolescher Wert")
}).describe("Beschreibung für right");

const ZonesSchema = z.object({
  id: z.number().int().describe("Ganzzahl"),
  labels: z.array(z.string().describe("String-Wert")).describe("Beschreibung für labels"),
  role: z.string().describe("String-Wert"),
  length_mm: z.number().describe("Dezimalzahl"),
  left: LeftSchema,
  right: RightSchema,
  vacuum: z.boolean().describe("Boolescher Wert")
});

const PeripheralsSchema = z.object({
  stacklight: z.string().describe("String-Wert")
}).describe("Beschreibung für peripherals");

const MetadataSchema = z.object({
  created_at: z.string().describe("String-Wert"),
  author: z.string().describe("String-Wert")
}).describe("Beschreibung für metadata");

export const schema = z.object({
  schema_version: z.string().describe("String-Wert"),
  uuid: z.string().uuid().describe("String-Wert"),
  manufacturer: z.string().describe("String-Wert"),
  name: z.string().describe("String-Wert"),
  serial: z.string().describe("String-Wert"),
  location: z.string().describe("String-Wert"),
  chain_pitch_mm: z.number().describe("Dezimalzahl"),
  peripherals: PeripheralsSchema,
  extra_labels: z.array(z.string().describe("String-Wert")).describe("Beschreibung für extra_labels"),
  zones: z.array(ZonesSchema).describe("Beschreibung für zones"),
  metadata: MetadataSchema
});

export type SchemaType = z.infer<typeof schema>;

export type Left = z.infer<typeof LeftSchema>;
export type Right = z.infer<typeof RightSchema>;
export type Zones = z.infer<typeof ZonesSchema>;
export type Peripherals = z.infer<typeof PeripheralsSchema>;
export type Metadata = z.infer<typeof MetadataSchema>;
