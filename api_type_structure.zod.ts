import { z } from 'zod';

// Generiert aus: api_type_structure.json
export const schema = z.any();

export type SchemaType = z.infer<typeof schema>;

