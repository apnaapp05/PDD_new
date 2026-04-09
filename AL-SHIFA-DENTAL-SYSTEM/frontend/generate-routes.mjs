import fs from 'fs';
import path from 'path';

const APP_DIR = './src/app';

let imports = '';
let componentIndex = 0;

function traverse(dir, basePath) {
  if (!fs.existsSync(dir)) return '';
  const files = fs.readdirSync(dir);
  
  let layoutImport = null;
  const pageFiles = [];
  const subDirs = [];
  
  for (const file of files) {
    const filePath = path.join(dir, file);
    if (fs.statSync(filePath).isDirectory()) {
      subDirs.push(filePath);
    } else if (file === 'layout.tsx' || file === 'layout.jsx') {
      layoutImport = `C${componentIndex++}`;
      imports += `import ${layoutImport} from '@/${filePath.replace(/\\/g, '/').replace('src/', '').replace(/\.tsx?$/, '').replace(/\.jsx?$/, '')}';\n`;
    } else if (file === 'page.tsx' || file === 'page.jsx') {
      const pageImport = `C${componentIndex++}`;
      imports += `import ${pageImport} from '@/${filePath.replace(/\\/g, '/').replace('src/', '').replace(/\.tsx?$/, '').replace(/\.jsx?$/, '')}';\n`;
      pageFiles.push({ importName: pageImport, isRoot: dir === APP_DIR });
    }
  }

  let childrenRoutes = '';
  
  if (pageFiles.length > 0) {
    if (pageFiles[0].isRoot) {
      childrenRoutes += `<Route path="/" element={<${pageFiles[0].importName} />} />\n`;
    } else {
      childrenRoutes += `<Route index element={<${pageFiles[0].importName} />} />\n`;
    }
  }
  
  for (const subDir of subDirs) {
    const routePath = path.basename(subDir);
    childrenRoutes += traverse(subDir, routePath);
  }

  if (basePath === '') {
    return childrenRoutes;
  }

  if (layoutImport) {
    let layoutRoute = `<Route path="${basePath}" element={<${layoutImport}><Outlet /></${layoutImport}>}>\n`;
    layoutRoute += childrenRoutes;
    layoutRoute += `</Route>\n`;
    return layoutRoute;
  } else {
    let route = `<Route path="${basePath}">\n`;
    route += childrenRoutes;
    route += `</Route>\n`;
    return route;
  }
}

const rootRoutes = traverse(APP_DIR, '');

const finalFile = `
import React from 'react';
import { Routes, Route, Outlet } from 'react-router-dom';
${imports}

export default function AppRoutes() {
  return (
    <Routes>
      ${rootRoutes}
    </Routes>
  );
}
`;

fs.writeFileSync('./src/routes.tsx', finalFile, 'utf-8');
console.log('Routes generated successfully.');
