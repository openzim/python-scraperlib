import { nodeResolve } from '@rollup/plugin-node-resolve'; // used to bundle node_modules code
import commonjs from '@rollup/plugin-commonjs'; // used to bundle CommonJS node_modules
import terser from '@rollup/plugin-terser'; // used to minify JS code
import strip from '@rollup/plugin-strip';
import versionInjector from 'rollup-plugin-version-injector';

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
  plugins.push(strip());
}
plugins.push(versionInjector()); // do it last so that it is kept no matter what

export default {
  input: 'src/wombatSetup.js',
  output: {
    name: 'wombatSetup',
    file: 'dist/wombatSetup.js',
    sourcemap: false,
    format: 'iife',
    exports: 'named',
  },
  watch: watchOptions,
  plugins: plugins,
};
