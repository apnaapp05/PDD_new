import fs from 'fs';
import path from 'path';

const SRC_DIR = './src';

function processFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf-8');
  let originalContent = content;

  // Next dynamic
  content = content.replace(/from\s+['"]next\/dynamic['"]/g, 'from "@/lib/next-dynamic-shim"');
  
  // if layout.tsx
  if (filePath.endsWith('layout.tsx') || filePath.endsWith('layout.jsx')) {
     content = content.replace(/<html[^>]*>/g, '<div className="app-root">');
     content = content.replace(/<\/html>/g, '</div>');
     content = content.replace(/<body[^>]*>/g, '<div className="app-body">');
     content = content.replace(/<\/body>/g, '</div>');
     
     // Remove Next Metadata
     content = content.replace(/export\s+const\s+metadata\s*:[^=]+=\s*\{[\s\S]*?\};/g, '');
     content = content.replace(/import\s+type\s+\{\s*Metadata\s*\}\s+from\s+['"]next['"];?/g, '');
     content = content.replace(/import\s+\{\s*Inter\s*\}\s+from\s+['"]next\/font\/google['"];?/g, '');
     content = content.replace(/const\s+inter\s*=\s*Inter\([^)]+\);?/g, '');
     content = content.replace(/\$\{inter\.variable\}/g, '');
  }

  if (content !== originalContent) {
    fs.writeFileSync(filePath, content, 'utf-8');
    console.log(`Updated: ${filePath}`);
  }
}

function traverseDir(dir) {
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    if (stat.isDirectory()) {
      traverseDir(filePath);
    } else if (file.endsWith('.tsx') || file.endsWith('.jsx') || file.endsWith('.ts') || file.endsWith('.js')) {
      processFile(filePath);
    }
  }
}

traverseDir(SRC_DIR);
