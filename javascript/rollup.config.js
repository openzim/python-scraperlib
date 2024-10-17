// import path from 'path';
// import url from 'url';

import { nodeResolve } from '@rollup/plugin-node-resolve'; // used to bundle node_modules code
import commonjs from '@rollup/plugin-commonjs'; // used to bundle CommonJS node_modules
import terser from '@rollup/plugin-terser'; // used to minify JS code

// const __filename = url.fileURLToPath(import.meta.url);
// const __dirname = path.dirname(__filename);
// const outputDir =
//   process.env.OUTPUT_DIR || path.join(__dirname, '../src/zimscraperlib/rewriting/statics');

const noStrict = {
  renderChunk(code) {
    return code.replace("'use strict';", '');
  },
};

const watchOptions = {
  exclude: 'node_modules/**',
  chokidar: {
    alwaysStat: true,
    usePolling: true,
  },
};

const plugins = [nodeResolve({ preferBuiltins: false }), commonjs(), noStrict];
if (!process.env.DEV) {
  plugins.push(terser());
}

// const packageJson = JSON.parse(readFileSync('./package.json'));

export default {
  input: 'src/wombatSetup.js',
  // output: [
  //   {
  //     file: packageJson.main,
  //     format: 'cjs',
  //     sourcemap: false,
  //     exports: 'named',
  //     name: packageJson.name,
  //   },
  //   {
  //     file: packageJson.module,
  //     format: 'es',
  //     exports: 'named',
  //     sourcemap: false,
  //   },
  // ],
  output: {
    name: 'wombatSetup',
    //file: path.join(outputDir, 'wombatSetup.js'),
    file: 'dist/wombatSetup.js',
    sourcemap: false,
    format: 'iife',
    exports: 'named',
  },
  watch: watchOptions,
  plugins: plugins,
};
