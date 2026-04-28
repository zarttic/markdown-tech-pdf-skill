#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");

const skillName = "markdown-tech-pdf";
const packageRoot = path.resolve(__dirname, "..");
const sourceDir = path.join(packageRoot, skillName);

function codexHome() {
  return process.env.CODEX_HOME || path.join(os.homedir(), ".codex");
}

function copyDir(source, target) {
  fs.mkdirSync(target, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const sourcePath = path.join(source, entry.name);
    const targetPath = path.join(target, entry.name);
    if (entry.isDirectory()) {
      copyDir(sourcePath, targetPath);
    } else if (entry.isFile()) {
      fs.copyFileSync(sourcePath, targetPath);
    }
  }
}

function main() {
  if (!fs.existsSync(sourceDir)) {
    console.error(`Skill source not found: ${sourceDir}`);
    process.exit(1);
  }

  const skillsDir = path.join(codexHome(), "skills");
  const targetDir = path.join(skillsDir, skillName);
  copyDir(sourceDir, targetDir);

  console.log(`Installed ${skillName} to ${targetDir}`);
  console.log("Restart Codex if the skill does not appear immediately.");
}

main();
