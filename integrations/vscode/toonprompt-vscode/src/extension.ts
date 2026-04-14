import * as vscode from "vscode";
import { spawnSync } from "node:child_process";

export function activate(context: vscode.ExtensionContext): void {
  const command = vscode.commands.registerCommand("toonprompt.optimizeSelection", async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showWarningMessage("No active editor found.");
      return;
    }

    const selection = editor.selection;
    const text = editor.document.getText(selection).trim();
    if (!text) {
      vscode.window.showWarningMessage("Select some text first.");
      return;
    }

    const cfg = vscode.workspace.getConfiguration("toonprompt");
    const binary = cfg.get<string>("binaryPath", "toon");
    const profile = cfg.get<string>("profile", "default");

    const proc = spawnSync(binary, ["--profile", profile, "inspect", "--prompt", text, "--format", "json"], {
      encoding: "utf-8"
    });
    if (proc.status !== 0) {
      vscode.window.showErrorMessage(`ToonPrompt failed: ${proc.stderr || proc.stdout}`);
      return;
    }

    try {
      const parsed = JSON.parse(proc.stdout);
      const output = String(parsed.transformed ?? text);
      await editor.edit((builder) => builder.replace(selection, output));
      vscode.window.showInformationMessage("ToonPrompt optimization applied.");
    } catch {
      vscode.window.showErrorMessage("Failed to parse ToonPrompt output.");
    }
  });

  context.subscriptions.push(command);
}

export function deactivate(): void {
  // no-op
}
