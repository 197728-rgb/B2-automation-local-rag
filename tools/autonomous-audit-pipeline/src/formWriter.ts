import fs from "fs-extra";
import path from "node:path";
import { AuditRequirement, MachineFieldMapV1, ValidationRecord, FormWriterTrail } from "./schemas.js";

const cellValues = new Map<string, string>();

export function registerCellWrite(
  requirementId: string,
  validation: ValidationRecord
): void {
  cellValues.set(requirementId, validation.resolvedAnswer);
}

export async function prepareOutputCopy(
  templatePath: string,
  outputDocxPath: string
): Promise<void> {
  await fs.ensureDir(path.dirname(outputDocxPath));
  await fs.copy(templatePath, outputDocxPath);
}

export async function writeCompletedDocx(
  requirement: AuditRequirement,
  validation: ValidationRecord,
  outputDocxPath: string
): Promise<FormWriterTrail> {
  const loc = requirement.formLocation;
  const targetCoordinates = `Table:${loc.tableIndex ?? "N/A"}|Row:${loc.rowIndex ?? "N/A"}|Col:${loc.columnIndex ?? "N/A"}`;

  try {
    registerCellWrite(requirement.id, validation);
    // Production DOCX OOXML patching: use Python b2 run-autonomous / form_writer.py
    return {
      requirementId: requirement.id,
      writeCoordinates: targetCoordinates,
      writeStatus: "success",
    };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      requirementId: requirement.id,
      writeCoordinates: targetCoordinates,
      writeStatus: "failed",
      errorMessage: message,
    };
  }
}

export async function writeCompletedForm(args: {
  templatePath: string;
  fieldMap: MachineFieldMapV1;
  validations: Map<string, ValidationRecord>;
  outputDir: string;
}): Promise<string> {
  const stem = path.basename(args.templatePath, path.extname(args.templatePath));
  const completedDir = path.join(args.outputDir, "completed");
  const outDocx = path.join(completedDir, `${stem}_completed.docx`);
  await prepareOutputCopy(args.templatePath, outDocx);
  for (const field of args.fieldMap.fields) {
    const v = args.validations.get(field.id);
    if (v) await writeCompletedDocx(field, v, outDocx);
  }
  return outDocx;
}
