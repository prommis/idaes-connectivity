import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  cleanupSVG,
  exportJSONPackage,
  importDirectory,
  runSVGO,
} from '@iconify/tools';

const buildDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(buildDirectory, '..');
const sourceDirectory = resolve(repositoryRoot, 'idaes_connectivity', 'images');
const outputDirectory = resolve(buildDirectory, 'dist', 'package');

const iconSet = await importDirectory(sourceDirectory, {
  prefix: 'idaes',
  ignoreImportErrors: false,
});

iconSet.forEach((name, type) => {
  if (type !== 'icon') {
    return;
  }

  const svg = iconSet.toSVG(name);
  if (!svg) {
    throw new Error(`Unable to load icon: ${name}`);
  }

  try {
    cleanupSVG(svg);
    // These equipment illustrations intentionally retain their fixed palette.
    runSVGO(svg);
    iconSet.fromSVG(name, svg);
  } catch (error) {
    throw new Error(`Invalid icon "${name}": ${error.message}`, {
      cause: error,
    });
  }
});

iconSet.info = {
  name: 'IDAES Process Equipment',
  author: {
    name: 'PrOMMiS',
    url: 'https://github.com/prommis/idaes-connectivity',
  },
  license: {
    title: 'BSD 3-Clause',
    spdx: 'BSD-3-Clause',
    url: 'https://github.com/prommis/idaes-connectivity/blob/main/LICENSE.md',
  },
};

const license = await readFile(resolve(repositoryRoot, 'LICENSE.md'), 'utf8');
const readme = `# IDAES Process Equipment Icons

Iconify-compatible process equipment icons generated from the SVG sources in
the idaes-connectivity repository.

Icon names use the \`idaes\` prefix, for example \`idaes:pump\` and
\`idaes:heat-exchanger-1\`.
`;

await exportJSONPackage(iconSet, {
  target: outputDirectory,
  cleanup: true,
  package: {
    name: '@prommis/idaes-icons',
    version: '0.1.0',
    description: 'IDAES process equipment icons in Iconify format',
    license: 'BSD-3-Clause',
    homepage: 'https://github.com/prommis/idaes-connectivity',
    repository: {
      type: 'git',
      url: 'git+https://github.com/prommis/idaes-connectivity.git',
    },
  },
  customFiles: {
    'LICENSE.md': license,
    'README.md': readme,
  },
});

console.log(`Built ${iconSet.count()} icons in ${outputDirectory}`);
